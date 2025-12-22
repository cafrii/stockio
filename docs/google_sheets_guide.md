# Google Spreadsheet 연동 가이드

## 개요

이 문서는 Google Spreadsheet에서 IMPORTXML 함수를 사용하여 Stockio 서비스에서 주식 시세 데이터를 가져오는 방법을 설명합니다.

---

## 1. 로컬 환경에서 테스트

### 1.1 로컬 서버 실행

```bash
# 가상환경 활성화 (필요시)
source .venv/bin/activate

# 서버 실행
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 1.2 터널링 도구 설치 (ngrok)

Google Sheets는 외부에서 로컬 서버에 직접 접근할 수 없으므로, ngrok과 같은 터널링 도구가 필요합니다.

```bash
# ngrok 설치 (Homebrew 사용시)
brew install ngrok

# ngrok 실행
ngrok http 8000
```

ngrok이 제공하는 공개 URL을 확인합니다 (예: `https://abcd1234.ngrok.io`).


---

## 2. Google Spreadsheet 설정

### 2.1 새 시트 생성

1. [Google Spreadsheet](https://sheets.google.com)에서 새 시트를 생성합니다.
2. 다음과 같이 헤더를 작성합니다:

| A열 | B열 | C열 | D열 |
|-----|-----|-----|-----|
| 종목명 | 종목코드 | 시장 | 현재가 |

### 2.2 IMPORTXML 함수 작성

#### 기본 예제 (삼성전자)

D2 셀에 다음 수식을 입력합니다:

```
=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code=005930&market=J", "//price")
```

- `your-ngrok-url`을 실제 ngrok URL로 변경
- `//price`는 XML의 `<price>` 태그를 추출하는 XPath 표현식

#### 다양한 종목 예제

| A열 | B열 | C열 | D열 (수식) |
|-----|-----|-----|-----|
| 삼성전자 | 005930 | J | `=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code="&B2&"&market="&C2, "//price")` |
| 카카오 | 035720 | J | `=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code="&B3&"&market="&C3, "//price")` |
| SK하이닉스 | 000660 | J | `=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code="&B4&"&market="&C4, "//price")` |

### 2.3 동적 수식 (권장)

B열과 C열을 참조하여 동적으로 수식을 작성하면 편리합니다:

```
=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code="&B2&"&market="&C2, "//price")
```

이렇게 하면 B열과 C열만 변경하면 자동으로 시세가 업데이트됩니다.

---

## 3. XPath 표현식

XML 응답 구조:

```xml
<?xml version="1.0" encoding="utf-8"?>
<stock>
  <code>005930</code>
  <price>110500</price>
  <timestamp>2025-12-23T00:52:15</timestamp>
  <market>KOSPI</market>
</stock>
```

### 사용 가능한 XPath

| 필드 | XPath | 설명 |
|------|-------|------|
| 종목코드 | `//code` | 종목 코드 |
| 현재가 | `//price` | 현재 가격 |
| 조회시각 | `//timestamp` | 조회 시각 |
| 시장구분 | `//market` | 시장 구분 (KOSPI/KOSDAQ) |

### 전체 데이터 가져오기

여러 필드를 한 번에 가져오려면:

```
=IMPORTXML("https://your-ngrok-url.ngrok.io/api/price?code=005930&market=J", "//stock/*")
```

---

## 4. 테스트 체크리스트

### 4.1 기본 동작 확인

- [ ] 로컬 서버가 정상 실행되는가?
- [ ] ngrok이 정상 동작하는가?
- [ ] Google Sheets에서 IMPORTXML 함수가 데이터를 가져오는가?

### 4.2 다양한 종목 테스트

- [ ] 삼성전자 (005930, KOSPI)
- [ ] 카카오 (035720, KOSPI)
- [ ] SK하이닉스 (000660, KOSPI)
- [ ] KODEX 200 (069500, ETF)
- [ ] 코스닥 종목 (예: 247540, 086520)

### 4.3 에러 케이스

- [ ] 잘못된 종목 코드 입력 시 에러 메시지가 표시되는가?
- [ ] 네트워크 에러 시 적절한 에러 메시지가 표시되는가?

---

## 5. 문제 해결

### IMPORTXML이 작동하지 않는 경우

1. **ngrok URL 확인**: ngrok이 실행 중이고 URL이 정확한지 확인
2. **서버 로그 확인**: `python main.py`를 실행한 터미널에서 요청 로그 확인
3. **브라우저에서 직접 테스트**: ngrok URL을 브라우저에서 열어서 XML 응답이 정상적으로 반환되는지 확인
4. **CORS 설정 확인**: main.py의 CORS 설정이 모든 origin을 허용하는지 확인

### 데이터가 업데이트되지 않는 경우

- Google Sheets는 IMPORTXML 캐시를 사용하므로, 강제 새로고침이 필요할 수 있습니다
- 수식을 약간 변경했다가 다시 되돌리면 캐시가 갱신됩니다
- 또는 `Ctrl+Shift+F9` (Windows) / `Cmd+Shift+F9` (Mac)으로 강제 새로고침

---

## 6. 실전 활용 예제

### 6.1 포트폴리오 관리 시트

| 종목명 | 종목코드 | 시장 | 보유수량 | 현재가 | 평가금액 |
|--------|---------|------|---------|--------|---------|
| 삼성전자 | 005930 | J | 10 | `=IMPORTXML(...)` | `=D2*E2` |
| 카카오 | 035720 | J | 5 | `=IMPORTXML(...)` | `=D3*E3` |

### 6.2 조건부 서식

현재가에 조건부 서식을 적용하여 가격 변동을 시각화할 수 있습니다.

---

## 7. 주의사항

- **API 호출 제한**: 키움 API에는 호출 제한이 있을 수 있습니다
- **캐싱**: Google Sheets는 IMPORTXML 결과를 캐시하므로 실시간 업데이트가 아닙니다
- **장 시간**: 증권 시장 폐장 시간에는 시세가 업데이트되지 않습니다
- **네트워크 보안**: ngrok을 사용하면 로컬 서버가 공개되므로, API 키 등 민감한 정보가 노출되지 않도록 주의

---

## 8. 다음 단계 (Phase 1.4)

로컬 테스트가 완료되면 Render 등의 클라우드 플랫폼에 배포하여 ngrok 없이도 사용할 수 있습니다.

배포 후에는 ngrok URL 대신 배포된 서버 URL을 사용하면 됩니다:

```
=IMPORTXML("https://your-app.onrender.com/api/price?code=005930&market=J", "//price")
```
