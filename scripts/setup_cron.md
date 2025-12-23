# Keep-Alive Cron Job 설정 가이드 (macOS)

## 개요

Render Free Tier는 15분간 요청이 없으면 서비스가 sleep 상태로 전환됩니다.
이를 방지하기 위해 주기적으로 health check를 호출하는 cron job을 설정합니다.

---

## 방법 1: Crontab 사용 (권장 - 간단함)

### 1. 스크립트 테스트

먼저 스크립트가 정상 동작하는지 확인:

```bash
# 프로젝트 디렉토리로 이동
cd /Users/yhlee/work/ai/test-api-kiwoom

# 스크립트 실행 테스트
./scripts/keep_alive.sh

# 로그 확인
tail -f ~/.stockio_keepalive.log
```

**예상 출력**:
```
[2025-12-23 11:30:00] Keep-alive ping started...
[2025-12-23 11:30:01] ✅ Success (HTTP 200)
[2025-12-23 11:30:01] Keep-alive ping completed.
```

### 2. Crontab 편집

```bash
crontab -e
```

**처음 실행하는 경우**:
- 에디터 선택 프롬프트가 나타남
- `nano` (초보자 친화적) 또는 `vim` 선택

### 3. Cron Job 추가

에디터에서 다음 라인 추가:

```cron
# Stockio Keep-Alive (10분마다 실행)
*/10 * * * * /Users/yhlee/work/ai/test-api-kiwoom/scripts/keep_alive.sh

# 또는 5분마다 실행 (더 확실함)
# */5 * * * * /Users/yhlee/work/ai/test-api-kiwoom/scripts/keep_alive.sh
```

**Cron 문법**:
```
┌─────── 분 (0-59)
│ ┌───── 시 (0-23)
│ │ ┌─── 일 (1-31)
│ │ │ ┌─ 월 (1-12)
│ │ │ │ ┌ 요일 (0-7, 0과 7은 일요일)
│ │ │ │ │
* * * * * 명령어
```

**예시**:
- `*/10 * * * *` = 10분마다
- `*/5 * * * *` = 5분마다
- `0 * * * *` = 매시 정각
- `0 9-18 * * 1-5` = 평일 9시~18시 사이 매시 정각

### 4. 저장 및 종료

- **nano**: `Ctrl + O` (저장) → `Enter` → `Ctrl + X` (종료)
- **vim**: `ESC` → `:wq` → `Enter`

### 5. Crontab 확인

```bash
# 등록된 cron job 목록 확인
crontab -l
```

### 6. macOS 권한 허용

macOS Catalina 이상에서는 cron이 디스크 접근 권한이 필요할 수 있습니다.

**권한 에러 발생 시**:
1. **시스템 설정** → **개인정보 보호 및 보안** → **전체 디스크 접근 권한**
2. `+` 버튼 클릭
3. `/usr/sbin/cron` 추가
4. 또는 **터미널** 앱 자체를 추가

### 7. 로그 모니터링

```bash
# 실시간 로그 확인
tail -f ~/.stockio_keepalive.log

# 최근 10줄 확인
tail -n 10 ~/.stockio_keepalive.log

# 오늘의 로그만 확인
grep "$(date '+%Y-%m-%d')" ~/.stockio_keepalive.log
```

### 8. Cron Job 제거 (필요시)

```bash
# crontab 편집기 열기
crontab -e

# 해당 라인 삭제 후 저장

# 또는 모든 cron job 제거
# crontab -r
```

---

## 방법 2: Launchd 사용 (macOS 권장 방법)

macOS에서는 launchd가 cron보다 권장되는 방식입니다.

### 1. Plist 파일 생성

```bash
nano ~/Library/LaunchAgents/com.stockio.keepalive.plist
```

### 2. Plist 내용 작성

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stockio.keepalive</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/yhlee/work/ai/test-api-kiwoom/scripts/keep_alive.sh</string>
    </array>

    <key>StartInterval</key>
    <integer>600</integer>  <!-- 600초 = 10분 -->

    <key>StandardOutPath</key>
    <string>/Users/yhlee/.stockio_keepalive_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/yhlee/.stockio_keepalive_stderr.log</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

### 3. Launchd 로드

