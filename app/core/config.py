"""
Stockio 설정 모듈

환경 변수를 관리하고 애플리케이션 설정을 제공합니다.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """애플리케이션 설정 클래스"""

    # 키움 API 설정
    KIWOOM_API_APPKEY: str = os.getenv("KIWOOM_API_APPKEY", "")
    KIWOOM_API_SECRET: str = os.getenv("KIWOOM_API_SECRET", "")
    KIWOOM_API_HOST: str = os.getenv("KIWOOM_API_HOST", "https://api.kiwoom.com")
    KIWOOM_TOKEN_ENV: str = os.getenv("KIWOOM_TOKEN_ENV", "/tmp/.kiwoom_env")

    # 토스증권 API 설정
    TOSS_API_CLIENT_ID: str = os.getenv("TOSS_API_CLIENT_ID", "")
    TOSS_API_SECRET: str = os.getenv("TOSS_API_SECRET", "")
    TOSS_API_HOST: str = os.getenv("TOSS_API_HOST", "https://openapi.tossinvest.com")
    TOSS_TOKEN_ENV: str = os.getenv("TOSS_TOKEN_ENV", "/tmp/.toss_env")

    # provider 선택 설정
    # /api/price 요청에 provider 파라미터가 없을 때 사용할 기본 provider.
    # 하드코딩 대신 환경 변수로 변경 가능 → 백엔드 설정 한 번으로 전체 교체.
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "kiwoom").lower()

    # 애플리케이션 설정
    APP_NAME: str = "Stockio"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 캐싱 설정 (Phase 2에서 사용)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # 5분

    # Rate Limiting (Phase 2에서 사용)
    MIN_REQUEST_INTERVAL: float = float(os.getenv("MIN_REQUEST_INTERVAL", "0.2"))  # 200ms

    @classmethod
    def validate(cls) -> bool:
        """필수 환경 변수 검증"""
        if not cls.KIWOOM_API_APPKEY:
            raise ValueError("KIWOOM_API_APPKEY가 설정되지 않았습니다.")
        if not cls.KIWOOM_API_SECRET:
            raise ValueError("KIWOOM_API_SECRET이 설정되지 않았습니다.")
        return True


# 설정 인스턴스
config = Config()
