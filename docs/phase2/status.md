# Phase 2 진행 상황

**최종 업데이트**: 2026-07-23 (Phase 2.1 구현·실측 완료)

> 상위 진행 상황은 `docs/status.md`, Phase 2 상세 계획은 `docs/phase2/milestone.md` 참고.
> 갑작스러운 중단 후 심리스 재개를 위한 상태 문서. 단계(milestone) 완료 시 갱신한다.

---

## 현재 단계

**Phase 2.1(증권사 API 이중화) 구현·실측 완료 ✅ → 다음: Phase 2.2(금 시세)**

### 토스 API 조사 결과 (중요)
- 토스 `/api/v1/prices`는 **현재가(lastPrice)만 제공, 52주 최고가 필드 없음**.
  → toss provider는 `high52w`/`high52w_date`를 항상 `None`(빈 필드)으로 반환.
  → 52주 최고가가 필요하면 kiwoom provider 사용해야 함.
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

## 진행 중 / 다음 작업

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

### Phase 2.2: 금 시세 (스크래핑)
- [ ] 2.2.1 스크래핑 설정 외부화 (`config/scrape_targets.yaml`)
- [ ] 2.2.2 스크래핑 서비스 구현 — **대상 URL·XPath 제공 대기**
- [ ] 2.2.3 `/api/gold` 엔드포인트
- [ ] 2.2.4 변경 대응 가이드 문서화
- [ ] 2.2.5 검증

---

## 블로커 / 대기 항목
- 토스 API 키·시크릿 (사용자 제공 예정: 폴더 구조 확정 후)
- 금 시세 대상 URL·XPath (사용자 제공 예정)
- 금 시세 대상의 lazy 로딩 여부 → headless 렌더링 도입 및 gamma Docker 반영 여부 결정

---

## 참고 문서
- `docs/phase2/milestone.md`: Phase 2 상세 마일스톤
- `docs/milestone.md`: 전체 마일스톤
- `docs/architecture.md`: 아키텍처
- `.ai/docs/gamma_docker_guide.md`: gamma 서버 배포 가이드
