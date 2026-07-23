"""
증권사 API 공통 인터페이스

여러 증권사(키움, 토스 등) 클라이언트를 동일한 방식으로 사용하기 위한
추상 베이스 클래스와 공통 예외를 정의한다.

각 provider 구현체는 StockProvider를 상속하고 get_stock_price()를 구현하며,
동일한 스키마의 딕셔너리를 반환해야 한다.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class StockProviderError(Exception):
    """증권사 API 공통 에러 (모든 provider 에러의 베이스)"""
    pass


class ProviderAuthError(StockProviderError):
    """증권사 API 인증 에러"""
    pass


class StockProvider(ABC):
    """
    증권사 시세 provider 공통 인터페이스

    구현체는 클래스 속성 `name`(provider 식별자)을 정의하고
    get_stock_price()를 구현한다.
    """

    #: provider 식별자 (예: "kiwoom", "toss"). 구현체에서 반드시 지정.
    name: str = ""

    @abstractmethod
    async def get_stock_price(self, code: str, market: str = "KOSPI") -> Dict[str, Any]:
        """
        주식 현재가(및 가능 시 52주 최고가) 조회

        Args:
            code: 종목 코드 (예: "005930")
            market: 시장 구분 ("KOSPI", "KOSDAQ")

        Returns:
            provider와 무관하게 동일한 스키마의 딕셔너리:
            {
                "code": "005930",
                "price": 54300,
                "high52w": 88800 | None,      # 미제공 provider는 None
                "low52w": 49900 | None,       # 52주 최저가
                "high52w_date": "20240711" | None,
                "timestamp": "2026-07-23T14:30:00",
                "market": "KOSPI",
                "provider": "kiwoom",
            }

        Raises:
            ProviderAuthError: 인증 실패
            StockProviderError: 그 외 API 호출 실패
        """
        raise NotImplementedError


def normalize_price(value: Optional[str]) -> Optional[float]:
    """
    가격 문자열을 숫자로 정규화 (부호/콤마 제거, 정수면 int로 반환)

    키움은 "+88800"/"-54300", 토스는 "72000"/"180.5" 등 표기가 달라
    공통 파서로 흡수한다.

    Args:
        value: 가격 문자열

    Returns:
        int(정수인 경우) 또는 float, 파싱 실패 시 None
    """
    if value is None:
        return None
    try:
        num = abs(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None
    # 정수면 int로 (기존 키움 응답과 표기 호환)
    return int(num) if num == int(num) else num
