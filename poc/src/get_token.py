
import requests
import json

# this module cannot use imports.py
import os, dotenv
from utils_exception import *
from logging import debug,info,warning,error
from config import KIWOOM_API_HOST


KIWOOM_TOKEN_ENV = "/tmp/.kiwoom_env"


#---- 다른 모듈로 분리 필요한가?

from bs4 import BeautifulSoup
import html2text

def ExtractMessageFromHtml(html_content):
	'''
	'''
	soup = BeautifulSoup(html_content, 'html.parser')
	# debug('soup: %s', soup)

	# 모바일/웹 공통으로 핵심 콘텐츠가 들어 있는 영역만 추출 (예: id="main" 또는 class="content")
	main_section = soup.find('div', {'id': 'main'}) or soup.find('div', {'class': 'content'})
	if not main_section:
		main_section = soup  # fallback to full soup
	# debug('main section: %s', main_section)

	# 텍스트만 정제 추출
	text_maker = html2text.HTML2Text()
	text_maker.ignore_links = True
	text_maker.body_width = 0  # 줄 바꿈 방지
	plain_text = text_maker.handle(str(main_section))

	# 불필요한 공백 제거
	lines = [line.strip() for line in plain_text.splitlines() if line.strip()]

	# 핵심 정보만 추려냄 (예: 점검 시간, 서비스 재개 시점)
	important_lines = [line for line in lines if any(keyword in line for keyword in ['점검', '서비스', '중단', '복구', '재개', '공지'])]

	return '\n'.join(important_lines[:5])  # 상위 몇 줄만 반환




# 접근토큰 발급
def fn_au10001(data:dict = None) -> dict:
	# returns python dict-like object.

	dotenv.load_dotenv()
	KIWOOM_API_APPKEY = os.getenv("KIWOOM_API_APPKEY")
	KIWOOM_API_SECRET = os.getenv("KIWOOM_API_SECRET")
	if not (KIWOOM_API_APPKEY and KIWOOM_API_SECRET):
		error('no api appkey or secret!')
		raise ConfigError('no api appkey or secret!')
		# return None

	# 1. 요청할 API URL
	host = KIWOOM_API_HOST
	endpoint = '/oauth2/token'
	url =  host + endpoint

	# 2. header 데이터
	headers = {
		'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
	}
	# 요청 바디 데이터
	if data is None:
		data = {
			'grant_type': 'client_credentials',  # grant_type
			'appkey': KIWOOM_API_APPKEY,  # 앱키
			'secretkey': KIWOOM_API_SECRET,  # 시크릿키
		}

	# 3. http POST 요청
	resp = requests.post(url, headers=headers, json=data)

	# 4. 응답 상태 코드와 데이터 출력
	debug('Code: %d', resp.status_code)
	debug('Header: %s', resp.headers)

	content_type = resp.headers.get('Content-Type', '')
	if 'application/json' in content_type:
		# 'Content-Type': 'application/json;charset=UTF-8',
		debug('Body: %s', resp.json())
		json.dumps(resp.json(), indent=4, ensure_ascii=False)

	elif 'text/html' in content_type:
		# 'Content-Type': 'text/html',

		# 시스템 점검과 같은 메시지일 가능성이 매우 크다.
		debug('apparent_encoding: %s', resp.apparent_encoding)
		resp.encoding = resp.apparent_encoding
		# print(resp.text)
		msgs = ExtractMessageFromHtml(resp.text)
		debug('server messages: %s', msgs)
		# return {}
		raise ApiMaintenanceException(msgs)

	else:
		raise ApiMaintenanceException(f'unknown reason')

	if resp.status_code != 200:
		error("status code %d", 200)
		raise AuthenticationError(f'wrong status_code {resp.status_code}')

	return resp.json()


# 접근토큰폐기
def fn_au10002(token:str) -> dict:
	'''
	'''
	KIWOOM_API_APPKEY = os.getenv("KIWOOM_API_APPKEY")
	if not KIWOOM_API_APPKEY:
		dotenv.load_dotenv()
		KIWOOM_API_APPKEY = os.getenv("KIWOOM_API_APPKEY")

	KIWOOM_API_SECRET = os.getenv("KIWOOM_API_SECRET")
	if not (KIWOOM_API_APPKEY and KIWOOM_API_SECRET):
		error('no api appkey or secret!')
		raise ConfigError('no api appkey or secret!')
		# return None

	host = KIWOOM_API_HOST
	endpoint = '/oauth2/revoke'
	url =  host + endpoint

	headers = {
		'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
	}
	data = {
		'appkey': KIWOOM_API_APPKEY,  # 앱키
		'secretkey': KIWOOM_API_SECRET,  # 시크릿키
		'token': token,  # 토큰
	}
	resp = requests.post(url, headers=headers, json=data)

	debug('Code: %s', resp.status_code)
	debug('Header: %s', resp.headers)
	debug('Body: %s', resp.json())

	if resp.status_code != 200:
		error("status code %d", 200)
		raise AuthenticationError(f'wrong status_code {resp.status_code}')

	return resp.json()





