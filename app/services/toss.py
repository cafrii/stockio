"""
토스증권 Open API 클라이언트

토스증권 Open API 1.2.4 (docs/toss_openapi_3.1.0.json) 기준으로 작성.
키움 클라이언트와 동일한 StockProvider 인터페이스를 구현하여 이중화한다.

주의: 토스 현재가 API(/api/v1/prices)는 현재가만 제공하며 52주 최고/최저가는
제공하지 않는다. 대신 일봉 캔들 API(/api/v1/candles, interval=1d)를 페이지네이션으로
약 250거래일(≈52주)치 조회하여 high52w/low52w를 직접 산출한다.
(키움 250hgst/250lwst와 동일한 250일 창 기준 → provider 간 정합)
"""
import os
import time
import httpx
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from app.core.config import config
from app.services.base import StockProvider, StockProviderError, ProviderAuthError, normalize_price

logger = logging.getLogger(__name__)


class TossAPIError(StockProviderError):
    """토스 API 에러"""
    pass


class TossAuthError(ProviderAuthError):
    """토스 인증 에러"""
    pass


class TossClient(StockProvider):
    """토스증권 Open API 클라이언트"""

    name = "toss"

    #: 52주 산출 창(거래일 수). 키움 250hgst(250일)와 정합.
    WINDOW_52W_DAYS = 250
    #: 캔들 API 1회 호출당 최대 봉 수
    CANDLE_MAX_PER_CALL = 200

    def __init__(self):
        self.api_host = config.TOSS_API_HOST
        self.client_id = config.TOSS_API_CLIENT_ID
        self.client_secret = config.TOSS_API_SECRET
        self.token_file = config.TOSS_TOKEN_ENV
        self._token: Optional[str] = None
        self._token_expire_at: Optional[str] = None  # "YYYYmmddHHMMSS" 형식
        self._last_token_issued_at: Optional[str] = None

    # ------------------------------------------------------------------
    # 토큰 관리
    # ------------------------------------------------------------------
    def _load_token_from_file(self) -> Optional[str]:
        """파일에서 저장된 토큰 로드 (만료 시 None)"""
        if not os.path.isfile(self.token_file):
            return None
        if not os.access(self.token_file, os.R_OK):
            logger.warning("토스 토큰 파일 읽기 권한 없음")
            return None

        load_dotenv(self.token_file, override=True)
        token = os.getenv("TOSS_API_TOKEN")
        expire_at = os.getenv("TOSS_API_EXPIRE_AT")

        if not token or not expire_at:
            return None

        now = time.strftime("%Y%m%d%H%M%S")
        if expire_at < now:
            logger.info(f"토스 토큰 만료됨: expire_at={expire_at}, now={now}")
            try:
                os.remove(self.token_file)
            except Exception as e:
                logger.warning(f"만료된 토스 토큰 파일 삭제 실패: {e}")
            return None

        self._token = token
        self._token_expire_at = expire_at
        return token

    def _save_token_to_file(self, token: str, expire_at: str):
        """토큰을 파일에 저장"""
        with open(self.token_file, "w") as f:
            f.write(f"TOSS_API_TOKEN = {token}\n")
            f.write(f"TOSS_API_EXPIRE_AT = {expire_at}\n")
        self._token = token
        self._token_expire_at = expire_at
        self._last_token_issued_at = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"토스 토큰 파일 저장 완료: expire_at={expire_at}")

    async def _request_new_token(self) -> str:
        """새 토큰 발급 (OAuth2 client_credentials, form-urlencoded)"""
        if not self.client_id or not self.client_secret:
            raise TossAuthError("토스 API 자격 증명(TOSS_API_CLIENT_ID/SECRET)이 설정되지 않았습니다.")

        logger.info("토스 새 토큰 발급 요청 시작")
        url = f"{self.api_host}/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data, timeout=10.0)
        except httpx.HTTPError as e:
            logger.error(f"토스 토큰 요청 HTTP 에러: {e}")
            raise TossAPIError(f"토스 토큰 요청 실패: {e}")

        if response.status_code != 200:
            # OAuth2 표준 에러 포맷: {"error": "...", "error_description": "..."}
            err = _safe_json(response)
            msg = err.get("error_description") or err.get("error") or f"HTTP {response.status_code}"
            logger.error(f"토스 토큰 발급 실패: status={response.status_code}, msg={msg}")
            raise TossAuthError(f"토스 토큰 발급 실패: {msg}")

        result = response.json()
        token = result.get("access_token")
        expires_in = result.get("expires_in")

        if not token or expires_in is None:
            raise TossAuthError("토스 토큰 또는 만료 정보가 응답에 없습니다.")

        # expires_in(초) → 절대 만료 시각으로 변환. 안전 마진 60초 차감.
        expire_epoch = time.time() + max(int(expires_in) - 60, 0)
        expire_at = time.strftime("%Y%m%d%H%M%S", time.localtime(expire_epoch))

        logger.info(f"토스 새 토큰 발급 성공: expires_in={expires_in}, expire_at={expire_at}")
        self._save_token_to_file(token, expire_at)
        return token

    async def get_token(self, force_new: bool = False) -> str:
        """토큰 획득 (메모리 캐시 → 파일 → 신규 발급)"""
        if not force_new and self._token:
            now = time.strftime("%Y%m%d%H%M%S")
            if self._token_expire_at and self._token_expire_at > now:
                return self._token

        if not force_new:
            token = self._load_token_from_file()
            if token:
                return token

        return await self._request_new_token()

    # ------------------------------------------------------------------
    # 헤더/캔들 유틸
    # ------------------------------------------------------------------
    @staticmethod
    def _auth_headers(token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    async def _fetch_candles(
        self, code: str, token: str, count: int, before: Optional[str] = None
    ) -> (list, Optional[str]):
        """
        일봉 캔들 1페이지 조회 (GET /api/v1/candles, interval=1d).

        Returns:
            (candles 리스트, nextBefore) — nextBefore는 다음 페이지 상한(없으면 None)
        """
        url = f"{self.api_host}/api/v1/candles"
        params: Dict[str, Any] = {"symbol": code, "interval": "1d", "count": count}
        if before:
            params["before"] = before  # httpx가 '+' 등 URL 인코딩 처리

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, headers=self._auth_headers(token), params=params, timeout=10.0
                )
                if response.status_code == 401:
                    logger.warning("[toss] 캔들 401 - 토큰 재발급 후 재시도")
                    token = await self.get_token(force_new=True)
                    response = await client.get(
                        url, headers=self._auth_headers(token), params=params, timeout=10.0
                    )
                if response.status_code != 200:
                    err = _safe_json(response)
                    detail = (err.get("error") or {}).get("message") if isinstance(err.get("error"), dict) else err.get("error")
                    detail = detail or f"HTTP {response.status_code}"
                    raise TossAPIError(f"토스 캔들 조회 실패: {detail}")
                result = response.json()
        except httpx.HTTPError as e:
            raise TossAPIError(f"토스 캔들 조회 실패: {e}")

        r = result.get("result") or {}
        return (r.get("candles") or [], r.get("nextBefore"))

    async def _get_52w_high_low(self, code: str, token: str):
        """
        일봉 캔들을 페이지네이션(약 2회)으로 250거래일치 모아 52주 최고/최저가 산출.

        Returns:
            (high52w, low52w, high52w_date) — 실패 시 (None, None, None)
        """
        # 1페이지: 최신 200봉
        candles, next_before = await self._fetch_candles(
            code, token, count=self.CANDLE_MAX_PER_CALL
        )
        # 2페이지: 나머지(약 50봉)
        remaining = self.WINDOW_52W_DAYS - len(candles)
        if remaining > 0 and next_before:
            more, _ = await self._fetch_candles(
                code, token, count=min(remaining, self.CANDLE_MAX_PER_CALL), before=next_before
            )
            candles += more

        best_high: Optional[float] = None
        best_date: Optional[str] = None
        low52w: Optional[float] = None
        seen = set()
        for c in candles[: self.WINDOW_52W_DAYS + self.CANDLE_MAX_PER_CALL]:
            ts = c.get("timestamp")
            if ts in seen:  # 페이지 경계 중복 봉 제거
                continue
            seen.add(ts)
            high = normalize_price(c.get("highPrice"))
            low = normalize_price(c.get("lowPrice"))
            if high is not None and (best_high is None or high > best_high):
                best_high = high
                best_date = ts
            if low is not None and (low52w is None or low < low52w):
                low52w = low

        # ISO(2026-03-25T09:00:00+09:00) → "20260325" (키움 250hgst_pric_dt 포맷)
        high52w_date = best_date[:10].replace("-", "") if best_date else None
        return best_high, low52w, high52w_date

    # ------------------------------------------------------------------
    # 시세 조회
    # ------------------------------------------------------------------
    async def get_stock_price(self, code: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        현재가 조회(GET /api/v1/prices) + 일봉 캔들 기반 52주 최고/최저가 산출.
        """
        logger.info(f"[toss] 시세 조회 시작: code={code}, market={market}")
        token = await self.get_token()

        url = f"{self.api_host}/api/v1/prices"
        params = {"symbols": code}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self._auth_headers(token), params=params, timeout=10.0)

                # 401 인증 만료 → 토큰 재발급 후 1회 재시도
                if response.status_code == 401:
                    logger.warning("[toss] HTTP 401 - 토큰 재발급 후 재시도")
                    token = await self.get_token(force_new=True)
                    response = await client.get(url, headers=self._auth_headers(token), params=params, timeout=10.0)

                if response.status_code != 200:
                    err = _safe_json(response)
                    detail = (err.get("error") or {}).get("message") if isinstance(err.get("error"), dict) else err.get("error")
                    detail = detail or f"HTTP {response.status_code}"
                    logger.error(f"[toss] 시세 조회 실패: status={response.status_code}, msg={detail}")
                    if response.status_code in (401, 403):
                        raise TossAuthError(f"토스 인증 실패: {detail}")
                    raise TossAPIError(f"토스 시세 조회 실패: {detail}")

                result = response.json()
        except httpx.HTTPError as e:
            logger.error(f"[toss] HTTP 에러: {e}")
            raise TossAPIError(f"토스 시세 조회 실패: {e}")

        items = result.get("result") or []
        if not items:
            raise TossAPIError(f"토스 시세 데이터를 찾을 수 없습니다: code={code}")

        item = items[0]
        price = normalize_price(item.get("lastPrice"))
        if price is None:
            raise TossAPIError("토스 현재가 데이터를 찾을 수 없습니다")

        # 52주 최고/최저가: 일봉 캔들로 산출. 실패해도 현재가는 반환(정보만 결손).
        high52w = low52w = high52w_date = None
        try:
            high52w, low52w, high52w_date = await self._get_52w_high_low(code, token)
        except StockProviderError as e:
            logger.warning(f"[toss] 52주 산출 실패(현재가는 정상 반환): {e}")

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        logger.info(
            f"[toss] 시세 조회 성공: code={code}, price={price}, "
            f"high52w={high52w}, low52w={low52w}"
        )

        return {
            "code": code,
            "price": price,
            "high52w": high52w,
            "low52w": low52w,
            "high52w_date": high52w_date,
            "timestamp": timestamp,
            "market": market,
            "provider": self.name,
        }


def _safe_json(response: httpx.Response) -> Dict[str, Any]:
    """응답 JSON 파싱 실패 시 빈 딕셔너리 반환"""
    try:
        return response.json()
    except Exception:
        return {}


# 싱글톤 인스턴스
_client: Optional[TossClient] = None


def get_toss_client() -> TossClient:
    """토스 클라이언트 싱글톤 인스턴스 반환"""
    global _client
    if _client is None:
        _client = TossClient()
    return _client
