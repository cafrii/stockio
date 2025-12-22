# 주식 시세 조회 중계 서비스 (프로젝트 STOCK.io) 요구사항 문서

## 1. 개요

### 1.1 배경
- Google Spreadsheet에서 `IMPORTXML()` 함수를 통한 주식 시세 스크래핑이 웹사이트의 비동기 방식 변경으로 인해 동작하지 않음
- `GOOGLEFINANCE()` 함수는 일부 국내 주식/ETF를 지원하지 않음
- 증권사 OpenAPI를 활용하여 안정적인 시세 데이터 조회 필요

### 1.2 목적
Google Spreadsheet와 키움증권 REST API 간의 중계 서버를 구축하여 국내 주식/ETF의 현재 시세를 안정적으로 조회.
이 중계 서버를 본 문서에서는 Stockio 라고 부름.

### 1.3 시스템 아키텍처
```
[Google Spreadsheet] 
    ↓ (IMPORTXML)
[Stockio - Python FastAPI]
    ↓ (REST API)
[키움증권 OpenAPI Server]
```

---

## 2. 기능 요구사항

### 2.1 핵심 기능

#### 2.1.1 시세 조회 엔드포인트
- **목적**: Google Spreadsheet로부터 종목 코드를 받아 현재 시세를 반환
- **입력**: 
  - 종목 코드 (예: `005930` - 삼성전자)
  - 시장 구분 (예: `KOSPI`, `KOSDAQ`)
- **출력**: XML 형식의 현재 시세 데이터
- **처리 흐름**:
  1. Spreadsheet가 Stockio에 GET 요청 전송
  2. Stockio가 키움증권 REST API에 시세 조회 요청
  3. 키움증권 API로부터 받은 데이터를 XML로 변환
  4. Spreadsheet에 XML 응답 반환

#### 2.1.2 지원 대상
- **1차 목표 (현재 문제 해결)**:
  - 국내 주식 (KOSPI, KOSDAQ)
  - 국내 ETF

- **향후 확장 가능 영역** (Stockio 서버 동작이 안정화 된 경우):
  - KRX 금 현물 시세
  - 암호화폐 (비트코인, 이더리움)
  - 미국 주식/ETF (현재는 GOOGLEFINANCE로 해결 가능)

#### 2.1.3 조회 데이터 항목
- **Phase 1 (MVP)**:
  - 현재가 (종가)
  
- **Phase 2 (확장)**:
  - 시가, 고가, 저가
  - 전일 대비 등락률
  - 거래량
  - 시가총액

### 2.2 Spreadsheet 인터페이스 (사용자 측)

#### 2.2.1 사용 방법
Google Spreadsheet 셀 구성:
```
A1: 종목코드 (예: 005930)
B1: 시장구분 (예: KOSPI)
C1: =IMPORTXML("https://your-server.com/api/price?code="&A1&"&market="&B1, "//price")
```

#### 2.2.2 응답 XML 형식
```xml
<?xml version="1.0" encoding="UTF-8"?>
<stock>
  <code>005930</code>
  <price>71000</price>
  <timestamp>2025-12-22T14:30:00</timestamp>
</stock>
```

---

## 3. 기술 요구사항

### 3.1 개발 환경

#### 3.1.1 백엔드 프레임워크
- **선택지**: FastAPI
- **권장**: FastAPI
  - 비동기 처리 지원
  - 자동 API 문서화 (Swagger UI)
  - 타입 힌트 기반의 데이터 검증
  - 성능 우수

#### 3.1.2 개발 언어 및 버전
- Python 3.9+
- 주요 라이브러리:
  - `fastapi`
  - `uvicorn` (ASGI 서버)
  - `requests` (HTTP 클라이언트)
  - `python-dotenv` (환경 변수 관리)
  - `lxml` 또는 `xml.etree.ElementTree` (XML 생성)

### 3.2 외부 API 연동

#### 3.2.1 키움증권 REST API
- **API 버전**: 2025년 신규 개시 REST API
- **인증 방식**: API Key + Secret 기반
- **Rate Limit**: 
  - 기존 OpenAPI+ (OCX): 초당 5회, 시간당 ~1000회 제한
  - REST API: 공식 문서 확인 필요 (문서에서 명시되지 않음)
  - **대응 방안**: 
    - 요청 간 최소 간격 설정 (200ms)
    - 캐싱 메커니즘 구현

#### 3.2.2 API 엔드포인트 (예상)
```
GET /api/v1/market/stock/price
Parameters:
  - code: 종목코드
  - market: 시장구분
Headers:
  - Authorization: Bearer {access_token}
  - API-Key: {api_key}
```

### 3.3 배포 환경

