# Stockio 로컬 테스트 가이드

로컬에서 Stockio를 실행하고 API를 시험하는 방법. (마스터 문서: [`docs/README.md`](../README.md))

> 갱신: 2026-07-24 — Phase 2 반영(provider·금·스크래핑·렌더링). 이전 Phase 1.1 시절 내용은 대체됨.

---

## 1. 환경 준비

### 1.1 가상환경 활성화
```bash
source .venv/bin/activate
```

### 1.2 패키지 설치 (최초 1회)
```bash
pip install -r requirements.txt
```

### 1.3 headless 렌더링 (선택)
가상자산 등 **lazy 로딩 대상**을 로컬에서 시험하려면 playwright가 필요하다.
설치하지 않아도 주식·금 시세·정적 스크래핑은 정상 동작한다.
```bash
pip install playwright && playwright install chromium
```

### 1.4 환경 변수 (`.env`)
```ini
# 키움
KIWOOM_API_APPKEY=...
KIWOOM_API_SECRET=...
KIWOOM_API_HOST=https://api.kiwoom.com          # 모의투자: https://mockapi.kiwoom.com
KIWOOM_TOKEN_ENV=/tmp/.kiwoom_env
# 토스 (provider 이중화)
TOSS_API_CLIENT_ID=...
TOSS_API_SECRET=...
TOSS_API_HOST=https://openapi.tossinvest.com
TOSS_TOKEN_ENV=/tmp/.toss_env
# provider 미지정 시 기본값 (kiwoom | toss)
DEFAULT_PROVIDER=kiwoom
# 기타
DEBUG=false
```

> 키움·토스 모두 **호출 서버의 IP가 허용목록에 등록**돼 있어야 한다(미등록 시 403).

---

## 2. 서버 실행

```bash
uvicorn main:app --reload      # 또는  python main.py
```

정상 기동 로그 예:
```
INFO  Stockio v1.0.0 시작
INFO  키움 API 호스트: https://api.kiwoom.com
INFO  기본 provider: kiwoom
INFO  환경 변수 검증 완료
INFO  Uvicorn running on http://0.0.0.0:8000
```

확인용 URL: `/` (서비스 정보) · `/docs` (Swagger) · `/health`

---

## 3. API 테스트

### 3.1 헬스 체크
```bash
curl http://localhost:8000/health
# {"status":"healthy","timestamp":"...","service":"Stockio"}
```

### 3.2 주식 시세 (provider 이중화 + 52주)
```bash
curl "http://localhost:8000/api/price?code=005930"                 # 기본 provider
curl "http://localhost:8000/api/price?code=005930&provider=kiwoom"
curl "http://localhost:8000/api/price?code=005930&provider=toss"
```
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

### 3.3 금 시세 (스크래핑, 정적)
```bash
curl "http://localhost:8000/api/gold?target=krx"
curl "http://localhost:8000/api/gold?target=international"
curl "http://localhost:8000/api/gold"                 # 전체
curl "http://localhost:8000/api/gold?target=krx&refresh=1"   # 캐시 무시(개발용)
```

### 3.4 범용 스크래핑 (렌더링 대상 포함)
```bash
curl "http://localhost:8000/api/scrape?group=crypto&target=btc"   # playwright 필요
```

응답의 `<method>`로 정적(`static`)/렌더링(`render`) 경로를 구분할 수 있다.

### 3.5 에러 응답 예
```xml
<error>
  <message>시세 조회에 실패했습니다.</message>
  <code>502</code>
  <detail>...</detail>
</error>
```
에러 코드 의미와 대응은 [`docs/troubleshooting.md`](../troubleshooting.md) 참고.

---

## 4. 단위 테스트

```bash
pytest -q
```
- `tests/` 아래 키움/라우트 테스트. (참고 결과: `docs/test/phase1_2_test_results.md`, `phase1_3_test_results.md`)

---

## 5. 참고
- API 명세 전체: [`docs/README.md`](../README.md)
- 스크래핑 대상 추가/변경: [`docs/phase2/gold_scraping_guide.md`](../phase2/gold_scraping_guide.md)
- Swagger UI: http://localhost:8000/docs
- 로그 상세: `.env`에 `DEBUG=true`
