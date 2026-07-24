# Phase 2 진행 상황

**최종 업데이트**: 2026-07-24 (Phase 2.1 / 2.2 모두 구현·실측 완료)

> 상위 진행 상황은 `docs/status.md`, Phase 2 상세 계획은 `docs/phase2/milestone.md` 참고.
> 갑작스러운 중단 후 심리스 재개를 위한 상태 문서. 단계(milestone) 완료 시 갱신한다.

---

## 현재 단계

**Phase 2 전체(2.1 API 이중화 + 2.2 금 시세) 구현·실측 완료 ✅ → 다음: gamma 서버 재배포**

### 토스 API 조사 결과 (중요)
- 토스 `/api/v1/prices`는 **현재가(lastPrice)만 제공, 52주 최고/최저가 필드 없음**.
  → **일봉 캔들 API(`/api/v1/candles`, interval=1d)를 페이지네이션 2회로 ~250거래일 조회 후 min/max 산출**(방법 A).
  → 캔들은 `1m`/`1d`만 지원(주봉 없음), 1회 최대 200봉 → 250일은 200+50 두 번 호출.
  → 실측 교차검증: 005930 기준 kiwoom·toss 모두 `high52w_date=20260619` 일치.
- 토스 토큰: OAuth2 client_credentials(form-urlencoded), 응답 `expires_in`(초) → 절대 만료시각 변환 저장.
- 토스도 키움처럼 **허용 IP 등록** 필요(미등록 시 403). 실측은 성공(현재 서버 IP 등록됨).

---

## 결정 사항 (2026-07-23 확인)

| 항목 | 결정 |
|------|------|
| 토스증권 API | Phase 2에서 **실제 구현까지** 진행 |
| 금 시세 스크래핑 대상 | **사용자가 URL·XPath 직접 지정** (다음 턴 제공 예정) |
| 금 시세 방식 | 사용자 제공 URL·XPath 설정 외부화, 페이지 변경 시 설정 갱신 운영 |
| 마일스톤 재조정 | 기존 Phase 2(안정화)→Phase 3, 기존 Phase 3(확장)→Phase 4, 신규 작업=Phase 2 |
| 이번 세션 시작점 | 문서 셋업부터 |

---

## 완료된 작업

### 2026-07-23 — 계획 셋업
- [x] 현재 코드/문서 상태 파악 (52주 최고가 기능 구현 완료 상태 확인)
- [x] `docs/milestone.md` 재조정 (Phase 2→3, Phase 3→4, 신규 Phase 2 삽입)
- [x] `docs/phase2/milestone.md` 작성 (2.1 이중화, 2.2 금 시세 상세 계획)
- [x] `docs/phase2/status.md` 작성 (본 문서)

---
### Phase 2.1: 증권사 API 이중화 (토스) — 완료 ✅
- [x] 2.1.1 `StockProvider` 공통 인터페이스 추상화 (`app/services/base.py`)
- [x] 2.1.2 토스 클라이언트 구현 (`app/services/toss.py`) — 토큰+현재가, 실측 성공(005930)
- [x] 2.1.3 `/api/price` provider 파라미터 추가 + 팩토리(`app/services/provider.py`)
- [x] 2.1.4 검증: 토스 실측/라우트 E2E/잘못된 provider 400/싱글톤·예외계층 확인
- 기본 provider는 `DEFAULT_PROVIDER` 환경변수로 변경 가능(미설정 시 kiwoom)

**구현 파일**: `app/services/base.py`(신규), `app/services/toss.py`(신규),
`app/services/provider.py`(신규), `app/services/kiwoom.py`(인터페이스 구현),
`app/core/config.py`(토스·DEFAULT_PROVIDER), `app/api/routes.py`(provider 라우팅),
`app/utils/xml_builder.py`(`<provider>` 태그), `main.py`(루트·기동로그)

### toss 일봉 차트로 52주 최고/최저가 계산 - 완료
- **`app/services/kiwoom.py`**: `ka10001` 응답의 `250lwst`(52주 최저가)를 추가 파싱 →
  반환 dict에 `low52w` 추가. **추가 API 호출 없음**(기존 단일 호출 응답에 포함).
- **`app/services/toss.py`**: 일봉 캔들 산출 로직 신규.
- **`app/services/base.py`**: 공통 반환 스키마 문서에 `low52w` 추가.
- **`app/utils/xml_builder.py`**: `<high52w>` 다음에 `<low52w>` 요소 출력 추가(값이 있을 때만).


## 진행 중 / 다음 작업