#### 3.3.1 로컬 개발
- 로컬 머신에서 개발 및 테스트
- `uvicorn main:app --reload`

#### 3.3.2 프로덕션 배포
- **무료 호스팅 플랫폼 후보**:
  1. **Render** (권장)
     - 무료 티어 제공
     - Python/FastAPI 네이티브 지원
     - 자동 배포 (GitHub 연동)
     - HTTPS 자동 설정
     - 제약: Cold start (비활성 시 첫 요청 느림)
     
  2. **Railway**
     - 무료 티어 제공 (제한적)
     - 간편한 배포
     
  3. **Fly.io**
     - 무료 티어 제공
     - 글로벌 배포 지원

- **배포 요구사항**:
  - `requirements.txt` 파일 필수
  - 환경 변수 설정 (API Key, Secret)
  - Health check 엔드포인트 (`/health`)

---

## 4. 비기능 요구사항

### 4.1 성능

#### 4.1.1 응답 시간
- 목표: 2초 이내 (Stockio 처리 + 키움 API 응답)
- 캐싱 활용 시: 500ms 이내

#### 4.1.2 동시 처리
- 예상 부하: 100개 종목, 시간당 최대 100회 갱신
- Google Sheets IMPORTXML 자동 갱신: 시간당 1회

#### 4.1.3 캐싱 전략
- **목적**: API Rate Limit 회피 및 응답 속도 개선
- **방식**: 
  - In-memory 캐시 (Python `cachetools` 또는 `functools.lru_cache`)
  - TTL(Time To Live): 5분
  - 캐시 키: `{종목코드}_{시장구분}`

### 4.2 안정성

#### 4.2.1 에러 처리
모든 가능한 실패 시나리오에 대한 적절한 응답:

| 오류 상황 | HTTP 상태 코드 | XML 응답 예시 |
|----------|---------------|-------------|
| 종목 코드 없음 | 400 | `<error>종목 코드가 필요합니다</error>` |
| 잘못된 종목 코드 | 404 | `<error>종목을 찾을 수 없습니다</error>` |
| 키움 API 오류 | 502 | `<error>시세 조회 실패</error>` |
| Rate Limit 초과 | 429 | `<error>요청 한도 초과</error>` |
| 서버 내부 오류 | 500 | `<error>서버 오류</error>` |
| 시장 휴장 | 200 | `<price status="closed">이전 종가</price>` |

#### 4.2.2 로깅
- 요청/응답 로그
- 에러 로그
- API 호출 횟수 모니터링
- 로그 레벨: INFO, WARNING, ERROR

#### 4.2.3 장애 복구
- 키움 API 일시 장애 시 재시도 로직 (최대 3회, 지수 백오프)
- 캐시된 데이터 제공 (stale data 허용)

### 4.3 보안

#### 4.3.1 API 키 관리
- **환경 변수 방식** (개발/검증):
  - `.env` 파일에 저장
  - `.gitignore`에 `.env` 추가
  ```
  KIWOOM_API_KEY=your_api_key_here
  KIWOOM_API_SECRET=your_secret_here
  ```

- **프로덕션 환경**:
  - 호스팅 플랫폼의 환경 변수 관리 기능 사용
  - Render: Dashboard > Environment Variables
  - Railway: Settings > Variables

#### 4.3.2 접근 제어
- **Phase 1**: Public 엔드포인트 (보안 없음)
  - 개인용 스프레드시트만 사용하므로 URL만 알면 사용 가능
  
- **Phase 2** (선택 사항):
  - API Token 기반 인증
  - Rate Limiting (IP 기반)
  - CORS 정책 설정

#### 4.3.3 데이터 보안
- HTTPS 통신 필수 (호스팅 플랫폼 자동 제공)
- 민감 정보 로그 제외 (API Key, Secret)

### 4.4 확장성

#### 4.4.1 코드 구조
- 모듈화된 설계
  - API 클라이언트 (키움 API)
  - 비즈니스 로직 (시세 조회, 변환)
  - 라우터 (엔드포인트)
  - 유틸리티 (캐싱, 에러 처리)

#### 4.4.2 향후 확장 고려사항
- 여러 증권사 API 지원 (한국투자증권, 대신증권 등)
- 다양한 데이터 타입 (호가, 차트 데이터)
- Webhook 지원 (실시간 데이터 푸시)

---

## 5. 개발 일정

docs/milestone.md 참고


---

## 6. 테스트 계획

### 6.1 단위 테스트
- 키움 API 클라이언트 함수
- XML 변환 함수
- 캐싱 로직

### 6.2 통합 테스트
- 전체 요청/응답 플로우
- 다양한 종목 코드 (정상/비정상)
- 에러 시나리오

