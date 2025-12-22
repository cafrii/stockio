"""
키움증권 REST API 클라이언트

PoC 코드(poc/src/get_token.py)를 참고하여 작성되었습니다.
"""
import os
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from app.core.config import config


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

    def _load_token_from_file(self) -> Optional[str]:
        """파일에서 저장된 토큰 로드"""
        if not os.path.isfile(self.token_file):
            return None

        if not os.access(self.token_file, os.R_OK):
            return None

        # 토큰 파일 로드
        load_dotenv(self.token_file, override=True)
        token = os.getenv("KIWOOM_API_TOKEN")
        expire_at = os.getenv("KIWOOM_API_EXPIRE_AT")

        if not token or not expire_at:
            return None

        # 만료 시간 확인
        now = time.strftime("%Y%m%d%H%M%S")
        if expire_at < now:
            return None

        self._token = token
        self._token_expire_at = expire_at
        return token

    def _save_token_to_file(self, token: str, expire_at: str):
        """토큰을 파일에 저장"""
        with open(self.token_file, "w") as f:
            f.write(f"KIWOOM_API_TOKEN = {token}\n")
            f.write(f"KIWOOM_API_EXPIRE_AT = {expire_at}\n")

        self._token = token
        self._token_expire_at = expire_at

    def _request_new_token(self) -> str:
        """새 토큰 발급 요청"""
        url = f"{self.api_host}/oauth2/token"
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "secretkey": self.secret,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            raise KiwoomAPIError(f"토큰 요청 실패: {e}")

        result = response.json()

        # 응답 검증
        if result.get("return_code") != 0:
            raise AuthenticationError(f"토큰 발급 실패: {result.get('return_msg')}")

        if result.get("token_type") != "Bearer":
            raise AuthenticationError(f"잘못된 토큰 타입: {result.get('token_type')}")

        token = result.get("token")
        expire_at = result.get("expires_dt")

        if not token or not expire_at:
            raise AuthenticationError("토큰 또는 만료 시간이 없습니다")

        # 파일에 저장
        self._save_token_to_file(token, expire_at)

        return token

    def get_token(self, force_new: bool = False) -> str:
        """
        토큰 획득 (캐시된 토큰 재사용 또는 새로 발급)

        Args:
            force_new: True일 경우 강제로 새 토큰 발급

        Returns:
            액세스 토큰 문자열

        Raises:
            AuthenticationError: 인증 실패
            KiwoomAPIError: API 호출 실패
        """
        # 메모리에 캐시된 토큰 확인
        if not force_new and self._token:
            now = time.strftime("%Y%m%d%H%M%S")
            if self._token_expire_at and self._token_expire_at > now:
                return self._token

        # 파일에서 토큰 로드
        if not force_new:
            token = self._load_token_from_file()
            if token:
                return token

        # 새 토큰 발급
        return self._request_new_token()

    def get_stock_price(self, code: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        주식 현재가 조회

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
        # 토큰 획득
        token = self.get_token()

        # API 호출
        # 참고: 실제 키움 API 엔드포인트는 문서 확인 필요
        # 여기서는 일반적인 패턴으로 구현
        url = f"{self.api_host}/uapi/domestic-stock/v1/quotations/inquire-price"

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {token}",
            "appkey": self.appkey,
            "appsecret": self.secret,
        }

        params = {
            "fid_cond_mrkt_div_code": "J",  # 주식, 선물옵션, 채권 등 구분
            "fid_input_iscd": code,  # 종목코드
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)

            # 인증 에러 체크
            if response.status_code == 401:
                # 토큰 만료 가능성 - 재시도
                token = self.get_token(force_new=True)
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(url, headers=headers, params=params, timeout=10)

            response.raise_for_status()

        except requests.RequestException as e:
            raise KiwoomAPIError(f"시세 조회 실패: {e}")

        result = response.json()

        # 응답 검증
        return_code = result.get("rt_cd") or result.get("return_code")
        if return_code != "0" and return_code != 0:
            return_msg = result.get("msg1") or result.get("return_msg") or "알 수 없는 오류"
            raise KiwoomAPIError(f"시세 조회 실패: {return_msg}")

        # 데이터 추출 (실제 응답 구조에 따라 조정 필요)
        output = result.get("output") or {}

        # 현재가 추출
        current_price = output.get("stck_prpr") or output.get("price")

        if not current_price:
            raise KiwoomAPIError("현재가 데이터를 찾을 수 없습니다")

        # 타임스탬프 생성
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

        return {
            "code": code,
            "price": int(current_price),
            "timestamp": timestamp,
            "market": market,
        }


# 싱글톤 인스턴스
_client: Optional[KiwoomClient] = None


def get_kiwoom_client() -> KiwoomClient:
    """키움 클라이언트 싱글톤 인스턴스 반환"""
    global _client
    if _client is None:
        _client = KiwoomClient()
    return _client