def load_token() -> str:
	'''
	Returns: token string from stored data
		or None if no valid stored token
	'''
	token = None

	# check if file KIWOOM_TOKEN_ENV is really exist and readable
	if os.path.isfile(KIWOOM_TOKEN_ENV) and \
			os.access(KIWOOM_TOKEN_ENV, os.R_OK):
		debug('loading global env..')
		dotenv.load_dotenv(KIWOOM_TOKEN_ENV, verbose=True, override=True)

		token = os.getenv('KIWOOM_API_TOKEN')
		expire_at = os.getenv('KIWOOM_API_EXPIRE_AT')
		if token:
			debug('token: %s.., expire:%s', token[:8], expire_at)

	if token is None or expire_at is None:
		info('no stored token info')
		return None

	import time
	now = time.strftime('%Y%m%d%H%M%S')
	if expire_at < now:
		info('stored token expired at %s', expire_at)
		return None

	debug('valid stored token exist')
	return token

def remove_token_cache() -> bool:
	'''
	Returns
		- True if cache is removed.
		- False if no cache file exist.
	'''
	if not os.path.isfile(KIWOOM_TOKEN_ENV):
		debug('no token cache')
		return False

	info('remove stored token data..')

	# env_tmp = KIWOOM_TOKEN_ENV + '.tmp'
	# with open(KIWOOM_TOKEN_ENV, "r") as fr:
	# 	with open(env_tmp, "w") as fw:
	# 		lines = fr.readlines()
	# 		for line in lines:
	# 			fw.write(line.replace('KIWOOM_API_', '# KIWOOM_API_'))
	# import shutil
	# shutil.move(env_tmp, KIWOOM_TOKEN_ENV)

	# 현재는 이 토큰 저장 파일에는 토큰 외에는 저장되는 데이터가 없으니, 그냥 삭제해도 된다.
	os.remove(KIWOOM_TOKEN_ENV)
	return True


# export
def GetToken(force_query = False) -> str:
	'''
	Query token and stores them in global env file.

	Args:
		force_query: if True, request token again regardless stored token
		data: optional request data.

	Returns:
		token string, or None if something wrong.

	Raises:
		ConfigError:
		AuthenticationError:

	'''

	if not force_query:
		token = load_token()
		if token:
			return token

	jr = fn_au10001() # python dict-like object

	tt = jr.get('token_type')
	if  not tt or tt != 'Bearer':
		error("wrong token_type: %s", tt)
		raise AuthenticationError(f'wrong token_type {tt}')
		# return None

	with open(KIWOOM_TOKEN_ENV, "w") as f:
		f.write(f'KIWOOM_API_TOKEN = {jr.get('token')}\n')
		f.write(f'KIWOOM_API_EXPIRE_AT = {jr.get('expires_dt')}\n')
		debug('token saved.')

	with open(KIWOOM_TOKEN_ENV, "r") as f:
		debug('verify:')
		for line in f:
			debug('%s', line.rstrip())

	return jr.get('token')



def RevokeToken() -> bool:
	'''
	Revoke token which is previously aquired.
	Do nothing if no valid previous token exist.

	Returns:
		True if token is successfully revoked.
		False if no valid token

	Raises:
		ConfigError:
		AuthenticationError:

	'''
	token = load_token()
	if not token:
		debug('no valid token exist')
		return False

	jr = fn_au10002(token=token)

	remove_token_cache()

	# successfully revoked and cleaned.
	return True




# 실행 구간
if __name__ == '__main__':
	from utils_log import LogInit
	LogInit()

	import sys
	try:
		if len(sys.argv) >= 2 and sys.argv[1] == 'revoke':
			if RevokeToken():
				info('token revoked')
			else:
				info('no valid token')
		else:
			token = GetToken()
			info('token: %s', token)

	except Exception as e:
		error('%s %s', e.__class__, e)
		raise e




'''
Code: 200
Header: {
    "next-key": null,
    "cont-yn": null,
    "api-id": null
}
Body: {
    "expires_dt": "20250504211039",
    "return_msg": "정상적으로 처리되었습니다",
    "token_type": "Bearer",
    "return_code": 0,
    "token": "<token-data>"
}
'''


