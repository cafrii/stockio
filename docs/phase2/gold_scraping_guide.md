# 스크래핑 대상 변경 대응 가이드

마지막 갱신: 2026-07-24 (Phase 2.2 구현)

> 대상 페이지(네이버 등)의 구조는 예고 없이 바뀐다.
> 그때 **코드를 고치지 않고 설정 파일만 수정**해서 복구하기 위한 문서다.

---

## 1. 핵심 원칙

- URL·XPath는 **코드에 없다**. 전부 `config/scrape_targets.yaml` 에 있다.
- 이 파일을 고치면 **서버 재시작 없이 즉시 반영**된다.
  (파일 수정 시각(mtime)을 감지해 자동 재로드)
- 따라서 장애 대응은 대부분 **YAML 한 줄 수정**으로 끝난다.
- **운영(gamma)에서는 이 파일이 호스트에 있고 컨테이너에 읽기전용 마운트**된다
  (`-v ~/stockio/config:/app/config:ro`). 즉 **이미지 재빌드가 전혀 필요 없다.**
  - 갱신 절차: 리포지토리에서 수정 → 개발 환경에서 검증 → `scp config/scrape_targets.yaml gamma:~/stockio/config/` → 끝.
  - 배포 가이드: [`.ai/docs/gamma_docker_guide.md`](../../.ai/docs/gamma_docker_guide.md) "스크래핑 설정만 변경할 때"

---

## 2. 설정 파일 구조

`config/scrape_targets.yaml`

```yaml
defaults:
  timeout: 10           # HTTP 제한 시간(초)
  user_agent: "..."     # 일부 사이트는 UA에 따라 응답이 달라짐
  cache_ttl: 60         # 같은 URL 재요청 방지 캐시(초)

groups:
  gold:                       # 그룹 = 자산 종류
    international:            # 대상 키 → /api/gold?target=international
      label: "국제 금 시세 (GC 뉴욕상품거래소)"
      url: "https://m.stock.naver.com/marketindex/home/metals"
      xpath: '//*[@id="content"]/div[2]/ul/li[1]/div[1]/div[1]/b'
      unit: "USD/OZS"
      currency: "USD"
    krx:                      # → /api/gold?target=krx
      ...
```

| 항목 | 필수 | 설명 |
|------|------|------|
| `url` | ✅ | 조회할 페이지 주소 |
| `xpath` | ✅ | 값을 추출할 XPath |
| `label` | | 사람이 읽는 이름 |
| `unit` | | 단위 표기 (`원/g`, `USD/OZS`) |
| `currency` | | 통화 코드 |
| `render` | | 조회 방식 `never`/`auto`/`always` (기본 `auto`) |
| `wait_ms`·`wait_for` | | 렌더링 대기 (아래 참고) |
| `timeout`·`user_agent`·`cache_ttl` | | `defaults` 재정의용 |

---

## 2-1. 조회 방식: 정적 vs headless 렌더링

일부 페이지는 단순 HTTP GET으로 값을 얻을 수 없다. 두 경로를 모두 지원한다.

| `render` | 동작 | 쓰는 경우 |
|----------|------|-----------|
| `never` | 정적 HTTP GET만 | 가장 가볍다. 정적으로 확실히 되는 대상 |
| `auto` (기본) | 정적 시도 → **실패하면 그 대상만** 렌더링 재시도 | 평소 가볍게, 깨지면 자동 복구 |
| `always` | 항상 headless 렌더링 | CSR·봇차단이 확실한 대상 (정적 시도 낭비 제거) |

응답의 `<method>` 로 **어느 경로로 얻었는지** 확인할 수 있다 (`static` / `render`).

```xml
<quote>
  <target>btc</target>
  <price>94902000</price>
  <method>render</method>   <!-- 렌더링 경로로 획득 -->
</quote>
```

### 렌더링이 필요한 대표 증상

| 증상 | 원인 | 조치 |
|------|------|------|
| 시트에 "가져온 콘텐츠가 비어 있습니다" | 클라이언트 렌더링(CSR) | `render: always` |
| `HTTP 403` | 봇 차단 | `render: always` (실제 크롬 UA로 접속) |
| 정적은 되다가 갑자기 실패 | 페이지 방식 변경 | `auto`면 자동 폴백됨 |

### 렌더링 대기 옵션

```yaml
render: always
wait_for: '[data-test="instrument-price-last"]'   # 이 요소가 나타날 때까지 대기(권장)
wait_ms: 2500                                     # 또는 고정 대기(ms)
```

`wait_for` 가 `wait_ms` 보다 우선한다. 값이 늦게 채워지는 페이지는 `wait_for` 를 쓰는 편이 안정적이다.

### ⚠️ 렌더링 대상의 XPath 주의

**브라우저에서 "Copy XPath" 한 위치 기반 경로(`div[2]/div[1]/...`)는 headless 환경에서 자주 깨진다.**
광고·쿠키 배너 등이 달라 DOM 인덱스가 밀리기 때문이다.

→ 가능하면 **속성 기반 selector**를 쓴다.

```yaml
# 나쁨 (headless에서 깨짐)
xpath: '//*[@id="__next"]/div[2]/div[1]/div[2]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]'
# 좋음 (구조가 바뀌어도 견딤)
xpath: '//*[@data-test="instrument-price-last"]'
```

찾는 방법: 개발자도구에서 값 요소를 선택한 뒤 `data-test`, `id`, 고유한 `class` 같은
속성이 있는지 보고 `//*[@속성="값"]` 형태로 작성한다.

### 설치 (렌더링을 쓰려면)

playwright는 **선택적 의존성**이다. 설치하지 않아도 정적 스크래핑은 정상 동작한다.

```bash
pip install playwright
playwright install chromium
```