### Phase 2.2: 금 시세 (스크래핑) — 완료 ✅
- [x] 2.2.1 스크래핑 설정 외부화 (`config/scrape_targets.yaml`, `defaults` + `groups.<그룹>.<대상>`)
- [x] 2.2.2 범용 스크래핑 서비스 구현 (`app/services/scraper.py`) + 금 도메인 계층 (`app/services/gold.py`)
- [x] 2.2.3 `/api/gold` + 범용 `/api/scrape` 엔드포인트
- [x] 2.2.4 변경 대응 가이드 (`docs/phase2/gold_scraping_guide.md`)
- [x] 2.2.5 검증: 정상 추출·전체 조회·잘못된 대상 400·XPath 깨짐 502·캐시·회귀

**핵심 발견**: 네이버 metals 페이지는 **SSR 되어 있어 단순 HTTP GET + XPath로 추출된다.**
→ **headless 브라우저(playwright) 불필요**, gamma Docker에 브라우저 의존성 추가 불필요.
(구글시트 IMPORTXML이 실패한 것은 lazy 로딩이 아닌 다른 원인)

**실측**: 국제 금 4,051.6 USD/OZS / KRX 금 190,910 원/g

**설계 특징**
- 자산 무관 **범용 엔진** + 얇은 도메인 계층 → 가상자산 등은 YAML만 추가하면 코드 수정 없이 동작
- 설정 파일 mtime 감지 → **서버 재시작 없이 즉시 반영**
- URL 단위 TTL 캐시(기본 60초) → 두 대상이 같은 페이지를 공유하므로 실제 요청은 1회
- 실패 유형별 구분: 설정 오류 400 / 페이지 조회 실패 502 / XPath 미매칭 502(구조 변경 안내)

**추가 의존성**: `lxml`, `PyYAML` (requirements.txt 반영) → **gamma 재배포 시 이미지 재빌드 필요**

### Phase 2.2-b: lazy 로딩(headless 렌더링) 대응 — 완료 ✅

정적 GET으로 불가능한 페이지를 위한 확장 경로. 기존 lxml 방식과 **병행** 지원.

- [x] `app/services/renderer.py` 신규 (playwright, **선택적 의존성** — 미설치여도 정적은 정상 동작)
- [x] 대상별 `render: never | auto | always` 설정 (기본 `auto`)
  - `auto` = 정적 시도 → **실패한 대상만** 렌더링 재시도 (사용자 요청 동작)
- [x] 응답에 `<method>static|render</method>` 추가 (어느 경로로 얻었는지 진단)
- [x] 캐시 강제 무효화 파라미터 **`refresh=1`** (`/api/gold?target=krx&refresh=1`)
- [x] 캐시 키를 (url, 렌더링여부)로 분리
- [x] Dockerfile `--build-arg ENABLE_RENDER=true` 선택적 설치 (기본 false → 기존 경량 이미지 유지)

**실측 검증 (2026-07-24)**

| 대상 | 정적 | 렌더링 | 결과 |
|------|------|--------|------|
| 네이버 금(krx/international) | ✅ | 불필요 | `method=static` |
| 네이버 BTC (CSR) | ❌ 값 없음 | ✅ | 94,902,000원 `method=render` |
| investing.com XAU/USD | ❌ HTTP 403 | ✅ | 4,045.14 `method=render` |
| auto 폴백 (BTC를 auto로) | ❌ → 폴백 | ✅ | `method=render` 자동 전환 확인 |

**주의(중요)**: 브라우저 "Copy XPath"의 위치 기반 경로는 headless에서 DOM이 달라 자주 깨진다.
→ investing.com은 `//*[@data-test="instrument-price-last"]` 속성 기반으로 대체했다.
(사용자 제공 위치 기반 XPath는 렌더링 환경에서 미매칭)

**알려진 제약**: 렌더러는 이벤트 루프에 바인딩되므로 루프 변경 시 자동 재기동하도록 처리했다.

---

## 블로커 / 대기 항목
- ~~토스 API 키·시크릿~~ → **검증 완료** (2026-07-23 실측 성공, 005930)
- ~~금 시세 대상 URL·XPath~~ → **제공 완료** (naver metals 페이지 + XPath 2종)
- ~~금 시세 lazy 로딩/headless 여부~~ → **확정: SSR이라 headless 불필요**(단순 HTTP GET으로 추출)
- ~~토스 52주 최고/최저가~~ → **완료**(일봉 캔들 250일 산출, kiwoom과 교차검증 일치)
- gamma 재배포 시: 토스 4개 환경변수 + 서버 IP 토스 허용목록 등록 + `lxml`/`PyYAML` 포함 이미지 재빌드

---

## 참고 문서
- `docs/phase2/milestone.md`: Phase 2 상세 마일스톤
- `docs/phase2/gold_scraping_guide.md`: **스크래핑 대상 변경 대응 가이드**(페이지 구조 변경 시)
- `docs/milestone.md`: 전체 마일스톤
- `docs/architecture.md`: 아키텍처
- `.ai/docs/gamma_docker_guide.md`: gamma 서버 배포 가이드
