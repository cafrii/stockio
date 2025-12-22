# Phase 1.2 단위 시험 결과

**테스트 일시**: 2025-12-23
**테스트 환경**: 로컬 개발 환경 (macOS, Python 3.14)

---

## 테스트 항목

### 1. 키움 API 엔드포인트 확인 ✅
- PoC 코드 분석을 통해 API 패턴 파악
- 엔드포인트: `https://api.kiwoom.com/api/dostk/chart`
- Method: POST
- Headers: `authorization`, `api-id`, `cont-yn`, `next-key`
- API ID: `ka10081` (일봉 차트 조회)

### 2. 코드 수정 ✅
- `app/services/kiwoom.py` 수정
  - PoC 패턴에 맞춰 엔드포인트 및 헤더 구조 변경
  - 일봉 차트 API를 사용하여 최근 종가를 현재가로 제공
  - 응답 필드명 수정: `cur_prc` (current price)
- `.env` 파일 수정
  - `KIWOOM_API_HOST`: `https://api.kiwoom.com`

### 3. 토큰 발급 테스트 ✅
**결과**: 성공

```
클라이언트 생성 완료
API 호스트: https://api.kiwoom.com
APPKEY: Koomh2XU07...

토큰 발급 요청 중...
✅ 토큰 발급 성공!
토큰: MJoqDZIK0i0CM4fCv4GK...
만료 시간: 20251223155843

캐시된 토큰 재사용 테스트...
✅ 캐시된 토큰 재사용 성공!
```

**검증 사항**:
- 토큰 발급 API 호출 성공
- 토큰 파일 저장 (`/tmp/.kiwoom_env`)
- 메모리 캐싱 동작 확인
- 토큰 재사용 동작 확인

### 4. 시세 조회 테스트 ✅
**테스트 케이스**: 삼성전자(005930)

**결과**: 성공

```
삼성전자(005930) 시세 조회 중...
✅ 시세 조회 성공!
  종목 코드: 005930
  현재가: 110,500원
  조회 시각: 2025-12-23T00:35:43
  기준 날짜: 20251222
  시장: KOSPI
```

**검증 사항**:
- 키움 API 호출 성공 (일봉 차트 API)
- 응답 데이터 파싱 성공
- 현재가 추출 성공 (`cur_prc` 필드)
- 타임스탬프 생성 성공

### 5. API 엔드포인트 E2E 테스트 ✅

#### 5.1 삼성전자(005930)
```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>005930</code>
  <price>110500</price>
  <timestamp>2025-12-23T00:36:56</timestamp>
  <market>KOSPI</market>
</stock>
```
✅ 성공

#### 5.2 카카오(035720)
```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>035720</code>
  <price>58700</price>
  <timestamp>2025-12-23T00:37:09</timestamp>
  <market>KOSPI</market>
</stock>
```
✅ 성공

#### 5.3 SK하이닉스(000660)
```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>000660</code>
  <price>580000</price>
  <timestamp>2025-12-23T00:37:09</timestamp>
  <market>KOSPI</market>
</stock>
```
✅ 성공

#### 5.4 Health Check
```json
{
  "status": "healthy",
  "timestamp": "2025-12-23T00:37:09",
  "service": "Stockio"
}
```
✅ 성공

---

## 발견된 이슈 및 해결

### 이슈 1: API 호스트 주소 불일치
- **현상**: 404 Not Found 에러
- **원인**: `.env` 파일의 `KIWOOM_API_HOST`가 `https://openapi.kiwoom.com`으로 설정됨
- **해결**: PoC 코드에서 확인된 `https://api.kiwoom.com`으로 수정

### 이슈 2: 응답 필드명 불일치
- **현상**: "현재가 데이터를 찾을 수 없습니다" 에러
- **원인**: 예상 필드명 (`clsp`, `close_price`)이 실제 응답 구조와 다름
- **해결**: 디버그 스크립트로 실제 응답 구조 확인 → `cur_prc` 필드 사용

### 이슈 3: 서버 재시작 문제
- **현상**: 코드 수정 후에도 이전 코드가 실행됨
- **원인**: Python 프로세스가 완전히 종료되지 않음
- **해결**: `pkill -9` 명령으로 강제 종료 후 재시작

---

## 결론

✅ **Phase 1.2 단위 시험 완료**

모든 핵심 기능이 정상 동작합니다:
1. 토큰 발급 및 관리
2. 키움 API 호출 (일봉 차트 조회)
3. 시세 데이터 파싱
4. XML 응답 생성
5. FastAPI 엔드포인트 동작

---

## 다음 단계

**Phase 1.3: 로컬 E2E 테스트**
- Google Spreadsheet에서 IMPORTXML 함수로 실제 연동 테스트
- 다양한 시나리오 검증
- 에러 케이스 테스트

상세 내용은 `docs/milestone.md` 참고.
