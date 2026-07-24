"""
Stockio API 라우터

주식 시세 조회 및 헬스 체크 엔드포인트를 제공합니다.
"""
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import Response
import time
import logging

from app.services.kiwoom import get_kiwoom_client
from app.services.base import StockProviderError, ProviderAuthError
from app.services.provider import get_provider, available_providers, resolve_provider_name
from app.services import gold as gold_service
from app.services.scraper import (
    get_scraper,
    ScrapeError,
    ScrapeConfigError,
    ScrapeFetchError,
    ScrapeExtractError,
)
from app.utils.xml_builder import (
    build_stock_price_xml,
    build_error_xml,
    build_scrape_xml,
    build_scrape_list_xml,
)

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트

    Returns:
        JSON 응답
        {
            "status": "healthy",
            "timestamp": "2025-12-22T14:30:00"
        }
    """
    return {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "service": "Stockio",
    }


@router.get("/debug/ip")
async def get_server_ip():
    """
    서버의 아웃바운드 IP 주소 확인 (디버그용)

    Returns:
        JSON 응답 - 서버의 공인 IP 주소
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            # 여러 IP 확인 서비스 시도
            services = [
                "https://api.ipify.org?format=json",
                "https://ifconfig.me/ip",
                "https://icanhazip.com",
            ]

            results = {}
            for service in services:
                try:
                    response = await client.get(service, timeout=5.0)
                    if response.status_code == 200:
                        if "ipify" in service:
                            results[service] = response.json()
                        else:
                            results[service] = {"ip": response.text.strip()}
                except Exception as e:
                    results[service] = {"error": str(e)}

            return {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "services": results,
            }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


@router.get("/debug/token-status")
async def get_token_status():
    """
    토큰 상태 확인 (디버그용)

    Returns:
        JSON 응답 - 토큰 상태 정보
    """
    try:
        client = get_kiwoom_client()
        status = client.get_token_status()
        return status
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


