"""
키움증권 REST API 클라이언트

PoC 코드(poc/src/get_token.py)를 참고하여 작성되었습니다.
비동기 HTTP 클라이언트(httpx)를 사용하여 완전한 비동기 처리를 지원합니다.
"""
import os
import time
import httpx
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from app.core.config import config

# 로거 설정
logger = logging.getLogger(__name__)


class KiwoomAPIError(Exception):
    """키움 API 에러"""
    pass


class AuthenticationError(KiwoomAPIError):
    """인증 에러"""
    pass


class KiwoomClient:
    """키움증권 API 클라이언트"""

    def __init__(self):
        self.api_host = config.KIWOOM_API_HOST
        self.appkey = config.KIWOOM_API_APPKEY
        self.secret = config.KIWOOM_API_SECRET
        self.token_file = config.KIWOOM_TOKEN_ENV
        self._token: Optional[str] = None
        self._token_expire_at: Optional[str] = None
        self._last_token_issued_at: Optional[str] = None  # 마지막 토큰 발급 시간

    def _load_token_from_file(self) -> Optional[str]:
        """파일에서 저장된 토큰 로드"""
        logger.debug(f"토큰 파일 로드 시도: {self.token_file}")

        if not os.path.isfile(self.token_file):
            logger.debug("토큰 파일이 존재하지 않음")
            return None

        if not os.access(self.token_file, os.R_OK):
            logger.warning("토큰 파일 읽기 권한 없음")
            return None

        # 토큰 파일 로드
        load_dotenv(self.token_file, override=True)
        token = os.getenv("KIWOOM_API_TOKEN")
        expire_at = os.getenv("KIWOOM_API_EXPIRE_AT")

        if not token or not expire_at:
            logger.warning("토큰 파일에 토큰 또는 만료 시간이 없음")
            return None

        # 만료 시간 확인
        now = time.strftime("%Y%m%d%H%M%S")
        if expire_at < now:
            logger.info(f"토큰 만료됨: expire_at={expire_at}, now={now}")
            # 만료된 토큰 파일 삭제
            try:
                os.remove(self.token_file)
                logger.info("만료된 토큰 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"만료된 토큰 파일 삭제 실패: {e}")
            return None

        logger.info(f"토큰 파일 로드 성공: expire_at={expire_at}")
        self._token = token
        self._token_expire_at = expire_at
        return token

    def _save_token_to_file(self, token: str, expire_at: str):
        """토큰을 파일에 저장"""
        logger.info(f"토큰 파일 저장: expire_at={expire_at}")
        with open(self.token_file, "w") as f:
            f.write(f"KIWOOM_API_TOKEN = {token}\n")
            f.write(f"KIWOOM_API_EXPIRE_AT = {expire_at}\n")

        self._token = token
        self._token_expire_at = expire_at
        self._last_token_issued_at = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info("토큰 파일 저장 완료")

    async def _request_new_token(self) -> str:
        """새 토큰 발급 요청 (비동기)"""
        logger.info("새 토큰 발급 요청 시작")
        url = f"{self.api_host}/oauth2/token"
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.secret,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data, timeout=10.0)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"토큰 요청 HTTP 에러: {e}")
            raise KiwoomAPIError(f"토큰 요청 실패: {e}")

        result = response.json()

        # 응답 검증
        if result.get("return_code") != 0:
            logger.error(f"토큰 발급 실패: return_code={result.get('return_code')}, msg={result.get('return_msg')}")
            raise AuthenticationError(f"토큰 발급 실패: {result.get('return_msg')}")

        if result.get("token_type") != "Bearer":
            logger.error(f"잘못된 토큰 타입: {result.get('token_type')}")
            raise AuthenticationError(f"잘못된 토큰 타입: {result.get('token_type')}")

        token = result.get("token")
        expire_at = result.get("expires_dt")

        if not token or not expire_at:
            logger.error("토큰 또는 만료 시간이 응답에 없음")
            raise AuthenticationError("토큰 또는 만료 시간이 없습니다")

        logger.info(f"새 토큰 발급 성공: expire_at={expire_at}")

        # 파일에 저장
        self._save_token_to_file(token, expire_at)

        return token

    async def get_token(self, force_new: bool = False) -> str:
        """
        토큰 획득 (캐시된 토큰 재사용 또는 새로 발급) - 비동기

        Args:
            force_new: True일 경우 강제로 새 토큰 발급

        Returns:
            액세스 토큰 문자열

        Raises:
            AuthenticationError: 인증 실패
            KiwoomAPIError: API 호출 실패
        """
        logger.debug(f"토큰 획득 시작: force_new={force_new}")

        # 메모리에 캐시된 토큰 확인
        if not force_new and self._token:
            now = time.strftime("%Y%m%d%H%M%S")
            if self._token_expire_at and self._token_expire_at > now:
                logger.debug("메모리 캐시 토큰 사용")
                return self._token
            else:
                logger.debug(f"메모리 캐시 토큰 만료됨: expire_at={self._token_expire_at}, now={now}")

        # 파일에서 토큰 로드
        if not force_new:
            token = self._load_token_from_file()
            if token:
                logger.debug("파일에서 로드한 토큰 사용")
                return token

        # 새 토큰 발급
        logger.info("새 토큰 발급 필요")
        return await self._request_new_token()

    async def get_stock_price(self, code: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        주식 현재가 조회 (비동기)

        Args:
            code: 종목 코드 (예: "005930")
            market: 시장 구분 ("KOSPI", "KOSDAQ")

        Returns:
            시세 데이터 딕셔너리
            {
                "code": "005930",
                "price": 71000,
                "timestamp": "2025-12-22T14:30:00"
            }

        Raises:
            KiwoomAPIError: API 호출 실패
            AuthenticationError: 인증 실패
        """
        logger.info(f"시세 조회 시작: code={code}, market={market}")

        # 토큰 획득
        token = await self.get_token()

        # API 호출 - PoC 패턴 적용
        # 현재가 조회 API ID는 문서 확인 필요 (예상: km10XXX 또는 kq10XXX)
        # 일단 일봉 조회 API를 사용하여 가장 최근 종가를 현재가로 사용
        url = f"{self.api_host}/api/dostk/chart"

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "cont-yn": "N",
            "next-key": "",
            "api-id": "ka10081",  # 일봉 차트 조회
        }

        # 오늘 날짜 기준 조회
        base_dt = time.strftime("%Y%m%d")

        data = {
            "stk_cd": code,
            "base_dt": base_dt,
            "upd_stkpc_tp": "1",  # 수정주가구분
        }

        # 재시도 플래그
        retry_attempted = False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data, timeout=10.0)
                logger.debug(f"API 응답 상태 코드: {response.status_code}")

                # HTTP 401 인증 에러 체크
                if response.status_code == 401:
                    logger.warning("HTTP 401 인증 에러 발생 - 토큰 재발급 시도")
                    token = await self.get_token(force_new=True)
                    headers["authorization"] = f"Bearer {token}"
                    response = await client.post(url, headers=headers, json=data, timeout=10.0)
                    logger.info("토큰 재발급 후 재시도 완료")
                    retry_attempted = True

                if response.status_code != 200:
                    logger.error(f"HTTP 상태 코드 에러: {response.status_code}")
                    raise KiwoomAPIError(f"HTTP 상태 코드: {response.status_code}")

                result = response.json()
                logger.debug(f"API 응답: return_code={result.get('return_code')}")

                # 응답 검증
                return_code = result.get("return_code")
                if return_code != 0:
                    return_msg = result.get("return_msg") or "알 수 없는 오류"
                    logger.warning(f"API 에러 응답: return_code={return_code}, msg={return_msg}")

                    # return_code=3 인증 에러 - 재시도
                    if return_code == 3 and not retry_attempted:
                        logger.warning("return_code=3 인증 실패 감지 - 토큰 재발급 시도")
                        token = await self.get_token(force_new=True)
                        headers["authorization"] = f"Bearer {token}"
                        response = await client.post(url, headers=headers, json=data, timeout=10.0)
                        logger.info("토큰 재발급 후 재시도 완료")

                        if response.status_code != 200:
                            logger.error(f"재시도 후 HTTP 상태 코드 에러: {response.status_code}")
                            raise KiwoomAPIError(f"HTTP 상태 코드: {response.status_code}")

                        result = response.json()
                        return_code = result.get("return_code")
                        logger.debug(f"재시도 후 API 응답: return_code={return_code}")

                        if return_code != 0:
                            return_msg = result.get("return_msg") or "알 수 없는 오류"
                            logger.error(f"재시도 후에도 API 에러: return_code={return_code}, msg={return_msg}")
                            if return_code == 3:
                                raise AuthenticationError(f"인증 실패: {return_msg}")
                            raise KiwoomAPIError(f"시세 조회 실패: [{return_code}] {return_msg}")

                    elif return_code == 3:
                        # 이미 재시도했는데도 실패
                        logger.error(f"재시도 후에도 인증 실패: {return_msg}")
                        raise AuthenticationError(f"인증 실패: {return_msg}")
                    else:
                        # 다른 에러 코드
                        logger.error(f"API 에러: [{return_code}] {return_msg}")
                        raise KiwoomAPIError(f"시세 조회 실패: [{return_code}] {return_msg}")

        except httpx.HTTPError as e:
            logger.error(f"HTTP 에러: {e}")
            raise KiwoomAPIError(f"시세 조회 실패: {e}")

        # 차트 데이터 추출
        chart_data = result.get("stk_dt_pole_chart_qry")
        if not isinstance(chart_data, list) or len(chart_data) == 0:
            logger.error("차트 데이터 없음")
            raise KiwoomAPIError("차트 데이터가 없습니다")

        # 가장 최근 데이터 (첫 번째 요소)
        latest = chart_data[0]

        # 종가를 현재가로 사용 (cur_prc: current price)
        current_price = latest.get("cur_prc")

        if not current_price:
            logger.error("현재가 데이터 없음")
            raise KiwoomAPIError("현재가 데이터를 찾을 수 없습니다")

        # 타임스탬프 생성
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        logger.info(f"시세 조회 성공: code={code}, price={current_price}")

        return {
            "code": code,
            "price": int(current_price),
            "timestamp": timestamp,
            "market": market,
            "date": latest.get("dt"),  # 조회 날짜
        }

    def get_token_status(self) -> Dict[str, Any]:
        """
        토큰 상태 조회 (디버깅용)

        Returns:
            토큰 상태 정보 딕셔너리
        """
        now = time.strftime("%Y%m%d%H%M%S")
        now_readable = time.strftime("%Y-%m-%d %H:%M:%S")

        status = {
            "current_time": now_readable,
            "memory_cache": {
                "token_exists": self._token is not None,
                "token_preview": self._token[:20] + "..." if self._token else None,
                "expire_at": self._token_expire_at,
                "is_expired": self._token_expire_at < now if self._token_expire_at else None,
            },
            "token_file": {
                "path": self.token_file,
                "exists": os.path.isfile(self.token_file),
                "readable": os.access(self.token_file, os.R_OK) if os.path.isfile(self.token_file) else False,
            },
            "last_token_issued_at": self._last_token_issued_at,
        }

        # 파일 내용 읽기 시도
        if status["token_file"]["exists"] and status["token_file"]["readable"]:
            try:
                with open(self.token_file, "r") as f:
                    content = f.read()
                    lines = content.strip().split("\n")
                    file_data = {}
                    for line in lines:
                        if "=" in line:
                            key, value = line.split("=", 1)
                            file_data[key.strip()] = value.strip()

                    file_expire_at = file_data.get("KIWOOM_API_EXPIRE_AT")
                    status["token_file"]["content"] = {
                        "token_preview": file_data.get("KIWOOM_API_TOKEN", "")[:20] + "..." if file_data.get("KIWOOM_API_TOKEN") else None,
                        "expire_at": file_expire_at,
                        "is_expired": file_expire_at < now if file_expire_at else None,
                    }
            except Exception as e:
                status["token_file"]["read_error"] = str(e)

        return status

    def force_expire_token(self):
        """
        토큰 강제 만료 (테스트용)

        메모리 캐시와 파일의 만료 시간을 과거 시간으로 변경
        """
        expired_time = "20000101000000"  # 2000-01-01 00:00:00

        # 메모리 캐시 만료
        if self._token:
            self._token_expire_at = expired_time

        # 파일 만료
        if os.path.isfile(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    content = f.read()

                # 토큰 값 추출
                token = None
                for line in content.split("\n"):
                    if "KIWOOM_API_TOKEN" in line and "=" in line:
                        token = line.split("=", 1)[1].strip()
                        break

                if token:
                    # 만료 시간을 과거로 설정하여 재저장
                    with open(self.token_file, "w") as f:
                        f.write(f"KIWOOM_API_TOKEN = {token}\n")
                        f.write(f"KIWOOM_API_EXPIRE_AT = {expired_time}\n")
            except Exception as e:
                raise KiwoomAPIError(f"토큰 파일 만료 처리 실패: {e}")


# 싱글톤 인스턴스
_client: Optional[KiwoomClient] = None


def get_kiwoom_client() -> KiwoomClient:
    """키움 클라이언트 싱글톤 인스턴스 반환"""
    global _client
    if _client is None:
        _client = KiwoomClient()
    return _client
