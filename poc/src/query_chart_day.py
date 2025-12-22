'''
query_chart_day.py

일봉 차트 정보 조회

'''


import requests
import json
import time
from imports import *
from query_chart_base import RequestDailyChart, IsValidDt



#export
def GetDayPoleChart(stk_cd:str, base_dt:str='', **kwargs) -> list[dict]:
	'''
	Get daily pole chart (candle stick?)
	Args:
		- stock_code: 종목 코드. 문자열
		- base_dt: 기준 날짜 (YYYYMMDD)

	Returns:
		- 지정한 날짜를 기준으로 과거의 지정 종목의 일봉 차트 정보를 리턴.
		- list of python dictionary
		- 날짜 역순으로 정렬되어 있을 것으로 가정함.

	Example:
		- chart = GetDayPoleChart('005930') # 가장 최근 자료.
		- chart = GetDayPoleChart('005930', '20250502') # 5월2일 부터 과거 자료.
		- chart = GetDayPoleChart('005930', '20250502', to_date='20250101') # 5월2일 부터 1월1일 까지의 자료
		- chart = GetDayPoleChart('005930', '20250502', days=1000) # 5월2일 부터 1000일 분량의 자료

		구간이 명확하지 않은 경우에는 서버에서 전달 받은 기본 분량의 자료를 그대로 리턴. 현재 600 일 분량.

	Raises:
		ConfigError:
		AuthenticationError:
		ApiError:

	'''
	token = GetToken() # 접근토큰
	debug("using token %s..", token[:5])

	stk_cd = stk_cd or '005930' # default: 삼성전자 (KRX 거래소)
	base_dt = base_dt or time.strftime('%Y%m%d') # default: today

	to_date = kwargs.get('to_date', None)
	if to_date:
		if not IsValidDt(to_date):
			warning("invalid to_date '%s'! it will be ignored!", to_date)
			to_date = None

		if base_dt < to_date:
			warning("to_date is future than base_dt! it will be ignored!")
			to_date = None

	days = kwargs.get('days', 0)
	days = int(days) if isinstance(days, str) else days

	if days > 0 and to_date:
		# days 또는 to_date 둘 중 하나만 있어야 함.
		warning("both 'to_date' and 'days' args exist. to_date will be ignored.")
		to_date = None

	# remove our-own kwargs keys to reuse it.
	kwargs.pop('to_date') if 'to_date' in kwargs else None
	kwargs.pop('days') if 'days' in kwargs else None

	# 최초 요청 시 디폴트 kwargs
	kwargs.pop('next-key') if 'next-key' in kwargs else None

	# 수정주가구분 옵션은 기본적으로 비활성화 되어 있는데, 원하는 경우 켤 수 있음.
	# kwargs['upd_stkpc_tp'] = '0'

	merged_chart = []

	# 필요한 만큼의 데이터가 모아질 때 까지 반복.
	# 알수 없는 버그 등에 의한 무한 루프를 방지하기 위해
	# 횟수를 적정 수준으로 제한. 정상적인 경우라면 대략 1만개 정도 데이터 확보할 횟수임.
	# 10000//600 ~= 18
	for cnt in range(18):
		debug("(%d) stk_cd: %s, base_dt: %s, num merged %d", cnt, stk_cd, base_dt, len(merged_chart))

		jr = RequestDailyChart(token, stk_cd, base_dt, **kwargs)

		'''
		보통 api 통신이 성공한 경우 다음과 같이 응답된다.
			"return_code": 0,
			"return_msg": "조회가 완료되었습니다"
			... # 그 외 다른 정보들..
		'''
		if jr.get('return_code') != 0:
			error("return_code: %d: %s", jr.get('return_code'), jr.get('return_msg'))
			raise ApiError(f"API Error, {jr.get('return_code')}: {jr.get('return_msg')}")

		# 너무 데이터가 크기 때문에, 이걸 로깅하지는 않는다.
		# debug("resp:\n%s", json.dumps(jr, indent=2, ensure_ascii=False))

		'''
		api 에러의 예시:
			'return_msg': '인증에 실패했습니다[8005:Token이 유효하지 않습니다]', 'return_code': 3
			...
		'''
		if jr.get('stk_cd') != stk_cd:
			error("response has wrong stock code %s", jr.get('stk_cd'))
			raise ApiError(f"API Error, wrong stock code")

		chart = jr.get('stk_dt_pole_chart_qry')
		if not isinstance(chart, list):
			raise ApiError(f"API Error, wrong chart list")

		# sanity check
		# 리스트의 모든 요소에는 최소한 유효한 'dt' 키 값이 존재해야 함.
		for i,e in enumerate(chart):
			if not IsValidDt(e.get('dt')):
				error("chart[%d] has wrong dt field", i, e.get('dt'))
				raise ApiError("API Error, wrong chart element")

		# reverse sort
		chart.sort(key = lambda e: e.get('dt', ''), reverse = True)
		# 내부에도 중복 데이터는 없어야 하는데, 그 부분까지의 검사는 skip 하도록 한다.

		num_days = len(chart)
		debug("responsed %d days, %s ~ %s",
			num_days, chart[-1].get('dt'), chart[0].get('dt'))

		if merged_chart:
			# 항상 더 과거의 데이터를 추가하는 방식이어야 함.
			# 이 정도까지 검사를 해야 하는가? 그냥 서버의 데이터를 믿으면 안되나?
			if merged_chart[-1].get('dt') < chart[0].get('dt'):
				error("response dt %s is newer than previous %s",
		  				chart[0].get('dt'), merged_chart[-1].get('dt'))
				raise ApiError("API Error, wrong date order")

		if days > 0: # 날짜 수 지정한 경우
			merged_chart.extend(chart)
			merged_chart.sort(key = lambda e: e.get('dt', ''), reverse = True)
			debug("merged length %d", len(merged_chart))

			if len(merged_chart) >= days: # 필요한 수량 이상의 데이터 확보
				merged_chart[days:] = [] # days 개수만 남기고 불필요한 끝부분의 요소 제거
				debug("shrinked to length %d", len(merged_chart))
				break
			# 아직 충분히 채워지지 않으면 계속 반복 요청

		elif to_date: # 종료 날짜 지정한 경우
			reached_to_date = False
			# oldest_dt = merged_chart[-1].get('dt')

			for i,e in enumerate(chart):
				if to_date > e.get('dt'):
					debug("trim [%d] dt %s element and after", i, e.get('dt'))
					chart[i:] = [] # i번째 이후는 모두 제거
					reached_to_date = True
					break
			if chart[-1].get('dt') == to_date:
				debug("last element is from %s", to_date)
				reached_to_date = True

			merged_chart.extend(chart)
			merged_chart.sort(key = lambda e: e.get('dt', ''), reverse = True)
			debug("merged length %d", len(merged_chart))

			if reached_to_date:
				break
			# 아직 충분히 채워지지 않으면 계속 반복 요청

		else:
			# 1회 query 로 충분.
			merged_chart.extend(chart)
			break

		# repeat again
		kwargs['next_key'] = jr.get('next_key')

	debug('final merged chart: len %d, %s ~ %s', len(merged_chart),
	   			merged_chart[-1].get('dt'), merged_chart[0].get('dt'))

	return merged_chart