@router.post("/debug/force-expire-token")
async def force_expire_token():
    """
    토큰 강제 만료 (테스트용)

    메모리 캐시와 파일의 만료 시간을 과거로 설정하여
    토큰 재발급 로직을 테스트할 수 있습니다.

    Returns:
        JSON 응답 - 작업 결과
    """
    try:
        client = get_kiwoom_client()
        client.force_expire_token()
        return {
            "success": True,
            "message": "토큰이 강제로 만료되었습니다.",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


def _scrape_error_response(e: ScrapeError) -> Response:
    """스크래핑 예외를 XML 에러 응답으로 변환 (공통)"""
    if isinstance(e, ScrapeConfigError):
        # 설정에 없는 대상/그룹 → 요청 잘못
        status_code, message = 400, "스크래핑 설정 오류입니다."
    elif isinstance(e, ScrapeExtractError):
        # XPath 미매칭 → 페이지 구조 변경 가능성 (설정 갱신 필요)
        status_code, message = (
            502,
            "값 추출에 실패했습니다. 페이지 구조가 변경되었을 수 있습니다. "
            "config/scrape_targets.yaml의 xpath를 확인하세요.",
        )
    elif isinstance(e, ScrapeFetchError):
        status_code, message = 502, "대상 페이지 조회에 실패했습니다."
    else:
        status_code, message = 502, "스크래핑에 실패했습니다."

    error_xml = build_error_xml(message=message, code=status_code, detail=str(e))
    return Response(content=error_xml, media_type="application/xml", status_code=status_code)


@router.get("/api/gold")
async def get_gold_price(
    target: str = Query(
        None,
        description="금 시세 대상 (krx, international). 미지정 시 전체 반환",
    ),
    refresh: bool = Query(
        False,
        description="true면 캐시를 무시하고 새로 조회 (개발/검증용). 예: &refresh=1",
    ),
):
    """
    금 시세 조회 엔드포인트 (스크래핑 기반)

    대상 URL·XPath는 `config/scrape_targets.yaml`의 `groups.gold`에 정의되어 있으며
    코드에 하드코딩되지 않는다. 페이지 변경 시 설정만 갱신하면 된다.

    Args:
        target: 대상 키. 미지정 시 정의된 모든 대상을 반환
        refresh: true면 캐시 무시하고 새로 조회

    Returns:
        XML 응답
        <?xml version="1.0" encoding="UTF-8"?>
        <gold>
          <target>krx</target>
          <label>국내 금 시세 (KRX 금 현물)</label>
          <price>190990</price>
          <unit>원/g</unit>
          <currency>KRW</currency>
          <timestamp>2026-07-24T01:00:00</timestamp>
          <method>static</method>
        </gold>
    """
    try:
        # target 미지정 → 전체 조회 (동일 URL은 캐시로 1회만 요청)
        if not target:
            items = await gold_service.get_all_gold_prices(force_refresh=refresh)
            xml_content = build_scrape_list_xml(items, root_tag="golds", item_tag="gold")
            logger.info(f"금 시세 전체 조회 성공: {len(items)}건")
            return Response(content=xml_content, media_type="application/xml")

        data = await gold_service.get_gold_price(
            target.strip().lower(), force_refresh=refresh
        )
        xml_content = build_scrape_xml(data, root_tag="gold")
        logger.info(f"금 시세 조회 성공: {data['target']} = {data['value']}")
        return Response(content=xml_content, media_type="application/xml")

    except ScrapeError as e:
        logger.error(f"금 시세 조회 실패: {e}")
        return _scrape_error_response(e)

    except Exception as e:
        logger.exception(f"금 시세 조회 중 예상치 못한 에러: {e}")
        error_xml = build_error_xml(
            message="서버 내부 오류가 발생했습니다.", code=500, detail=str(e)
        )
        return Response(content=error_xml, media_type="application/xml", status_code=500)


@router.get("/api/scrape")
async def scrape_target(
    group: str = Query(..., description="자산 그룹 (예: gold, crypto)"),
    target: str = Query(None, description="대상 키. 미지정 시 그룹 전체 반환"),
    refresh: bool = Query(
        False,
        description="true면 캐시를 무시하고 새로 조회 (개발/검증용). 예: &refresh=1",
    ),
):
    """
    범용 스크래핑 엔드포인트

    설정 파일에 그룹/대상을 추가하기만 하면 코드 변경 없이 조회할 수 있다.
    (예: 가상자산 시세 등 증권사 API가 제공하지 않는 정보)

    Args:
        group: 자산 그룹 (설정의 `groups` 키)
        target: 대상 키. 미지정 시 그룹 내 전체

    Returns:
        XML 응답
    """
    try:
        scraper = get_scraper()
        group_key = group.strip().lower()

        if not target:
            items = await scraper.scrape_group(group_key, force_refresh=refresh)
            if not items:
                raise ScrapeConfigError(f"'{group_key}' 그룹에 정의된 대상이 없습니다.")
            xml_content = build_scrape_list_xml(items, root_tag="quotes", item_tag="quote")
            logger.info(f"스크래핑 그룹 조회 성공: {group_key} {len(items)}건")
            return Response(content=xml_content, media_type="application/xml")

        data = await scraper.scrape(
            group_key, target.strip().lower(), force_refresh=refresh
        )
        xml_content = build_scrape_xml(data, root_tag="quote")
        logger.info(f"스크래핑 조회 성공: {group_key}.{data['target']} = {data['value']}")
        return Response(content=xml_content, media_type="application/xml")

    except ScrapeError as e:
        logger.error(f"스크래핑 실패: {e}")
        return _scrape_error_response(e)

    except Exception as e:
        logger.exception(f"스크래핑 중 예상치 못한 에러: {e}")
        error_xml = build_error_xml(
            message="서버 내부 오류가 발생했습니다.", code=500, detail=str(e)
        )
        return Response(content=error_xml, media_type="application/xml", status_code=500)


@router.get("/api/price")
async def get_stock_price(
    code: str = Query(..., description="종목 코드 (예: 005930)", min_length=6, max_length=6),
    market: str = Query("KOSPI", description="시장 구분 (KOSPI, KOSDAQ)"),
    provider: str = Query(None, description="증권사 provider (kiwoom, toss). 미지정 시 서버 기본값"),
):
    """
    주식 현재가 조회 엔드포인트

    Args:
        code: 종목 코드 (6자리)
        market: 시장 구분 (기본값: KOSPI)
        provider: 증권사 provider (kiwoom, toss). 미지정 시 서버 기본값(DEFAULT_PROVIDER)

    Returns:
        XML 응답
        <?xml version="1.0" encoding="UTF-8"?>
        <stock>
          <code>005930</code>
          <price>71000</price>
          <timestamp>2025-12-22T14:30:00</timestamp>
          <market>KOSPI</market>
          <provider>kiwoom</provider>
        </stock>

    Raises:
        HTTPException: 에러 발생 시
    """
    # provider 검증 (미지정 시 기본값 적용)
    provider_name = resolve_provider_name(provider)
    if provider_name not in available_providers():
        error_xml = build_error_xml(
            message=f"유효하지 않은 provider입니다. 사용 가능: {', '.join(available_providers())}",
            code=400,
        )
        return Response(content=error_xml, media_type="application/xml", status_code=400)

    # 시장 구분 검증 및 변환
    market = market.upper()

    # 약어 변환 (J=KOSPI, Q=KOSDAQ)
    market_mapping = {
        "J": "KOSPI",
        "Q": "KOSDAQ",
        "KOSPI": "KOSPI",
        "KOSDAQ": "KOSDAQ",
    }

    if market not in market_mapping:
        error_xml = build_error_xml(
            message="유효하지 않은 시장 구분입니다. KOSPI, KOSDAQ, J, Q만 가능합니다.",
            code=400,
        )
        return Response(content=error_xml, media_type="application/xml", status_code=400)

    market = market_mapping[market]  # 약어를 정식 명칭으로 변환

    try:
        # provider 클라이언트 획득 (kiwoom | toss)
        client = get_provider(provider_name)

        # 시세 조회 (비동기)
        price_data = await client.get_stock_price(code=code, market=market)

        # XML 변환
        xml_content = build_stock_price_xml(price_data)

        # 로그
        logger.info(f"시세 조회 성공: {code} ({market}) [{provider_name}] = {price_data['price']}")

        return Response(content=xml_content, media_type="application/xml")

    except ProviderAuthError as e:
        logger.error(f"인증 실패: {e}")
        error_xml = build_error_xml(
            message="인증에 실패했습니다.",
            code=401,
            detail=str(e),
        )
        return Response(content=error_xml, media_type="application/xml", status_code=401)

    except StockProviderError as e:
        logger.error(f"API 에러: {e}")
        error_xml = build_error_xml(
            message="시세 조회에 실패했습니다.",
            code=502,
            detail=str(e),
        )
        return Response(content=error_xml, media_type="application/xml", status_code=502)

    except Exception as e:
        logger.exception(f"예상치 못한 에러: {e}")
        error_xml = build_error_xml(
            message="서버 내부 오류가 발생했습니다.",
            code=500,
            detail=str(e),
        )
        return Response(content=error_xml, media_type="application/xml", status_code=500)
