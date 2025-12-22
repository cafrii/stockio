# 프로젝트 아키텍처

## 시스템 아키텍처

```
[Google Spreadsheet]
    ↓ (IMPORTXML)
[Stockio - FastAPI Server]
    ↓ (REST API)
[키움증권 OpenAPI Server]
```

**Stockio**는 Google Spreadsheet와 키움증권 REST API 사이의 중계 서버 역할을 합니다.

---

## 디렉토리 구조

```
test-api-kiwoom/
├── main.py                 # FastAPI 애플리케이션 진입점
├── requirements.txt        # Python 의존성
├── .env                    # 환경 변수 (로컬 개발용, Git 제외)
├── .gitignore             # Git 제외 파일
├── README.md              # 프로젝트 개요
│
├── app/                   # 메인 애플리케이션 패키지
│   ├── __init__.py
│   │
│   ├── api/              # API 라우터
│   │   ├── __init__.py
│   │   └── routes.py     # 엔드포인트 정의 (/api/price, /health)
│   │
│   ├── core/             # 핵심 설정 및 유틸리티
│   │   ├── __init__.py
│   │   ├── config.py     # 환경 변수 및 설정 관리
│   │   └── cache.py      # 캐싱 로직 (Phase 2에서 구현)
│   │
│   ├── services/         # 외부 서비스 연동
│   │   ├── __init__.py
│   │   └── kiwoom.py     # 키움 API 클라이언트 (PoC 코드 재사용)
│   │
│   └── utils/            # 유틸리티 함수
│       ├── __init__.py
│       ├── xml_builder.py # XML 응답 생성
│       └── logger.py     # 로깅 (Phase 2에서 강화)
│
├── tests/                # 테스트 코드 (Phase 1.2에서 작성)
│   ├── __init__.py
│   ├── test_api.py      # API 엔드포인트 테스트
│   └── test_kiwoom.py   # 키움 API 클라이언트 테스트
│
├── docs/                # 프로젝트 문서
│   ├── project.md       # 프로젝트 개요 및 목표
│   ├── stockio_prd.md   # 요구사항 문서
│   ├── milestone.md     # 마일스톤
│   ├── architecture.md  # 아키텍처 문서 (이 파일)
│   ├── poc_summary.md   # PoC 요약
│   └── status.md        # 진행 상황 (작성 예정)
│
└── poc/                 # PoC 코드 (참고용)
    ├── src/
    └── docs/
```

---

## 모듈 역할

### 1. `main.py`
- FastAPI 애플리케이션 진입점
- 라우터 등록
- CORS, 미들웨어 설정 (필요시)

### 2. `app/api/routes.py`
- `/api/price`: 주식 시세 조회 엔드포인트
  - Query 파라미터: `code` (종목코드), `market` (시장구분)
  - Response: XML 형식
- `/health`: 헬스 체크 엔드포인트

### 3. `app/services/kiwoom.py`
- 키움 API 클라이언트 모듈
- 기능:
  - 토큰 발급 및 관리
  - 시세 조회 API 호출
  - API 에러 처리
- PoC 코드 재사용 (`poc/src/` 참고)

### 4. `app/utils/xml_builder.py`
- XML 응답 생성 함수
- 정상 응답 XML 생성
- 에러 응답 XML 생성

### 5. `app/core/config.py`
- 환경 변수 관리 (`python-dotenv` 사용)
- 설정 클래스 정의 (`pydantic` 활용 가능)
- 예:
  ```python
  KIWOOM_API_APPKEY
  KIWOOM_API_SECRET
  KIWOOM_API_HOST
  ```

### 6. `app/core/cache.py` (Phase 2)
- 인메모리 캐싱 구현
- TTL 5분 설정

### 7. `app/utils/logger.py` (Phase 2)
- 로깅 설정
- 요청/응답/에러 로그

---

## 데이터 흐름

### 정상 시나리오
```
1. Google Spreadsheet
   ↓ IMPORTXML("https://stockio.com/api/price?code=005930&market=KOSPI")
2. Stockio API Router (routes.py)
   ↓ 파라미터 검증
3. Kiwoom API Client (kiwoom.py)
   ↓ 토큰 확인 → 시세 조회 API 호출
4. 키움증권 서버
   ↓ JSON 응답
5. XML Builder (xml_builder.py)
   ↓ JSON → XML 변환
6. Google Spreadsheet
   ↓ XML 파싱 후 셀에 표시
```

### 에러 시나리오
```
1. 잘못된 종목 코드 입력
   ↓
2. Stockio: 파라미터 검증 실패
   ↓
3. HTTP 400 + 에러 XML 응답
```

---

## API 명세

### `/api/price`

**Request:**
```
GET /api/price?code=005930&market=KOSPI
```

**Response (정상):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<stock>
  <code>005930</code>
  <price>71000</price>
  <timestamp>2025-12-22T14:30:00</timestamp>
</stock>
```

**Response (에러):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<error>
  <message>종목 코드가 필요합니다</message>
  <code>400</code>
</error>
```

### `/health`

**Request:**
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T14:30:00"
}
```

---

## 환경 변수

`.env` 파일 형식:

```bash
# 키움 API 인증 정보
KIWOOM_API_APPKEY=your_appkey_here
KIWOOM_API_SECRET=your_secret_here

# 키움 API 호스트 (실전/모의투자)
KIWOOM_API_HOST=https://openapi.kiwoom.com

# 토큰 저장 경로 (PoC에서 사용)
KIWOOM_TOKEN_ENV=/tmp/.kiwoom_env
```

---

## 기술 스택

| 항목 | 기술 |
|-----|------|
| 언어 | Python 3.14 |
| 웹 프레임워크 | FastAPI |
| ASGI 서버 | Uvicorn |
| HTTP 클라이언트 | requests |
| 환경 변수 관리 | python-dotenv |
| XML 생성 | xml.etree.ElementTree |
| 가상 환경 | venv + pip |

---

## 배포 구조

### 로컬 개발
```
localhost:8000
├── /api/price
└── /health
```

### 프로덕션 (Render)
```
https://stockio-xyz.onrender.com
├── /api/price
└── /health
```

---

## 보안 고려사항

1. **API Key 관리**
   - `.env` 파일 사용
   - Git에서 제외 (`.gitignore`)
   - 프로덕션: 호스팅 플랫폼의 환경 변수 기능

2. **토큰 관리**
   - 토큰 파일 `/tmp/.kiwoom_env`는 PoC 용도
   - 프로덕션에서는 메모리 캐싱 또는 Redis 고려

3. **HTTPS**
   - 로컬: HTTP (개발용)
   - 프로덕션: HTTPS (호스팅 플랫폼 자동 제공)

---

## PoC 코드 재사용 계획

PoC에서 검증된 기능을 `app/services/kiwoom.py`로 통합:

1. **토큰 관리**
   - `poc/src/get_token.py` 참고
   - 토큰 발급, 저장, 재사용 로직

2. **시세 조회**
   - `poc/src/query_*.py` 참고
   - 현재가 조회 API 호출 로직

3. **에러 처리**
   - `poc/docs/Errors.md` 참고
   - 리턴 코드별 처리

---

## 다음 단계

Phase 1.0 완료 후:
- [ ] Phase 1.1: 핵심 기능 구현 (main.py, routes.py, kiwoom.py, xml_builder.py)
- [ ] Phase 1.2: 단위 시험
- [ ] Phase 1.3: 로컬 E2E 테스트
- [ ] Phase 1.4: 배포