# 단위 시험
if __name__ == '__main__':
	from utils_log import LogInit
	LogInit()

	stock_code = '005930'
	base_date = '' # 비어 있는 경우, 오늘 날짜

	if len(sys.argv) >= 2:
		stock_code = sys.argv[1]

	if len(sys.argv) >= 3:
		base_date = sys.argv[2]

	kwargs = {}
	if len(sys.argv) >= 4:
		if '=' in sys.argv[3]:
			vs = sys.argv[3].split('=')
			if len(vs) == 2:
				kwargs[vs[0]] = vs[1]
	info('kwargs: %s', kwargs)

	try:
		chart = GetDayPoleChart(stock_code, base_date, **kwargs)
		info('total %d days chart', len(chart))

		if chart:
			debug("latest:\n%s",
				json.dumps(chart[0], indent=2, ensure_ascii=False))
		if chart and len(chart) >= 2:
			debug("oldest:\n%s",
				json.dumps(chart[-1], indent=2, ensure_ascii=False))

	except Exception as e:
		error("%s %s", e.__class__, e)
		raise

'''
응답 해석:
Element	한글명	type	Required	Length	Description
stk_cd	종목코드	String	N	6
stk_dt_pole_chart_qry	주식일봉차트조회	LIST	N
- cur_prc	현재가	String	N	20   # 인터넷에 오픈 된 데이터로 교차 확인해 확인해 보면 이 값이 "종가" 이다.
- trde_qty	거래량	String	N	20
- trde_prica	거래대금	String	N	20
- dt	일자	String	N	20
- open_pric	시가	String	N	20
- high_pric	고가	String	N	20
- low_pric	저가	String	N	20
- upd_stkpc_tp	수정주가구분	String	N	20	1:유상증자, 2:무상증자, 4:배당락, 8:액면분할, 16:액면병합, 32:기업합병, 64:감자, 256:권리락
- upd_rt	수정비율	String	N	20
- bic_inds_tp	대업종구분	String	N	20
- sm_inds_tp	소업종구분	String	N	20
- stk_infr	종목정보	String	N	20
- upd_stkpc_event	수정주가이벤트	String	N	20
- pred_close_pric	전일종가	String	N	20


response 로그 예시

23:46:24 D query_chart_day fn_ka10081: Code: 200
23:46:24 D query_chart_day fn_ka10081: Header: {... 'next-key': 'A0059302022111700010000', 'resp-cnt': '600', 'cont-yn': 'Y', 'user-data': '', 'api-id': 'ka10081'}
23:46:24 D query_chart_day GetDayPoleChart: responsed total 600 days, 20221118 ~ 20250502
23:46:24 D query_chart_day <module>: latest:
{
  "cur_prc": "54300",
  "trde_qty": "22454204",
  "trde_prica": "1227727",
  "dt": "20250502",
  "open_pric": "55000",
  "high_pric": "55500",
  "low_pric": "54200",
  "upd_stkpc_tp": "",
  "upd_rt": "",
  "bic_inds_tp": "",
  "sm_inds_tp": "",
  "stk_infr": "",
  "upd_stkpc_event": "",
  "pred_close_pric": ""
}
23:46:24 D query_chart_day <module>: oldest:
{
  "cur_prc": "61800",
  "trde_qty": "12236503",
  "trde_prica": "757455",
  "dt": "20221118",
  "open_pric": "61800",
  "high_pric": "62400",
  "low_pric": "61400",
  "upd_stkpc_tp": "",
  "upd_rt": "",
  "bic_inds_tp": "",
  "sm_inds_tp": "",
  "stk_infr": "",
  "upd_stkpc_event": "",
  "pred_close_pric": ""
}
'''
