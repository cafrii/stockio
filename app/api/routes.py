"""
Stockio API 라우터

주식 시세 조회 및 헬스 체크 엔드포인트를 제공합니다.
"""
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import Response
import time
import logging

from app.services.kiwoom import get_kiwoom_client, KiwoomAPIError, AuthenticationError
from app.utils.xml_builder import build_stock_price_xml, build_error_xml

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


@router.get("/api/price")
async def get_stock_price(
    code: str = Query(..., description="종목 코드 (예: 005930)", min_length=6, max_length=6),
    market: str = Query("KOSPI", description="시장 구분 (KOSPI, KOSDAQ)"),
):
    """
    주식 현재가 조회 엔드포인트

    Args:
        code: 종목 코드 (6자리)
        market: 시장 구분 (기본값: KOSPI)

    Returns:
        XML 응답
        <?xml version="1.0" encoding="UTF-8"?>
        <stock>
          <code>005930</code>
          <price>71000</price>
          <timestamp>2025-12-22T14:30:00</timestamp>
          <market>KOSPI</market>
        </stock>

    Raises:
        HTTPException: 에러 발생 시
    """
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
        # 키움 클라이언트 획득
        client = get_kiwoom_client()

        # 시세 조회 (비동기)
        price_data = await client.get_stock_price(code=code, market=market)

        # XML 변환
        xml_content = build_stock_price_xml(price_data)

        # 로그
        logger.info(f"시세 조회 성공: {code} ({market}) = {price_data['price']}")

        return Response(content=xml_content, media_type="application/xml")

    except AuthenticationError as e:
        logger.error(f"인증 실패: {e}")
        error_xml = build_error_xml(
            message="인증에 실패했습니다.",
            code=401,
            detail=str(e),
        )
        return Response(content=error_xml, media_type="application/xml", status_code=401)

    except KiwoomAPIError as e:
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
