#!/bin/bash

# Render 서비스 Keep-Alive 스크립트
# Render Free Tier의 15분 idle sleep 방지

# 설정
SERVICE_URL="https://stockio.onrender.com"
LOG_FILE="$HOME/.stockio_keepalive.log"
MAX_LOG_LINES=1000

# 로그 디렉토리 확인
mkdir -p "$(dirname "$LOG_FILE")"

# 현재 시간
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Health check 호출
echo "[$TIMESTAMP] Keep-alive ping started..." >> "$LOG_FILE"

# curl 호출 (타임아웃 30초)
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" --max-time 30 "$SERVICE_URL/health" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | sed 's/HTTP_CODE://')
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ]; then
    echo "[$TIMESTAMP] ✅ Success (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    # echo "$BODY" >> "$LOG_FILE"  # 필요시 응답 본문도 기록
else
    echo "[$TIMESTAMP] ❌ Failed (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    echo "$RESPONSE" >> "$LOG_FILE"
fi

# 로그 파일 크기 제한 (최근 1000줄만 유지)
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    if [ "$LINE_COUNT" -gt "$MAX_LOG_LINES" ]; then
        tail -n "$MAX_LOG_LINES" "$LOG_FILE" > "$LOG_FILE.tmp"
        mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
fi

echo "[$TIMESTAMP] Keep-alive ping completed." >> "$LOG_FILE"
