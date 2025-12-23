# 배포 후 검증 가이드

**작성일**: 2025-12-23
**목적**: Render 배포 후 서비스가 정상 동작하는지 단계별로 검증

---

## 검증 체크리스트

### ✅ Step 1: 배포 완료 확인

**Render 대시보드에서 확인**:
- [ ] 빌드 성공 (Build Logs에서 "Build succeeded" 확인)
- [ ] 서비스 실행 중 (Status: "Live" 표시)
- [ ] URL 생성됨 (`https://stockio-xxxx.onrender.com`)

**배포 로그에서 확인**:
```
INFO:     Stockio v1.0.0 시작
INFO:     디버그 모드: False
INFO:     키움 API 호스트: https://api.kiwoom.com
INFO:     환경 변수 검증 완료
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:xxxx
```

---

### ✅ Step 2: Health Check

**명령어**:
```bash
curl https://YOUR-APP-NAME.onrender.com/health
```

**예상 응답**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-23T11:00:00",
  "service": "Stockio"
}
```

**검증 항목**:
- [ ] HTTP 200 응답
- [ ] JSON 형식
- [ ] status: "healthy"
- [ ] timestamp가 현재 시간 (UTC)

---

### ✅ Step 3: 루트 엔드포인트

**명령어**:
```bash
curl https://YOUR-APP-NAME.onrender.com/
```

**예상 응답**:
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

**검증 항목**:
- [ ] HTTP 200 응답
- [ ] 서비스 정보 표시
- [ ] 엔드포인트 목록 확인

---

### ✅ Step 4: API 문서 확인

**브라우저에서 접속**:
```
https://YOUR-APP-NAME.onrender.com/docs
```

**검증 항목**:
- [ ] Swagger UI 표시
- [ ] `/health` 엔드포인트 보임
- [ ] `/api/price` 엔드포인트 보임
- [ ] "Try it out" 버튼으로 테스트 가능

---

### ✅ Step 5: 시세 조회 - KOSPI (정식 명칭)

**명령어**:
```bash
curl "https://YOUR-APP-NAME.onrender.com/api/price?code=005930&market=KOSPI"
```

**예상 응답**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>005930</code>
  <price>112000</price>
  <timestamp>2025-12-23T11:00:00</timestamp>
  <market>KOSPI</market>
</stock>
```

**검증 항목**:
- [ ] HTTP 200 응답
- [ ] XML 형식
- [ ] 종목 코드 일치
- [ ] 가격 데이터 존재
- [ ] market이 "KOSPI"

---

### ✅ Step 6: 시세 조회 - KOSDAQ (약어 사용)

**명령어**:
```bash
curl "https://YOUR-APP-NAME.onrender.com/api/price?code=247540&market=Q"
```

**예상 응답**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>247540</code>
  <price>158100</price>
  <timestamp>2025-12-23T11:00:00</timestamp>
  <market>KOSDAQ</market>
</stock>
```

**검증 항목**:
- [ ] HTTP 200 응답
- [ ] market이 "KOSDAQ" (약어 "Q" 변환 성공)
- [ ] KOSDAQ 종목 정상 조회

---

### ✅ Step 7: 에러 처리 - Validation 에러

**명령어** (빈 종목 코드):
```bash
curl "https://YOUR-APP-NAME.onrender.com/api/price?code=&market=KOSPI"
```

**예상 응답**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<error>
  <message>파라미터 검증 실패: code</message>
  <code>400</code>
  <detail>String should have at least 6 characters</detail>
</error>
```

**검증 항목**:
- [ ] HTTP 400 응답
- [ ] XML 형식 (JSON 아님!)
- [ ] 에러 메시지 명확

---

### ✅ Step 8: 에러 처리 - 잘못된 종목 코드

**명령어**:
```bash
curl "https://YOUR-APP-NAME.onrender.com/api/price?code=999999&market=KOSPI"
```

**예상 응답**:
```xml
<?xml version="1.0" encoding="utf-8"?>
<error>
  <message>시세 조회에 실패했습니다.</message>
  <code>502</code>
  <detail>현재가 데이터를 찾을 수 없습니다</detail>
</error>
```

**검증 항목**:
- [ ] HTTP 502 응답
- [ ] XML 형식
- [ ] 적절한 에러 메시지

---

### ✅ Step 9: 토큰 발급 확인

**Render 로그에서 확인**:
```
INFO:     시세 조회 성공: 005930 (KOSPI) = 112000
```

