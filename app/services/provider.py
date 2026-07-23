"""
증권사 provider 팩토리

provider 이름("kiwoom" | "toss")으로 해당 StockProvider 싱글톤을 반환한다.
provider 미지정 시 config.DEFAULT_PROVIDER(환경 변수로 변경 가능)를 사용한다.
"""
from typing import Optional, List

from app.core.config import config
from app.services.base import StockProvider, StockProviderError
from app.services.kiwoom import get_kiwoom_client
from app.services.toss import get_toss_client

# provider 이름 → 싱글톤 팩토리 함수 매핑
_PROVIDERS = {
    "kiwoom": get_kiwoom_client,
    "toss": get_toss_client,
}


def available_providers() -> List[str]:
    """지원하는 provider 이름 목록"""
    return list(_PROVIDERS.keys())


def resolve_provider_name(name: Optional[str]) -> str:
    """provider 이름 정규화 (미지정 시 기본값 적용)"""
    if not name:
        return config.DEFAULT_PROVIDER
    return name.strip().lower()


def get_provider(name: Optional[str] = None) -> StockProvider:
    """
    provider 이름으로 StockProvider 인스턴스 반환

    Args:
        name: "kiwoom" | "toss" | None(기본값 사용)

    Returns:
        StockProvider 구현체 싱글톤

    Raises:
        StockProviderError: 지원하지 않는 provider
    """
    resolved = resolve_provider_name(name)
    factory = _PROVIDERS.get(resolved)
    if factory is None:
        raise StockProviderError(
            f"지원하지 않는 provider입니다: '{resolved}'. 사용 가능: {available_providers()}"
        )
    return factory()
