
# 동작 환경
- 본 리포지토리의 코드 동작은 venv 가상 환경을 이용하여 진행됩니다.
```
$ python3 -m venv .venv
# 현재 폴더에 .venv/ 폴더 트리가 생성됨.

$ . .venv/bin/activate

(.venv)프롬프트 변경됨. 이하 작업 진행.

# 가상환경 종료
$ deactivate
```

- 참고로, .venv 폴더는 .gitignore 에 등록되어 있습니다. 폴더 명 변경 시 .gitignore 에 추가해 주는 것이 좋습니다.

- 가상환경에 진입했다면, 패키지는 pip (또는 pip3) 으로 설치하면 됩니다.
```
(.venv) $ pip install <패키지이름>
```


<br>

# 설치 필요한 패키지
이 리포지토리의 코드를 실행하기 위해 필요한 패키지를 설명합니다.

- requests
- dotenv
- pandas
- beautifulsoup4 html2text

<br>
한번에 다 설치하기

```
pip install -U requests dotenv pandas beautifulsoup4 html2text
```
