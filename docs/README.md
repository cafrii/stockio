# Stockio — 마스터 문서

주식·금·가상자산 시세를 **구글 시트 IMPORTXML**용 XML로 중계하는 경량 FastAPI 백엔드.

- 증권사 REST API(키움·토스)로 주식 현재가·52주 최고/최저가 제공
- 증권사 API로 얻을 수 없는 값(금·가상자산 등)은 페이지 **스크래핑**으로 제공
- 운영: 사내 **gamma 서버**(Docker). 외부 접근은 `https://<myserver.com>:8100`

> 이 문서는 Phase 1·2의 산출물을 한눈에 보는 허브다. 세부는 각 링크 문서를 참고한다. <br>
> (최초 키움 PoC 내용은 범위 밖 — `docs/poc/` 참고) <br>
> `<myserver.com>`는 실제 동작하는 DNS 이름을 사용하여야 한다.

---

## 1. 아키텍처 (요약)

```
구글 시트 IMPORTXML ─┐
   기타 클라이언트  ─┴─▶ stockio (FastAPI)
                          ├─ /api/price  ─▶ 키움 / 토스 REST API   (provider 선택)
                          └─ /api/gold   ─▶ 스크래퍼 ─┬─ 정적 HTTP GET (lxml)
                             /api/scrape              └─ headless 렌더링 (playwright, 선택)
```

- 상세: [`docs/phase1/architecture.md`](phase1/architecture.md)
- 스크래핑 설계·모듈 구조: [`docs/phase2/gold_scraping_guide.md`](phase2/gold_scraping_guide.md) 7절

---

## 2. API 명세

모든 시세 응답은 **XML**(구글 시트 IMPORTXML용), 에러도 XML `<error>`. 기준 URL 예: `https://<myserver.com>:8100`

### 2.1 `GET /health` — 헬스 체크 (JSON)

```json
{ "status": "healthy", "timestamp": "2026-07-24T02:50:00", "service": "Stockio" }
```

### 2.2 `GET /api/price` — 주식 현재가 + 52주 최고/최저가

| 파라미터 | 필수 | 기본 | 설명 |
|----------|------|------|------|
| `code` | ✅ | — | 종목코드 6자리 (예: `005930`) |
| `market` | | `KOSPI` | `KOSPI`/`KOSDAQ` (`J`/`Q` 약어 가능) |
| `provider` | | 서버 기본값 | `kiwoom` \| `toss`. 미지정 시 `DEFAULT_PROVIDER`(환경변수) |

```xml
<stock>
  <code>005930</code>
  <price>249000</price>
  <high52w>374500</high52w>
  <low52w>62000</low52w>
  <high52w_date>20260619</high52w_date>
  <timestamp>2026-07-24T02:50:01</timestamp>
  <market>KOSPI</market>
  <provider>kiwoom</provider>
</stock>
```

- **provider 이중화**: 스프레드시트 수식을 바꾸지 않고 서버 `DEFAULT_PROVIDER` 한 줄로 전체 교체 가능.
- **52주 값**: 키움은 `250hgst`/`250lwst` 단일 호출. 토스는 52주 필드가 없어 **일봉 캔들 250일을 조회해 산출**(키움과 동일 기준).
- 토스는 KRX/NXT를 구분하지 않으며 `market`은 응답 라벨 용도로만 echo 됨.

### 2.3 `GET /api/gold` — 금 시세 (스크래핑)

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `target` | | `krx` \| `international`. **미지정 시 전체** |
| `refresh` | | `1`이면 캐시 무시하고 새로 조회 (개발용, 시트 수식엔 넣지 말 것) |

```xml
<gold>
  <target>krx</target>
  <label>국내 금 시세 (KRX 금 현물)</label>
  <price>189540</price>
  <unit>원/g</unit>
  <currency>KRW</currency>
  <timestamp>2026-07-24T02:50:16</timestamp>
  <method>static</method>   <!-- static | render : 어느 경로로 얻었는지 -->
</gold>
```

전체 조회 시 루트가 `<golds>`, 각 항목이 `<gold>`.

### 2.4 `GET /api/scrape` — 범용 스크래핑

증권사 API가 주지 않는 값(가상자산 등)을 설정만 추가해 조회. 응답 형식은 `/api/gold`와 동일(`<quote>`/`<quotes>`).

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `group` | ✅ | 자산 그룹 (`gold`, `crypto` 등, 설정의 `groups` 키) |
| `target` | | 대상 키. 미지정 시 그룹 전체 |
| `refresh` | | `1`이면 캐시 무시 |

