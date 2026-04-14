# 토큰 디버깅 가이드

**작성일**: 2025-12-29
**목적**: 토큰 만료 문제 디버깅 및 테스트 방법

---

## 문제 상황

2025-12-23에 Render 배포 후 정상 동작했으나, 12-29에 다음 에러 발생:

```
인증 실패: 인증에 실패했습니다[8005:Token이 유효하지 않습니다]
```

### 원인 분석

키움 API는 **HTTP 200 + `return_code=3`**으로 인증 실패를 알림.
기존 코드는 **HTTP 401에 대한 재시도만 구현**되어 있고, `return_code=3`에 대한 재시도는 없었음.

```python
# 기존 코드 (app/services/kiwoom.py:187-191)
if response.status_code == 401:  # ✅ HTTP 401 재시도
    token = await self.get_token(force_new=True)
    # ...

# 기존 코드 (app/services/kiwoom.py:202-208)
if return_code == 3:  # ❌ 인증 실패인데 재시도 없음!
    raise AuthenticationError(f"인증 실패: {return_msg}")
```

---

## 해결 방법

### 1. 로깅 강화

모든 토큰 관련 작업에 상세 로그 추가:
- 토큰 로드 시도/성공/실패
- 만료 시간 체크 결과
- 새 토큰 발급 과정
- API 호출 및 재시도 과정

### 2. 만료된 토큰 파일 자동 삭제

```python
# app/services/kiwoom.py:65-73
if expire_at < now:
    logger.info(f"토큰 만료됨: expire_at={expire_at}, now={now}")
    # 만료된 토큰 파일 삭제
    try:
        os.remove(self.token_file)
        logger.info("만료된 토큰 파일 삭제 완료")
    except Exception as e:
        logger.warning(f"만료된 토큰 파일 삭제 실패: {e}")
    return None
```

### 3. return_code=3 재시도 로직 추가

```python
# app/services/kiwoom.py:250-270
# return_code=3 인증 에러 - 재시도
if return_code == 3 and not retry_attempted:
    logger.warning("return_code=3 인증 실패 감지 - 토큰 재발급 시도")
    token = await self.get_token(force_new=True)
    headers["authorization"] = f"Bearer {token}"
    response = await client.post(url, headers=headers, json=data, timeout=10.0)
    logger.info("토큰 재발급 후 재시도 완료")
    # ... 재시도 응답 검증
```

---

## 디버그 엔드포인트

### 1. 토큰 상태 확인

```bash
curl http://localhost:8000/debug/token-status
```

**응답 예시**:
```json
{
  "current_time": "2025-12-29 17:25:40",
  "memory_cache": {
    "token_exists": false,
    "token_preview": null,
    "expire_at": null,
    "is_expired": null
  },
  "token_file": {
    "path": "/tmp/.kiwoom_env",
    "exists": true,
    "readable": true,
    "content": {
      "token_preview": "BvMLD8EbbIQBnEGMojQ1...",
      "expire_at": "20251230162204",
      "is_expired": false
    }
  },
  "last_token_issued_at": null
}
```

### 2. 토큰 강제 만료 (테스트용)

```bash
curl -X POST http://localhost:8000/debug/force-expire-token
```

**응답**:
```json
{
  "success": true,
  "message": "토큰이 강제로 만료되었습니다.",
  "timestamp": "2025-12-29T17:25:59"
}
```

---

## 로컬 테스트 절차

### 1. 정상 토큰으로 시세 조회

```bash
curl "http://localhost:8000/api/price?code=000660&market=KOSPI"
```

**결과**: 성공 ✅

**로그**:
```
2025-12-29 17:25:48 - app.services.kiwoom - INFO - 시세 조회 시작: code=000660, market=KOSPI
2025-12-29 17:25:48 - app.services.kiwoom - INFO - 토큰 파일 로드 성공: expire_at=20251230162204
2025-12-29 17:25:48 - app.services.kiwoom - INFO - 시세 조회 성공: code=000660, price=640000
```

### 2. 토큰 강제 만료

```bash
curl -X POST http://localhost:8000/debug/force-expire-token
```

### 3. 만료된 토큰으로 시세 조회 (재발급 테스트)

