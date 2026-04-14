# Stockio 테스트 가이드

본 문서는 Stockio 서비스의 로컬 테스트 방법을 설명합니다.

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

### 1.3 환경 변수 확인
`.env` 파일에 다음 항목이 설정되어 있는지 확인:
```
KIWOOM_API_APPKEY=...
KIWOOM_API_SECRET=...
KIWOOM_API_HOST=https://openapi.kiwoom.com
KIWOOM_TOKEN_ENV=/tmp/.kiwoom_env
```

---

## 2. 서버 실행

### 2.1 로컬 서버 시작
```bash
python main.py
```

또는

```bash
uvicorn main:app --reload
```

서버가 성공적으로 시작되면 다음과 같은 로그가 출력됩니다:
```
INFO:     Stockio v1.0.0 시작
INFO:     디버그 모드: False
INFO:     키움 API 호스트: https://openapi.kiwoom.com
INFO:     환경 변수 검증 완료
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2.2 서버 확인
브라우저에서 다음 URL에 접속:
- http://localhost:8000/ - 서비스 정보
- http://localhost:8000/docs - Swagger UI (API 문서)
- http://localhost:8000/health - 헬스 체크

---

## 3. API 테스트

### 3.1 Health Check
```bash
curl http://localhost:8000/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T23:32:20",
  "service": "Stockio"
}
```

### 3.2 루트 엔드포인트
```bash
curl http://localhost:8000/
```

**예상 응답:**
```json
{
  "service": "Stockio",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "price": "/api/price?code={종목코드}&market={시장구분}",
    "docs": "/docs"
  }
}
```

### 3.3 시세 조회
```bash
curl "http://localhost:8000/api/price?code=005930&market=KOSPI"
```

**현재 상태:**
- ❌ 키움 API 엔드포인트 URL이 정확하지 않아 404 에러 발생
- 🔧 Phase 1.2 단위 시험에서 수정 예정

**예상 응답 (정상):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<stock>
  <code>005930</code>
  <price>71000</price>
  <timestamp>2025-12-22T14:30:00</timestamp>
  <market>KOSPI</market>
</stock>
```

**예상 응답 (에러):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<error>
  <message>시세 조회에 실패했습니다.</message>
  <code>502</code>
  <detail>...</detail>
</error>
```

---

## 4. Phase 1.1 테스트 결과 (2025-12-22)

### 4.1 성공한 항목 ✅
- [x] 서버 시작 및 환경 변수 로드
- [x] Health check 엔드포인트 동작
- [x] 루트 엔드포인트 동작
- [x] 에러 처리 및 XML 응답 생성
- [x] CORS 설정

### 4.2 수정 필요 항목 🔧
- [ ] 키움 API 엔드포인트 URL 확인 및 수정
  - 현재: `/uapi/domestic-stock/v1/quotations/inquire-price` (404 에러)
  - 키움 API 문서 확인 필요
- [ ] 시세 조회 파라미터 확인
  - `fid_cond_mrkt_div_code`, `fid_input_iscd` 등
- [ ] 응답 데이터 파싱 로직 확인
  - `output.stck_prpr` 등의 필드명 확인

---

## 5. 다음 단계 (Phase 1.2: 단위 시험)

1. **키움 API 문서 확인**
   - 현재가 조회 API의 정확한 엔드포인트 및 파라미터 확인
   - 응답 데이터 구조 확인

2. **단위 테스트 작성**
   - `tests/test_kiwoom.py` - 키움 API 클라이언트 테스트
   - `tests/test_api.py` - API 엔드포인트 테스트

3. **실제 시세 조회 테스트**
   - 키움 API 문서를 참고하여 `app/services/kiwoom.py` 수정
   - 실제 종목 코드로 시세 조회 동작 확인

---

## 6. Google Spreadsheet 연동 (Phase 1.3에서 진행)

키움 API 연동이 완료되면 Google Spreadsheet에서 다음과 같이 사용:

```
=IMPORTXML("http://localhost:8000/api/price?code=005930&market=KOSPI", "//price")
```

---

## 참고

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 로그 레벨 변경: `.env` 파일에 `DEBUG=true` 추가
