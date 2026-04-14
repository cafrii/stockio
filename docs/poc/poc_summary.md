

이 리포지토리는 원래 키움증권의 REST API를 이용한 몇 가지 시험적인 코드들을 연습하기 위한 작업들의 기록용이었다. 

지금은 그 작업은 중단된 상태이다. 마지막으로 작업 한지 수 개월이 지났고 지금은 더 이상 관리되지 않고 있다.

당시 작업한 코드들은 모두 poc/ 아래에 위치해 있다.

poc/src/query_*.py 코드들은 각각 특정 API를 시험하기 위한 목적으로 작성되었다.
일부는 작성 진행 중인 상태에서 멈추었을 것이므로 모두 다 100% 동작한다고 보장할 수는 없다.

poc/docs/ 아래에 있는 다음 문서들을 참고하면 도움이 된다.
- PoC.md
- Logging.md
- Security.md
- Terms.md

유효기간이 짧은 이 토큰은 재활용을 위해 아래 경로에 임시로 저장하게 하고 있다.
- /tmp/.kiwoom_env

코드에서는 다음과 같이 정의해서 사용중이다.
KIWOOM_TOKEN_ENV = "/tmp/.kiwoom_env"

이 리포지토리의 .kiwoom_env 는 위 임시 저장 파일의 symlink이다. (개발 편의)

각 query 테스트 코드의 결과는 로그로 출력하게만 되어 있다.
환경변수 dbg=root:debug 를 추가하여 로그를 확인할 수 있다.

예:
```
# 삼성전자 주식 일봉 차트 정보
dbg=root:debug python3 query_chart_day.py 005930

```