### 6.3 수동 테스트
- Google Spreadsheet에서 실제 조회
- 100개 종목 동시 조회
- 장 시간/장 외 시간 동작 확인

---

## 7. 운영 및 모니터링

### 7.1 모니터링 지표
- API 호출 횟수 (시간당/일간)
- 응답 시간 평균/최대
- 에러 발생률
- 캐시 히트율

### 7.2 알림
- 연속 에러 발생 시 (5회 이상)
- Rate Limit 근접 시 (80% 도달)
- 서버 다운 시

### 7.3 유지보수
- 로그 정기 확인 (주 1회)
- 키움 API 업데이트 모니터링
- 호스팅 플랫폼 상태 확인

---

## 8. 리스크 및 대응 방안

### 8.1 주요 리스크

| 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|--------|--------|------------|----------|
| 키움 API Rate Limit 초과 | 높음 | 중간 | 캐싱 + 요청 간격 제어 |
| 무료 호스팅 서비스 제한 | 중간 | 높음 | 여러 플랫폼 백업 계획 |
| 키움 API 정책 변경 | 높음 | 낮음 | API 문서 정기 확인 |
| Cold Start 지연 | 낮음 | 높음 | Health check ping 설정 |
| Google Sheets IMPORTXML 차단 | 높음 | 낮음 | 대체 방안 (Google Apps Script) |

### 8.2 백업 계획
- 여러 무료 호스팅 플랫폼에 동일 서버 배포
- 키움 API 외 다른 증권사 API 준비

---

## 9. 참고 자료

### 9.1 키움증권 API
- 키움 REST API 포털: https://openapi.kiwoom.com
- API 가이드 문서 (로그인 후 확인)

### 9.2 Google Spreadsheet
- IMPORTXML 함수는 문서가 열려 있는 동안 시간당 1회 자동 갱신
- 수동 갱신: 셀 삭제 후 Ctrl+Z (Undo)

### 9.3 무료 호스팅
- Render: https://render.com
- Railway: https://railway.app
- Fly.io: https://fly.io

### 9.4 기술 스택
- FastAPI: https://fastapi.tiangolo.com
- Uvicorn: https://www.uvicorn.org

---

## 10. 부록

### 10.1 예상 디렉토리 구조
```
stock-proxy-server/
├── main.py                 # FastAPI 애플리케이션 진입점
├── requirements.txt        # Python 의존성
├── .env                    # 환경 변수 (로컬 개발용)
├── .gitignore             # Git 제외 파일
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py      # API 엔드포인트
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py      # 설정 관리
│   │   └── cache.py       # 캐싱 로직
│   ├── services/
│   │   ├── __init__.py
│   │   └── kiwoom.py      # 키움 API 클라이언트
│   └── utils/
│       ├── __init__.py
│       ├── xml_builder.py # XML 생성
│       └── logger.py      # 로깅
└── tests/
    ├── __init__.py
    ├── test_api.py
    └── test_kiwoom.py
```

### 10.2 샘플 코드 (FastAPI)
```python
# main.py
from fastapi import FastAPI
from app.api import routes

app = FastAPI(title="Stock Price Proxy Server")

app.include_router(routes.router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

```python
# app/api/routes.py
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from app.services.kiwoom import get_stock_price
from app.utils.xml_builder import build_xml_response

router = APIRouter()

@router.get("/price")
async def get_price(
    code: str = Query(..., description="종목 코드"),
    market: str = Query("KOSPI", description="시장 구분")
):
    try:
        price_data = await get_stock_price(code, market)
        xml_content = build_xml_response(price_data)
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
```

### 10.3 Google Spreadsheet 수식 예시
```
# 단일 종목 조회
=IMPORTXML("https://your-server.onrender.com/api/price?code=005930&market=KOSPI", "//price")

# 여러 종목 조회 (각 행에 종목 코드 입력)
A열: 종목코드
B열: =IMPORTXML("https://your-server.onrender.com/api/price?code="&A2&"&market=KOSPI", "//price")
```

---

## 11. 결론

본 요구사항 문서는 Google Spreadsheet와 키움증권 REST API를 연결하는 Stockio 개발을 위한 지침을 제공합니다. 

**핵심 목표**:
1. 국내 주식/ETF의 현재 시세를 안정적으로 조회
2. 무료 호스팅 환경에서 안정적 운영
3. 향후 확장 가능한 구조

**다음 단계**:
- [ ] 개발 환경 설정
- [ ] MVP 개발 시작
- [ ] 로컬 테스트 및 검증
- [ ] 프로덕션 배포

---

**문서 버전**: 1.0  
**작성일**: 2025-12-22  
**최종 수정일**: 2025-12-22