```bash
# plist 로드
launchctl load ~/Library/LaunchAgents/com.stockio.keepalive.plist

# 즉시 실행 (테스트)
launchctl start com.stockio.keepalive

# 상태 확인
launchctl list | grep stockio
```

### 4. Launchd 관리 명령어

```bash
# 로드 (시작)
launchctl load ~/Library/LaunchAgents/com.stockio.keepalive.plist

# 언로드 (중지)
launchctl unload ~/Library/LaunchAgents/com.stockio.keepalive.plist

# 상태 확인
launchctl list | grep stockio

# 로그 확인
tail -f ~/.stockio_keepalive_stdout.log
tail -f ~/.stockio_keepalive_stderr.log
```

---

## 검증

### 1. 동작 확인

10분 후 로그 확인:

```bash
tail -n 20 ~/.stockio_keepalive.log
```

**예상 로그**:
```
[2025-12-23 11:00:00] Keep-alive ping started...
[2025-12-23 11:00:01] ✅ Success (HTTP 200)
[2025-12-23 11:00:01] Keep-alive ping completed.
[2025-12-23 11:10:00] Keep-alive ping started...
[2025-12-23 11:10:01] ✅ Success (HTTP 200)
[2025-12-23 11:10:01] Keep-alive ping completed.
```

### 2. Render 대시보드 확인

Render 대시보드에서:
- **Metrics** 탭에서 Request 그래프 확인
- 10분마다 규칙적인 요청 패턴 확인
- 서비스가 "Live" 상태 유지 확인

---

## 문제 해결

### 스크립트가 실행되지 않아요

**1. 실행 권한 확인**:
```bash
ls -la scripts/keep_alive.sh
# -rwxr-xr-x 여야 함

# 권한 없으면 부여
chmod +x scripts/keep_alive.sh
```

**2. 절대 경로 사용**:
Cron에서는 상대 경로 사용 불가. 절대 경로 사용:
```cron
*/10 * * * * /Users/yhlee/work/ai/test-api-kiwoom/scripts/keep_alive.sh
```

**3. 환경 변수 확인**:
Cron은 제한된 환경 변수를 가짐. 스크립트 상단에 PATH 추가:
```bash
#!/bin/bash
export PATH=/usr/local/bin:/usr/bin:/bin
```

### Cron이 실행되지 않아요

**1. Cron 서비스 확인** (macOS):
```bash
# Cron 프로세스 확인
ps aux | grep cron

# Cron 재시작 (필요시)
sudo launchctl stop com.vix.cron
sudo launchctl start com.vix.cron
```

**2. 로그 확인**:
```bash
# 시스템 로그 확인
log show --predicate 'process == "cron"' --last 1h

# macOS 개인정보 보호 설정 확인
# 시스템 설정 → 개인정보 보호 → 전체 디스크 접근 권한
```

### 로그 파일이 생성되지 않아요

**권한 문제**:
```bash
# 로그 디렉토리 권한 확인
ls -la ~/.stockio_keepalive.log

# 수동으로 생성 및 권한 부여
touch ~/.stockio_keepalive.log
chmod 644 ~/.stockio_keepalive.log
```

---

## 대안: 외부 Uptime Monitoring 서비스

Cron job 대신 외부 서비스 사용 가능:

### 1. UptimeRobot (무료)
- https://uptimerobot.com
- 5분 간격 모니터링 (무료)
- URL: `https://stockio.onrender.com/health`
- 다운타임 알림 기능

### 2. Cron-Job.org (무료)
- https://cron-job.org
- 웹 기반 cron job 서비스
- 1분 간격까지 가능

### 3. BetterUptime (무료 티어)
- https://betteruptime.com
- 모니터링 + 상태 페이지 제공

---

## 권장 설정

**개발/테스트 환경**:
- Crontab 사용
- 10분 간격
- 로컬 맥에서 실행

**프로덕션 환경**:
- UptimeRobot 같은 외부 서비스 사용
- 5분 간격
- 다운타임 알림 설정
- 맥 종료 시에도 동작

---

## 참고

- Render Free Tier: 15분 idle → sleep
- Keep-alive 권장 간격: 5~10분
- 로그 파일 크기: 자동으로 1000줄로 제한
- macOS sleep 시 cron 중단: 맥을 항상 켜두거나 외부 서비스 사용

---

**문의**: GitHub Issues (https://github.com/cafrii/stockio/issues)
