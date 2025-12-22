"""
Stockio - 주식 시세 조회 중계 서비스

Google Spreadsheet와 키움증권 REST API 사이의 중계 서버
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="주식 시세 조회 중계 서비스 - Google Spreadsheet와 키움증권 API를 연결합니다.",
)

# CORS 설정 (Google Spreadsheet에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용하도록 변경 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info(f"{config.APP_NAME} v{config.APP_VERSION} 시작")
    logger.info(f"디버그 모드: {config.DEBUG}")
    logger.info(f"키움 API 호스트: {config.KIWOOM_API_HOST}")

    # 환경 변수 검증
    try:
        config.validate()
        logger.info("환경 변수 검증 완료")
    except ValueError as e:
        logger.error(f"환경 변수 검증 실패: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info(f"{config.APP_NAME} 종료")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "price": "/api/price?code={종목코드}&market={시장구분}",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level="info" if not config.DEBUG else "debug",
    )