```bash
curl "http://localhost:8000/api/price?code=005930&market=KOSPI"
```

**결과**: 성공 ✅ (자동 재발급)

**로그**:
```
2025-12-29 17:26:08 - app.services.kiwoom - INFO - 시세 조회 시작: code=005930, market=KOSPI
2025-12-29 17:26:08 - app.services.kiwoom - INFO - 토큰 만료됨: expire_at=20000101000000, now=20251229172608
2025-12-29 17:26:08 - app.services.kiwoom - INFO - 만료된 토큰 파일 삭제 완료
2025-12-29 17:26:08 - app.services.kiwoom - INFO - 새 토큰 발급 필요
2025-12-29 17:26:08 - app.services.kiwoom - INFO - 새 토큰 발급 요청 시작
2025-12-29 17:26:09 - app.services.kiwoom - INFO - 새 토큰 발급 성공: expire_at=20251230162204
2025-12-29 17:26:09 - app.services.kiwoom - INFO - 토큰 파일 저장 완료
2025-12-29 17:26:09 - app.services.kiwoom - INFO - 시세 조회 성공: code=005930, price=119500
```

---

## Render 배포 환경에서 디버깅

### 1. 토큰 상태 확인

```bash
curl https://stockio.onrender.com/debug/token-status
```

### 2. 로그 확인

Render 대시보드 → 서비스 선택 → "Logs" 탭 클릭

**주요 로그 키워드**:
- `토큰 만료됨`
- `새 토큰 발급 요청 시작`
- `return_code=3 인증 실패 감지`
- `토큰 재발급 후 재시도 완료`

### 3. 토큰 강제 만료 테스트

```bash
# 1. 토큰 만료
curl -X POST https://stockio.onrender.com/debug/force-expire-token

# 2. 시세 조회 (자동 재발급 확인)
curl "https://stockio.onrender.com/api/price?code=005930&market=KOSPI"

# 3. 로그 확인 (Render 대시보드)
```

---

## 예상되는 에러 케이스

### Case 1: HTTP 401 에러

**로그**:
```
WARNING - HTTP 401 인증 에러 발생 - 토큰 재발급 시도
INFO - 토큰 재발급 후 재시도 완료
```

**처리**: 자동 재발급 및 재시도 ✅

### Case 2: return_code=3 에러

**로그**:
```
WARNING - API 에러 응답: return_code=3, msg=인증에 실패했습니다
WARNING - return_code=3 인증 실패 감지 - 토큰 재발급 시도
INFO - 토큰 재발급 후 재시도 완료
```

**처리**: 자동 재발급 및 재시도 ✅

### Case 3: 토큰 만료 (파일 기반)

**로그**:
```
INFO - 토큰 만료됨: expire_at=20000101000000, now=20251229172608
INFO - 만료된 토큰 파일 삭제 완료
INFO - 새 토큰 발급 필요
INFO - 새 토큰 발급 성공
```

**처리**: 자동 재발급 ✅

---

## 변경 사항 요약

### 수정된 파일

1. **app/services/kiwoom.py**
   - 로깅 강화 (모든 토큰 관련 작업)
   - 만료된 토큰 파일 자동 삭제
   - `return_code=3` 재시도 로직 추가
   - `get_token_status()` 메서드 추가
   - `force_expire_token()` 메서드 추가

2. **app/api/routes.py**
   - `/debug/token-status` 엔드포인트 추가
   - `/debug/force-expire-token` 엔드포인트 추가

### 테스트 결과

- ✅ 정상 토큰으로 시세 조회
- ✅ 만료된 토큰 자동 감지 및 재발급
- ✅ HTTP 401 에러 재시도
- ✅ return_code=3 에러 재시도
- ✅ 로그 출력 완벽

---

## 다음 단계

1. GitHub에 코드 push
2. Render 자동 배포
3. 배포 후 `/debug/token-status`로 상태 확인
4. 며칠 후 토큰 자연 만료 시 로그 확인

---

## 참고

- 키움 API 토큰 유효기간: 약 24시간
- Render 무료 Tier `/tmp/` 디렉토리: ephemeral (재시작 시 초기화)
- 로그 레벨: INFO (프로덕션), DEBUG (개발)
