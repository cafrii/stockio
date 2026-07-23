"""
토스증권 Open API 클라이언트

토스증권 Open API 1.2.4 (docs/toss_openapi_3.1.0.json) 기준으로 작성.
키움 클라이언트와 동일한 StockProvider 인터페이스를 구현하여 이중화한다.

주의: 토스 현재가 API(/api/v1/prices)는 현재가만 제공하며 52주 최고가는
제공하지 않는다. 따라서 high52w / high52w_date는 항상 None으로 반환한다.
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
    # 시세 조회
    # ------------------------------------------------------------------
    async def get_stock_price(self, code: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        현재가 조회 (GET /api/v1/prices?symbols=...)

        토스는 52주 최고가를 제공하지 않으므로 high52w/high52w_date는 None.
        """
        logger.info(f"[toss] 시세 조회 시작: code={code}, market={market}")
        token = await self.get_token()

        url = f"{self.api_host}/api/v1/prices"
        params = {"symbols": code}

        def _headers(tok: str) -> Dict[str, str]:
            return {"Authorization": f"Bearer {tok}", "Accept": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=_headers(token), params=params, timeout=10.0)

                # 401 인증 만료 → 토큰 재발급 후 1회 재시도
                if response.status_code == 401:
                    logger.warning("[toss] HTTP 401 - 토큰 재발급 후 재시도")
                    token = await self.get_token(force_new=True)
                    response = await client.get(url, headers=_headers(token), params=params, timeout=10.0)

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

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        logger.info(f"[toss] 시세 조회 성공: code={code}, price={price}")

        return {
            "code": code,
            "price": price,
            "high52w": None,        # 토스 미제공
            "high52w_date": None,   # 토스 미제공
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
