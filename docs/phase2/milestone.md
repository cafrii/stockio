# Phase 2 상세 마일스톤: 증권사 API 이중화 및 금 시세

최초 작성: 2026-07-23

> 상위 마일스톤은 `docs/milestone.md`, 진행 상태는 `docs/phase2/status.md` 참고.
> 본 문서는 Phase 2(신규 작업)의 세부 계획만 다룬다.

---

## 배경 및 목표

Phase 1에서 키움증권 REST API 기반 현재가·52주 최고가 조회 서비스를 완성했다
(구글시트 IMPORTXML 연동, 사내 gamma 서버 Docker 배포). Phase 2에서는 다음 두 축을 추가한다.

1. **증권사 API 이중화** — 키움 외 토스증권 API를 추가하여 장애·정책 변화에 대비.
   요청 시 provider를 선택할 수 있게 한다.
2. **금 시세 정보** — 증권사 API로 얻을 수 없는 KRX 금 시세 / 국제 금 시세(원·달러)를
   스크래핑으로 확보. lazy 로딩 페이지 대응 및 URL·XPath 외부 설정화가 핵심.

### 설계 원칙
- 기존 아키텍처(`routes.py` → `services/*` → `xml_builder.py`, httpx 완전 비동기, 싱글톤 클라이언트)를 유지·확장한다.
- 증권사별 코드는 **공통 인터페이스로 추상화**하여 provider 추가 비용을 낮춘다.
- 스크래핑 대상의 **URL·XPath는 절대 하드코딩하지 않는다.** 외부 설정 파일로 분리하고, 변경 시 코드 수정 없이 설정만 갱신하도록 한다.

---

## Phase 2.1: 증권사 API 이중화 (토스증권 추가)

### 목표
`/api/price` 요청 시 `provider`를 선택(kiwoom | toss)할 수 있게 하고, 응답 스키마는 provider와 무관하게 동일하게 유지한다.

### 작업 항목
- [ ] **2.1.1 공통 인터페이스 추상화**
  - `app/services/base.py` (가칭)에 `StockProvider` 추상 클래스 정의
  - 공통 시그니처: `async def get_stock_price(code, market) -> dict`
  - 반환 딕셔너리 스키마 통일(`code`, `price`, `high52w`, `high52w_date`, `timestamp`, `market`, `provider`)
  - 기존 `KiwoomClient`가 이 인터페이스를 구현하도록 리팩터링(동작 변경 없이)
- [ ] **2.1.2 토스증권 클라이언트 구현** (`app/services/toss.py`)
  - 토스 developers 문서 기준 인증(토큰) 및 시세 조회 구현
  - 키/시크릿은 환경 변수화 (`TOSS_API_APPKEY`, `TOSS_API_SECRET` 등, `config.py`에 추가)
  - 토스가 52주 최고가를 제공하지 않을 경우의 처리 방침 결정(빈 필드 허용 등)
- [ ] **2.1.3 provider 라우팅**
  - `/api/price`에 `provider` 쿼리 파라미터 추가(기본값 `kiwoom`, 하위 호환 유지)
  - provider factory (예: `get_provider(name)`)로 싱글톤 분기
  - 유효하지 않은 provider는 에러 XML 반환
- [ ] **2.1.4 검증**
  - kiwoom/toss 동일 종목 교차 조회, 응답 스키마 일치 확인
  - 기존 구글시트 수식 무변경 동작(회귀) 확인

### 참고
- 토스 developers 문서: https://developers.tossinvest.com/docs
- 키/시크릿: 사용자가 확보 완료(폴더 구조 확정 후 제공 예정)

### 미결정/확인 대상
- 토스 API의 52주 최고가 제공 여부 및 필드명
- provider 파라미터 표기(`kiwoom`/`toss` 소문자 고정 여부)

---

## Phase 2.2: 금 시세 정보 (스크래핑)

### 목표
KRX 금 시세 및 국제 금 시세(원·달러)를 조회하는 엔드포인트 제공. 대상 페이지가 대부분 lazy 로딩이라 구글시트 IMPORTXML/단순 HTTP GET으로는 빈 값이 나오는 문제를 백엔드에서 해결한다.

### 스크래핑 방식 (결정)
- 사용자가 **즐겨 사용하는 페이지 URL과 XPath를 직접 제공**한다.
- 백엔드는 제공된 설정으로 값을 추출한다. **페이지 구조 변경 시 사용자가 설정을 갱신**하는 운영 모델.
- lazy 로딩 렌더링이 필요한 대상은 headless 렌더링이 필요할 수 있음 → 대상 URL 확인 후 방식(단순 HTTP vs headless) 확정.

### 작업 항목
- [ ] **2.2.1 스크래핑 설정 외부화**
  - 설정 파일(예: `config/scrape_targets.yaml`)에 대상별 `url`, `xpath`, (필요 시)`render: true/false`, `label`, `unit` 정의
  - URL·XPath는 코드에 하드코딩하지 않음
- [ ] **2.2.2 스크래핑 서비스 구현** (`app/services/gold.py` 가칭)
  - 설정 로드 → 대상 페이지 요청 → XPath 추출 → 정규화(숫자/부호/천단위 콤마 제거)
  - lazy 로딩 대상: headless 렌더링 경로(도입 시 gamma Docker 이미지에 의존성 추가 필요)
- [ ] **2.2.3 엔드포인트 추가**
  - 예: `/api/gold?target=krx` 형태(대상 키로 설정 조회), XML 응답
- [ ] **2.2.4 변경 대응 가이드 문서화**
  - `docs/phase2/gold_scraping_guide.md` (가칭): 대상 추가/URL·XPath 갱신 절차, 실패 진단(빈 값·타임아웃·구조 변경) 체크리스트
- [ ] **2.2.5 검증**
  - 정상 추출, 페이지 변경 가정(잘못된 XPath) 시 명확한 에러 응답 확인

### 미결정/확인 대상 (사용자 제공 대기)
- 대상 사이트 URL 및 XPath (KRX 금 / 국제 금 각각)
- 각 대상의 lazy 로딩 여부 → headless 렌더링(playwright 등) 필요 여부 및 Docker 반영 범위
- 응답 필드(가격 외 통화·기준시각 포함 여부)

---

## 산출물 요약
- 리팩터링/신규 코드: `app/services/base.py`, `app/services/toss.py`, `app/services/gold.py`, `app/api/routes.py`, `app/core/config.py`
- 설정 파일: `config/scrape_targets.yaml`
- 문서: 본 문서, `docs/phase2/status.md`, `docs/phase2/gold_scraping_guide.md`
- 배포: gamma 서버 Docker 반영(스크래핑 방식 확정 후 의존성 갱신)

## 진행 순서(제안)
1. Phase 2.1 (토스 이중화) — 인터페이스 추상화가 이후 확장 기반이 됨
2. Phase 2.2 (금 시세) — 사용자 URL·XPath 제공 시점에 착수

> 파일/모듈명 중 "(가칭)"은 구현 착수 시 최종 확정한다.