**첫 번째 시세 조회 후 로그 확인**:
- [ ] 토큰 발급 메시지 없음 (이미 캐시된 토큰 사용)
- 또는
- [ ] 토큰 발급 성공 로그 (첫 실행 또는 재시작 후)

**주의사항**:
- 토큰은 메모리에 캐시됨
- 서버 재시작 시 자동으로 재발급

---

### ✅ Step 10: Google Spreadsheet 연동

**Google Sheets에서 테스트**:

**1. 기본 시세 조회**:
```
=IMPORTXML("https://YOUR-APP-NAME.onrender.com/api/price?code=005930&market=KOSPI", "//price")
```
- [ ] 가격 데이터 표시 (예: 112000)

**2. 여러 필드 조회**:
```
=IMPORTXML("https://YOUR-APP-NAME.onrender.com/api/price?code=005930&market=KOSPI", "//stock/*")
```
- [ ] code, price, timestamp, market 모두 표시

**3. KOSDAQ 종목 (약어)**:
```
=IMPORTXML("https://YOUR-APP-NAME.onrender.com/api/price?code=247540&market=Q", "//price")
```
- [ ] KOSDAQ 종목 정상 조회

---

## 성능 테스트

### Cold Start 측정

**서비스 Sleep 후 첫 요청**:
```bash
time curl "https://YOUR-APP-NAME.onrender.com/health"
```

**예상 시간**:
- **Cold Start**: 30초 ~ 1분
- **Warm Start**: 1초 이하

**검증 항목**:
- [ ] Cold start 시간 확인 (Free Tier 특성)
- [ ] Warm start 시간 확인 (정상 응답 속도)

### 연속 요청 테스트

**여러 종목 연속 조회**:
```bash
for code in 005930 035720 000660; do
  curl "https://YOUR-APP-NAME.onrender.com/api/price?code=$code&market=KOSPI"
  echo ""
done
```

**검증 항목**:
- [ ] 모든 요청 성공
- [ ] 응답 속도 일정 (캐시된 토큰 사용)
- [ ] 메모리 누수 없음 (Render Metrics 확인)

---

## 문제 발생 시 체크포인트

### 1. 배포가 실패한 경우
- [ ] Render 빌드 로그 확인
- [ ] `requirements.txt` 문법 오류 확인
- [ ] Python 버전 호환성 (`runtime.txt`)

### 2. 환경 변수 에러
- [ ] Render 대시보드에서 환경 변수 설정 확인
- [ ] `KIWOOM_API_APPKEY`, `KIWOOM_API_SECRET` 값 확인
- [ ] 환경 변수 변경 후 재배포 (Manual Deploy)

### 3. 토큰 발급 실패
- [ ] Render 로그에서 에러 메시지 확인
- [ ] 키움 API 인증 정보 유효성 확인
- [ ] `KIWOOM_API_HOST` 값 확인

### 4. 시세 조회 실패
- [ ] 종목 코드 6자리 확인
- [ ] 시장 구분 (KOSPI/KOSDAQ/J/Q) 확인
- [ ] 키움 API 응답 에러 확인 (Render 로그)

### 5. Google Sheets 에러
- [ ] IMPORTXML 함수 문법 확인
- [ ] XPath 표현식 확인 (`//price`, `//stock/*`)
- [ ] Render 서비스가 Live 상태인지 확인
- [ ] Cold start 대기 시간 고려 (1분 정도 기다려보기)

---

## 검증 완료 기준

다음 항목을 모두 통과하면 배포 성공:

**필수 항목**:
- [x] Health check 정상 응답
- [x] KOSPI 종목 시세 조회 성공
- [x] KOSDAQ 종목 시세 조회 성공 (market 필드 "KOSDAQ")
- [x] Validation 에러 XML 형식 반환
- [x] 잘못된 종목 코드 에러 처리
- [x] Google Sheets IMPORTXML 정상 동작

**선택 항목**:
- [ ] API 문서 (/docs) 접근 가능
- [ ] 시장 구분 약어 (J, Q) 정상 동작
- [ ] 연속 요청 시 안정적 응답

---

## 다음 단계

검증 완료 후:
1. `docs/status.md` 업데이트 (Phase 1.4 완료 기록)
2. Google Spreadsheet에서 실제 사용 시작
3. 사용자 피드백 수집
4. Phase 2 계획 수립

---

**검증 관련 문의**:
- GitHub Issues: https://github.com/cafrii/stockio/issues
