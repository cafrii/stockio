"""
금 시세 서비스

범용 스크래퍼(app/services/scraper.py) 위에 얹은 얇은 도메인 계층.
대상 정의(URL·XPath·단위)는 전부 config/scrape_targets.yaml의 `groups.gold`에 있다.

향후 가상자산 등 다른 자산이 필요하면 이 파일과 같은 형태의 얇은 모듈을
하나 더 만들거나(예: crypto.py), 범용 엔드포인트(/api/scrape)를 그대로 쓰면 된다.
"""
import logging
from typing import Any, Dict, List, Optional

from app.services.scraper import get_scraper, ScrapeError, ScrapeConfigError

logger = logging.getLogger(__name__)

#: 금 시세가 정의된 설정 그룹 이름
GOLD_GROUP = "gold"


def available_targets() -> List[str]:
    """설정에 정의된 금 시세 대상 목록 (예: ["international", "krx"])"""
    return get_scraper().config.targets(GOLD_GROUP)


async def get_gold_price(target: str) -> Dict[str, Any]:
    """
    금 시세 1건 조회

    Args:
        target: 대상 키 (설정 기준. 예: "krx", "international")

    Returns:
        스크래핑 결과 딕셔너리 (scraper.scrape() 참고)

    Raises:
        ScrapeError 계열
    """
    return await get_scraper().scrape(GOLD_GROUP, target)


async def get_all_gold_prices() -> List[Dict[str, Any]]:
    """설정에 정의된 모든 금 시세 조회 (동일 URL은 캐시로 1회만 요청)"""
    return await get_scraper().scrape_group(GOLD_GROUP)