```bash
curl "https://<myserver.com>:8100/api/scrape?group=crypto&target=btc"
```

> 대상 정의는 전부 [`config/scrape_targets.yaml`](../config/scrape_targets.yaml)에 있다. **URL·XPath 하드코딩 없음.**
> 페이지 변경 시 대응·새 대상 추가: [`docs/phase2/gold_scraping_guide.md`](phase2/gold_scraping_guide.md)

### 2.5 에러 응답 (공통)

```xml
<error>
  <message>시세 조회에 실패했습니다.</message>
  <code>502</code>
  <detail>...</detail>
</error>
```

| 코드 | 의미 |
|------|------|
| 400 | 파라미터/설정 오류 (잘못된 provider·target·render 값 등, `detail`에 사용 가능 목록) |
| 401 | 증권사 인증 실패 |
| 502 | 증권사 API 실패 / 페이지 조회 실패 / XPath 미매칭(구조 변경) |
| 500 | 서버 내부 오류 |

### 2.6 디버그 엔드포인트 (키움 토큰 진단용)

`GET /debug/ip`, `GET /debug/token-status`, `POST /debug/force-expire-token` — 운영 진단용.
자세한 토큰 문제 진단: [`docs/issues/token_debug_guide.md`](issues/token_debug_guide.md)

---

## 3. 개발 / 테스트

- 로컬 실행·API 테스트 절차: [`docs/test/local_test_guide.md`](test/local_test_guide.md)
- 요약:
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt      # (렌더링까지 쓰려면 playwright 별도 — 아래 참고)
  uvicorn main:app --reload
  curl "http://localhost:8000/api/price?code=005930"
  ```
- **headless 렌더링**(가상자산 등 lazy 로딩 대상)을 로컬에서 쓰려면:
  ```bash
  pip install playwright && playwright install chromium
  ```
  playwright는 **선택적 의존성** — 없어도 정적 스크래핑·주식·금 시세는 정상 동작한다.

---

## 4. 배포 (gamma)

- 전체 절차·롤백: [`.ai/docs/gamma_docker_guide.md`](../.ai/docs/gamma_docker_guide.md)
- 요점:
  - `--platform linux/amd64` 필수(gamma는 x86_64). 렌더링 포함은 `--build-arg ENABLE_RENDER=true`.
  - 토큰은 named volume `stockio-data`(`/data`)에 보존 → 컨테이너 재생성해도 유지.
  - **`config/scrape_targets.yaml`은 호스트에서 관리**(읽기전용 마운트) → 스크래핑 설정만 바뀌면
    **이미지 재빌드 없이** `scp` 한 번 + 자동 재로드로 반영. (코드 변경 시에만 재빌드)
  - 서비스 포트 8100, 외부는 Synology 역방향 프록시로 `https://<myserver.com>:8100`.

---

## 5. 구글 시트 사용

```
=IMPORTXML("https://<myserver.com>:8100/api/price?code=005930","/stock/price")
=IMPORTXML("https://<myserver.com>:8100/api/price?code=005930","/stock/high52w")
=IMPORTXML("https://<myserver.com>:8100/api/gold?target=krx","//price")
=IMPORTXML("https://<myserver.com>:8100/api/scrape?group=crypto&target=btc","//price")
```

- 시세 값 태그는 대상 무관하게 `//price`로 통일.
- 더 많은 예시: [`docs/guides/google_sheets_guide.md`](guides/google_sheets_guide.md)

---

## 6. 문제 해결

- **사용 중 발생하는 문제**(구글 시트 셀 에러 포함): [`docs/troubleshooting.md`](troubleshooting.md)
- 스크래핑 대상 페이지 변경 대응: [`docs/phase2/gold_scraping_guide.md`](phase2/gold_scraping_guide.md)

---

## 7. 진행 상황 / 계획

| 문서 | 내용 |
|------|------|
| [`docs/milestone.md`](milestone.md) | 전체 마일스톤(Phase 1~4) |
| [`docs/phase2/milestone.md`](phase2/milestone.md) | Phase 2 상세 계획 |
| [`docs/phase2/status.md`](phase2/status.md) | Phase 2 진행 상황 |
| [`docs/phase1/`](phase1/) | Phase 1 산출물(PRD·아키텍처·상태·배포) |
