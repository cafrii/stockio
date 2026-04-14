# Render 배포 가이드

**작성일**: 2025-12-23
**대상 플랫폼**: Render (https://render.com)
**서비스 유형**: Web Service (Free Tier)

---

## 사전 준비

### 1. Render 계정
- Render 계정이 없다면 https://render.com 에서 가입
- GitHub 계정으로 로그인 권장

### 2. GitHub Repository
- Repository: `cafrii/stockio`
- 최신 코드가 push 되어 있어야 함

### 3. 키움 API 인증 정보
다음 정보를 준비:
- `KIWOOM_API_APPKEY`: 키움증권 앱 키
- `KIWOOM_API_SECRET`: 키움증권 시크릿 키
- `KIWOOM_API_HOST`: https://api.kiwoom.com

---

## 배포 단계

### Step 1: GitHub Push

현재 수정된 파일들을 GitHub에 push:

```bash
# 변경사항 확인
git status

# 수정된 파일 추가
git add app/api/routes.py app/services/kiwoom.py main.py docs/status.md runtime.txt

# 커밋
git commit -m "Phase 1.3.1 & 1.3.2 완료: 비동기 구조 전환 및 코드 품질 개선

- requests → httpx.AsyncClient 완전 비동기 전환
- lifespan 패턴으로 마이그레이션 (DeprecationWarning 제거)
- Validation 에러 XML 형식 통일
- 시장 구분 약어(J, Q) 지원 추가
- Render 배포 준비 (runtime.txt 추가)

# Push
git push origin main
```

### Step 2: Render에서 New Web Service 생성

1. **Render 대시보드 접속**
   - https://dashboard.render.com 로그인

2. **New Web Service 클릭**
   - 우측 상단 "New +" → "Web Service" 선택

3. **GitHub Repository 연결**
   - "Connect a repository" 선택
   - `cafrii/stockio` 검색 후 "Connect" 클릭

### Step 3: 서비스 설정

**Basic Settings:**
- **Name**: `stockio` (또는 원하는 이름)
- **Region**: `Singapore` (가장 가까운 리전)
- **Branch**: `main`
- **Runtime**: `Python 3`

**Build & Deploy:**
- **Build Command**:
  ```
  pip install -r requirements.txt
  ```

- **Start Command**:
  ```
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```

**Instance Type:**
- **Free** 선택 (무료 티어)

### Step 4: 환경 변수 설정

"Environment" 탭에서 다음 환경 변수 추가:

| Key | Value | 비고 |
|-----|-------|------|
| `KIWOOM_API_APPKEY` | (실제 앱 키) | 키움증권에서 발급받은 값 |
| `KIWOOM_API_SECRET` | (실제 시크릿 키) | 키움증권에서 발급받은 값 |
| `KIWOOM_API_HOST` | `https://api.kiwoom.com` | 키움 API 호스트 |
| `KIWOOM_TOKEN_ENV` | `/tmp/.kiwoom_env` | 토큰 캐시 파일 경로 (선택사항) |

**주의사항**:
- 환경 변수는 암호화되어 저장됨
- API 키는 절대 GitHub에 커밋하지 말 것
- `KIWOOM_TOKEN_ENV`는 생략 가능 (기본값 사용)

### Step 5: 배포 시작

- **"Create Web Service"** 클릭
- 자동으로 빌드 및 배포 시작
- 로그에서 진행 상황 확인

### Step 6: 배포 완료 확인

배포가 완료되면 다음과 같은 URL이 생성됩니다:
```
https://stockio.onrender.com
```

**Health Check**:
```bash
curl https://stockio.onrender.com/health
```

**예상 응답**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-23T11:00:00",
  "service": "Stockio"
}
```

---

## 배포 후 테스트

### 1. 기본 엔드포인트 테스트

```bash
# Health Check
curl https://stockio.onrender.com/health

# 루트 엔드포인트
curl https://stockio.onrender.com/

# API 문서
# 브라우저에서 https://stockio.onrender.com/docs 접속
```

### 2. 시세 조회 테스트

```bash
# KOSPI - 삼성전자
curl "https://stockio.onrender.com/api/price?code=005930&market=KOSPI"

# KOSDAQ - 에코프로비엠 (약어 사용)
curl "https://stockio.onrender.com/api/price?code=247540&market=Q"
```

### 3. Google Spreadsheet 연동

```
=IMPORTXML("https://stockio.onrender.com/api/price?code=005930&market=KOSPI", "//price")
```

자세한 내용은 `docs/google_sheets_guide.md` 참조

---

## Render Free Tier 제한사항

### 1. 자동 Sleep
- **15분간 요청이 없으면 자동으로 sleep 상태로 전환**
- Sleep 후 첫 요청 시 cold start (30초~1분 소요)
- Google Sheets에서 첫 조회 시 지연 발생 가능

### 2. Ephemeral Filesystem
- **재배포/재시작 시 파일 시스템 초기화**
- `/tmp/.kiwoom_env` 토큰 파일은 재시작 시 삭제됨
- 메모리 캐시만 유지 (재시작 시 토큰 재발급)

### 3. 월 사용량 제한
- Free Tier: 월 750시간 무료
- 초과 시 서비스 일시 중단 또는 유료 전환 필요

### 4. 커스텀 도메인
- Free Tier는 `*.onrender.com` 서브도메인만 사용 가능
- 커스텀 도메인은 유료 플랜 필요

---

## 문제 해결

### Cold Start 시간이 너무 길어요
- Free Tier의 특성상 불가피함
- 유료 플랜으로 업그레이드 고려
- 또는 주기적으로 health check 요청 (cron job)

### 환경 변수가 적용되지 않아요
- Render 대시보드에서 환경 변수 확인
- 환경 변수 변경 후 "Manual Deploy" 클릭하여 재배포

### 토큰 발급 에러가 발생해요
- 환경 변수 `KIWOOM_API_APPKEY`, `KIWOOM_API_SECRET` 확인
- Render 로그에서 에러 메시지 확인
- 키움 API 인증 정보가 올바른지 확인

### 배포가 실패해요
- Render 로그에서 에러 메시지 확인
- `requirements.txt` 의존성 문제인지 확인
- Python 버전 호환성 확인 (`runtime.txt`)

---

## 모니터링

### Render 대시보드
- **Logs**: 실시간 로그 확인
- **Metrics**: CPU, 메모리 사용량 확인
- **Events**: 배포 이력 확인

### 추천 모니터링 방법
- Google Sheets에서 주기적으로 시세 조회하여 상태 확인
- Uptime monitoring 서비스 사용 (예: UptimeRobot)

---

## 다음 단계

배포 완료 후:
1. `docs/google_sheets_guide.md`를 참고하여 Google Spreadsheet 연동
2. 실제 종목 데이터로 테스트
3. Phase 2 기능 추가 계획 (캐싱, 다중 종목 조회 등)

---

**배포 관련 문의**:
- Render 문서: https://render.com/docs
- 프로젝트 이슈: https://github.com/cafrii/stockio/issues
