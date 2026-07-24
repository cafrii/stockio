# 문제 해결 (Troubleshooting)

**사용 동작 중** 발생하는 문제를 모은다. 구글 시트 셀 에러까지 포함.
(배포 중 에러 → [`.ai/docs/gamma_docker_guide.md`](../.ai/docs/gamma_docker_guide.md),
개발 환경 설정 에러 → [`docs/test/local_test_guide.md`](test/local_test_guide.md) 참고)

---

## 0. 먼저 할 것 — 백엔드를 직접 curl 해보기

구글 시트 셀이 이상하면, **셀 문제인지 백엔드 문제인지** 먼저 가른다.
브라우저나 터미널에서 같은 URL을 직접 열어본다.

```bash
curl "https://<myserver.com>:8100/api/gold?target=krx"
```

- **정상 XML이 나온다** → 백엔드는 정상. → 3절(시트 쪽) 확인.
- **`<error>` XML이 나온다** → 백엔드 문제. → `code`/`detail` 보고 2절 확인.
- **아무 응답이 없다/타임아웃** → 서버·네트워크. → 4절 확인.

---

## 1. 구글 시트 셀이 `#N/A` / "가져온 콘텐츠가 비어 있습니다"

| 원인 | 확인 | 조치 |
|------|------|------|
| 시트 수식의 XPath가 틀림 | 백엔드는 정상(0절)인데 셀만 비었나 | 수식 두 번째 인자를 `//price`로 (금·스크래핑) 또는 `/stock/price`로 (주식) |
| 대상이 lazy 로딩(CSR) | curl 하면 502 또는 값 비었나 | 설정에 `render: always` (2-3절) |
| 값에 `원` 등 문자가 섞임 | curl 결과가 502 파싱 실패인가 | XPath를 `.../text()[1]`로 (2-4절) |
| 캐시된 옛 값 | — | 잠시 후 갱신됨(기본 60초). 급하면 `&refresh=1`로 직접 확인 |

> 구글 시트는 IMPORTXML 결과를 자체적으로 최대 1시간 캐시한다.
> 셀을 강제 갱신하려면 URL에 무의미한 파라미터(`&t=2`)를 바꿔 넣거나 수식을 재입력한다.
> **`refresh=1`은 개발용이니 시트 수식에는 넣지 말 것**(매번 실제 페이지를 새로 긁는다).

---

## 2. 백엔드가 `<error>`를 반환할 때 (curl 결과 기준)

### 2-1. `400` "유효하지 않은 provider" / "정의되지 않은 대상·그룹"

요청 파라미터가 잘못됐다. `detail`에 **사용 가능한 값 목록**이 들어 있으니 그대로 맞춘다.

```xml
<detail>정의되지 않은 대상입니다: 'gold.silver'. 사용 가능: ['international', 'krx']</detail>
```

### 2-2. `401` 인증 실패

- 키움/토스 API 키·시크릿이 잘못됐거나 만료. 토큰 파일 문제일 수 있음.
- 키움 토큰 진단: [`docs/issues/token_debug_guide.md`](issues/token_debug_guide.md)
  또는 `GET /debug/token-status`.

### 2-3. `502` "페이지 구조가 변경되었을 수 있습니다" (XPath 미매칭)

가장 흔한 스크래핑 장애. **대상 페이지 구조가 바뀌어 XPath가 안 맞는다.**

→ `config/scrape_targets.yaml`의 해당 `xpath`를 다시 딴다.
전체 절차(개발자도구 Copy XPath, 속성 기반 selector 권장, 렌더링 대상 주의)는
[`docs/phase2/gold_scraping_guide.md`](phase2/gold_scraping_guide.md) 3·2-1절.

### 2-4. `502` 인데 값은 페이지에 있어 보임 → `원`·단위 문자 섞임

바깥 요소를 잡으면 숫자 옆 단위 텍스트까지 딸려온다. 예:

```html
<div class="DetailInfo_price_...">2,749,000<span>원</span></div>
```

이때 `//div[contains(@class,"DetailInfo_price_")]`는 `2,749,000원`을 반환 →
숫자 변환 실패 → **502**. (단순히 `원`이 붙는 게 아니라 아예 실패한다.)

**조치**: 텍스트 노드만 집는다.

```yaml
# 나쁨 → "2,749,000원" → 변환 실패
xpath: '//div[contains(@class,"DetailInfo_price_")]'
# 좋음 → "2,749,000"
xpath: '//div[contains(@class,"DetailInfo_price_")]/text()[1]'
```

### 2-5. `502` "대상 페이지 조회에 실패했습니다"

페이지 요청 자체 실패(타임아웃/404/차단).
- URL이 바뀌었으면 `url:` 갱신.
- 봇 차단(403)이면 `render: always`(실제 브라우저로 접속).
- 느리면 `timeout` 상향.

### 2-6. 토스 provider만 `502`/`403`

토스는 **서버 IP 허용목록**이 필요하다. gamma 아웃바운드 IP가
토스 개발자센터에 등록돼야 한다. (기본 provider가 kiwoom이면 기존 시트엔 영향 없음.)

---

## 3. 시트는 정상 형식인데 값이 이상/안 바뀜

- **값이 안 변한다**: 구글 시트/백엔드 캐시. 위 1절의 캐시 설명 참고.
- **주식 52주 값이 비어 있다**: 과거엔 토스가 52주 미제공이라 비었으나 현재는 캔들 산출로 채워진다.
  여전히 비면 해당 종목 캔들 데이터 부족일 수 있음 → 키움 provider로 확인.
- **금 값 단위가 안 맞음**: 페이지가 단위를 바꿨을 수 있다(`원/g` ↔ `원/3.75g`). `unit` 및 XPath 재확인.

---

## 4. 서버가 아예 응답하지 않음

```bash
curl -m 5 "https://<myserver.com>:8100/health"     # 외부 경로
ssh gamma "curl -m 5 http://localhost:8100/health"   # 컨테이너 직접
```

- 외부만 실패 → Synology 역방향 프록시/방화벽. [`.ai/docs/gamma_docker_guide.md`](../.ai/docs/gamma_docker_guide.md) 7절.
- 둘 다 실패 → 컨테이너 다운. `ssh gamma "docker ps -a --filter name=stockio; docker logs --tail 50 stockio"`.

---

## 5. 참고

- 스크래핑 대상 변경/추가: [`docs/phase2/gold_scraping_guide.md`](phase2/gold_scraping_guide.md)
- 키움 토큰 디버깅: [`docs/issues/token_debug_guide.md`](issues/token_debug_guide.md)
- API 명세: [`docs/README.md`](README.md)