Docker(gamma 배포)에서 켜려면:

```bash
docker build --build-arg ENABLE_RENDER=true -t stockio .
```

> 브라우저와 시스템 라이브러리 때문에 이미지가 수백 MB 커진다.
> 렌더링이 필요한 대상을 쓰지 않는다면 켜지 않아도 된다.

---

## 3. 증상별 대응

### 증상 A: `502` + "페이지 구조가 변경되었을 수 있습니다"

가장 흔한 경우. **XPath가 더 이상 맞지 않는다.**

```xml
<error>
  <message>값 추출에 실패했습니다. 페이지 구조가 변경되었을 수 있습니다. ...</message>
  <code>502</code>
</error>
```

**조치 — XPath 다시 따기**

1. 크롬에서 대상 페이지를 연다 (모바일 페이지는 모바일 UA 권장).
2. 원하는 값에 **우클릭 → 검사(Inspect)**.
3. 하이라이트된 요소에 **우클릭 → Copy → Copy XPath**.
4. 복사된 값을 YAML의 `xpath:` 에 **작은따옴표로 감싸서** 넣는다.
   (XPath 안에 큰따옴표 `"` 가 있으므로 반드시 작은따옴표 사용)
5. 저장 후 아래 4번의 검증 명령으로 확인. 재시작 불필요.

### 증상 B: `502` + "대상 페이지 조회에 실패했습니다"

페이지 요청 자체가 실패(타임아웃, 404, 차단).

- URL이 바뀌었는지 브라우저로 확인 → `url:` 갱신
- 접속은 되는데 실패하면 `user_agent` 를 실제 브라우저 값으로 교체
- 느리면 `timeout` 을 늘린다

### 증상 C: `400` + "정의되지 않은 대상/그룹"

요청한 `target`/`group` 이 설정에 없다. 응답 `detail` 에 **사용 가능한 목록이 표시**되므로 그걸 보고 맞춘다.

### 증상 D: 값은 나오는데 숫자가 이상함

- 단위가 바뀌었을 수 있다 (`원/g` ↔ `원/3.75g` 등) → `unit` 확인
- 다른 항목의 XPath를 잡았을 수 있다 → 증상 A 절차로 XPath 재확인

---

## 4. 검증 방법

설정을 고친 뒤:

```bash
# 개별 조회
curl "http://localhost:8000/api/gold?target=krx"
curl "http://localhost:8000/api/gold?target=international"

# 전체 조회
curl "http://localhost:8000/api/gold"

# 운영 서버(gamma)
curl "https://<myserver.com>:8100/api/gold?target=krx"
```

정상 응답:

```xml
<gold>
  <target>krx</target>
  <label>국내 금 시세 (KRX 금 현물)</label>
  <price>190910</price>
  <unit>원/g</unit>
  <currency>KRW</currency>
  <timestamp>2026-07-24T09:48:59</timestamp>
</gold>
```

### 캐시 강제 무효화 — `refresh=1`

캐시(`cache_ttl`, 기본 60초) 때문에 수정 직후 이전 값이 보일 수 있다.
개발·검증 중에는 `refresh=1` 을 붙이면 **캐시를 무시하고 새로 조회**한다.

```bash
curl "http://localhost:8000/api/gold?target=krx&refresh=1"
curl "http://localhost:8000/api/scrape?group=crypto&target=btc&refresh=1"
```

> 구글시트 수식에는 넣지 말 것 — 매 갱신마다 실제 페이지를 새로 긁는다.

---

## 5. 새 대상 추가하기 (예: 가상자산)

**코드 수정 없이** YAML에 그룹/대상만 추가하면 된다.

```yaml
groups:
  crypto:
    btc:
      label: "비트코인"
      url: "https://example.com/btc"
      xpath: '//*[@id="price"]'
      unit: "원"
      currency: "KRW"
```

바로 범용 엔드포인트로 조회된다:

```bash
curl "http://localhost:8000/api/scrape?group=crypto&target=btc"
curl "http://localhost:8000/api/scrape?group=crypto"          # 그룹 전체
```

금처럼 전용 경로(`/api/gold`)를 주고 싶을 때만 `app/services/gold.py` 를 본떠
얇은 모듈 + 라우트를 추가하면 된다.

---

## 6. 구글 시트에서 쓰기

```
=IMPORTXML("https://<myserver.com>:8100/api/gold?target=krx", "//price")
=IMPORTXML("https://<myserver.com>:8100/api/gold?target=international", "//price")
```

시세 값의 태그명은 대상과 무관하게 **`<price>` 로 통일**되어 있어 수식이 단순하다.

---

## 7. 참고: 구조 및 파일

| 파일 | 역할 |
|------|------|
| `config/scrape_targets.yaml` | **대상 정의(여기만 고치면 됨)** |
| `app/services/scraper.py` | 범용 엔진 (설정 로드 → 요청 → XPath 추출 → 숫자 정규화, 정적/렌더링 분기) |
| `app/services/renderer.py` | headless 렌더링 (playwright, 선택적 의존성) |
| `app/services/gold.py` | 금 시세 도메인 계층 (얇음) |
| `app/api/routes.py` | `/api/gold`, `/api/scrape` |

- 네이버 metals(금 시세) 페이지는 **SSR** 되어 있어 정적 GET으로 추출된다.
- 반면 네이버 **비트코인** 페이지는 CSR, **investing.com** 은 봇차단(403)이라
  렌더링 경로가 필요하다. 이 둘은 `render: always` 로 설정되어 있다.
- 기본값이 `auto` 이므로, 정적으로 되던 대상이 나중에 CSR로 바뀌어도
  **자동으로 렌더링 폴백**되어 값이 계속 나온다.
