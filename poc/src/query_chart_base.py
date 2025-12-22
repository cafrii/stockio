'''
query_chart_base.py

차트 정보 요청 api

'''


import requests
import json
import time
from imports import *


# export
def RequestChartData(token:str, api_id:str, stk_cd:str=None, **kwargs):
	'''
	주식 (틱/분봉/일봉/주봉/월봉/연봉) 차트조회요청
	지정한 날짜/시간 으로부터 과거의 데이터 조회
	한번 요청 시 ?회 분량의 데이터가 전달됨.

	Args:
	- token: (str) 접근 토큰
	- api_id: (str)
		ka10079: 틱
		ka10080: 분봉
		ka10081: 일봉
		ka10082: 주봉
		ka10083: 월봉
		ka10094: 연봉
	- stk_cd: (str) stock code. 종목코드. 필수 인자.
	- kwargs:
		tic_scope: (str) 1:1틱, 3:3틱, 5:5틱, 10:10틱, 30:30틱
		min_scope: (str) 1, 3, 5, 10, 15, 30, 45, 60 분
		base_dt: (str) base date. 기준일자, 'YYYYMMDD'. 필수 인자
		upd_stkpc_tp: (str) 수정주가구분 타입. 0 또는 1. default '1'
		next_key: (str) 연속조회용 키. default ''

	Returns:
		dictionary 객체 (response body 내용에 일부 수정 적용)

	Raises:
		ApiError
		ArgumentError
	'''

	upd_stkpc_tp = kwargs.get('upd_stkpc_tp', '1')
	next_key = kwargs.get('next_key', '')
	cont_yn = 'Y' if next_key else 'N'
	tic_scope = kwargs.get('tic_scope', '')
	min_scope = kwargs.get('min_scope', '')
	base_dt = kwargs.get('base_dt', '')

	host = KIWOOM_API_HOST
	endpoint = '/api/dostk/chart'
	url =  host + endpoint

	headers = {
		'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
		# 'authorization': f'Bearer {token}', # 접근토큰
		'cont-yn': cont_yn, # 연속조회여부
		'next-key': next_key, # 연속조회키
		'api-id': api_id, # TR명
	}
	data = {
		'stk_cd':  stk_cd,  # 종목코드 거래소별 종목코드 (KRX:039490,NXT:039490_NX,SOR:039490_AL)
		'upd_stkpc_tp': upd_stkpc_tp, # 수정주가구분 '0' or '1'
	}

	if api_id == 'ka10079': # 틱
		if tic_scope not in ['1', '3', '5', '10', '30']:
			raise ArgumentError(f'tic_scope {tic_scope} invalid')
		data['tic_scope'] = tic_scope

	elif api_id == 'ka10080': # 분봉
		if min_scope not in ['1', '3', '5', '10', '15', '30', '45', '60']:
			raise ArgumentError(f'min_scope {min_scope} invalid')
		data['tic_scope'] = min_scope
		# 1:1분, 3:3분, 5:5분, 10:10분, 15:15분, 30:30분, 45:45분, 60:60분
		# 주의: api 문서에는 여전히 키 이름이 'tic_scope' 이므로 주의!
	else:
		data['base_dt'] = base_dt # 기준일자 YYYYMMDD

	if cont_yn == 'Y' or len(next_key) > 0:
		debug('---- request: header\n%s', headers)

	# 주의: 헤더 내부의 token 정보가 로그 메시지로 표시되는 문제점들이 발생함.
	#      그래서 민감정보는 post() 요청 바로 직전에 추가. 로깅을 허용하지 않도록 함.
	#
	headers['authorization'] = f'Bearer {token}' # 접근토큰
	resp = requests.post(url, headers=headers, json=data)

	debug('---- response')
	debug('Code: %s', resp.status_code)
	debug('Header: %s', resp.headers)

	if resp.status_code != 200:
		error("wrong status_code %d", resp.status_code)
		raise ApiError(f"API Error, wrong status_code {resp.status_code}")

	rh = resp.headers
	next_key = None
	if rh.get('cont-yn') == 'Y' and rh.get('next-key'):
		debug('there are more data')
		next_key = rh.get('next-key')

	# debug('Body: %s', resp.json())
	jr = resp.json()

	if next_key: # 연속 조회 여부는 이 dict 객체에 담아서 전달하도록 한다.
		jr['next_key'] = next_key
	return jr



def RequestTickChart(token, stk_cd, tic_scope, **kwargs):
	return RequestChartData(token, 'ka10079', stk_cd, tic_scope=tic_scope, **kwargs)

def RequestMinuteChart(token, stk_cd, min_scope, **kwargs):
	return RequestChartData(token, 'ka10080', stk_cd, min_scope=min_scope, **kwargs)

def RequestDailyChart(token, stk_cd, base_dt, **kwargs):
	return RequestChartData(token, 'ka10081', stk_cd, base_dt=base_dt, **kwargs)

def RequestWeeklyChart(token, stk_cd, base_dt, **kwargs):
	return RequestChartData(token, 'ka10082', stk_cd, base_dt=base_dt, **kwargs)

def RequestMonthlyChart(token, stk_cd, base_dt, **kwargs):
	return RequestChartData(token, 'ka10083', stk_cd, base_dt=base_dt, **kwargs)

def RequestYearlyChart(token, stk_cd, base_dt, **kwargs):
	return RequestChartData(token, 'ka10094', stk_cd, base_dt=base_dt, **kwargs)


#export
def IsValidDt(dt:str) -> bool:
	# YYYYmmdd
	return ( isinstance(dt, str) and
			len(dt) == 8 and
			1900 <= int(dt[:4]) and # year
			1 <= int(dt[4:6]) <= 12 and # month
			1 <= int(dt[6:]) <= 31 ) # day

def IsValidDtm(dt:str) -> bool:
	# YYYYmmddHHMMSS
	return ( isinstance(dt, str) and
			len(dt) == 14 and
			1900 <= int(dt[:4]) and # year
			1 <= int(dt[4:6]) <= 12 and # month
			1 <= int(dt[6:8]) <= 31 and # day
			0 <= int(dt[8:10]) <= 23 and # hour
			0 <= int(dt[10:12]) <= 59 and # minute
			0 <= int(dt[12:14]) <= 61 ) # second


