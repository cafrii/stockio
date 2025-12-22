'''
query_chart_minute.py

분봉 차트 정보 조회

'''


import requests
import json
import time
from imports import *
from query_chart_base import RequestMinuteChart, IsValidDtm



#export
def GetMinuteChart(stk_cd:str, min_scope:str='1', **kwargs) -> list[dict]:
	'''
	Get tick chart (candle stick?)
	Args:
		- stock_code: (str) 종목 코드
		- min_scope: (str) 분 단위. (1, 3, 5, 10, 15, 30, 45, 60 분 중 하나)

	Returns:
		- 지정한 날짜를 기준으로 과거의 지정 종목의 틱 차트 정보를 리턴.
		- list of python dictionary
		- 시간 역순으로 정렬되어 있을 것으로 가정함.

	Example:

	Raises:
		ConfigError:
		AuthenticationError:
		ApiError:

	'''
	token = GetToken() # 접근토큰
	debug("using token %s..", token[:5])

	stk_cd = stk_cd or '005930' # default: 삼성전자 (KRX 거래소)
	to_time = kwargs.get('to_time', None)

	if to_time:
		if not IsValidDtm(to_time):
			warning("invalid to_time '%s'! it will be ignored!", to_time)
			to_time = None

	num_items = kwargs.get('items', 0)
	num_items = int(num_items) if isinstance(num_items, str) else num_items

	if num_items > 0 and to_time:
		# items 또는 to_time 둘 중 하나만 있어야 함.
		warning("both 'to_time' and 'items' args exist. to_time will be ignored.")
		to_time = None

	# # remove our-own kwargs keys to reuse it.
	kwargs.pop('to_time') if 'to_time' in kwargs else None
	kwargs.pop('items') if 'items' in kwargs else None

	# 최초 요청 시 디폴트 kwargs
	kwargs.pop('next-key') if 'next-key' in kwargs else None

	# 수정주가구분 옵션은 기본적으로 비활성화 되어 있는데, 원하는 경우 켤 수 있음.
	# kwargs['upd_stkpc_tp'] = '0'

	merged_chart = []
	req_items = num_items # requested_items

	for cnt in range(100):
		# safety limit. 900 x 100 = 90000, 60년 이상 분량임.

		debug("(%d) stk_cd: %s, min_scope: %s, num merged %d", cnt, stk_cd, min_scope, len(merged_chart))

		jr = RequestMinuteChart(token, stk_cd, min_scope, **kwargs)

		if jr.get('return_code') != 0:
			error("return_code: %d: %s", jr.get('return_code'), jr.get('return_msg'))
			raise ApiError(f"API Error, {jr.get('return_code')}: {jr.get('return_msg')}")

		if jr.get('stk_cd') != stk_cd:
			error("response has wrong stock code %s", jr.get('stk_cd'))
			raise ApiError(f"API Error, wrong stock code")

		chart = jr.get('stk_min_pole_chart_qry')
		if not isinstance(chart, list):
			raise ApiError(f"API Error, wrong chart list")

		# sanity check
		# 리스트의 모든 요소에는 최소한 유효한 'cntr_tm' (체결시간) 키 값이 존재해야 함.
		for i,e in enumerate(chart):
			if not IsValidDtm(e.get('cntr_tm')):
				error("chart[%d] has wrong cntr_tm field", i, e.get('cntr_tm'))
				raise ApiError("API Error, wrong chart element")

		# reverse sort
		chart.sort(key = lambda e: e.get('cntr_tm', ''), reverse = True)

		num_items = len(chart)
		if num_items == 0:
			warning("empty items?")
			break
		debug("responsed %d items, %s ~ %s",
			num_items, chart[-1].get('cntr_tm'), chart[0].get('cntr_tm'))

		if merged_chart:
			if merged_chart[-1].get('cntr_tm') < chart[0].get('cntr_tm'):
				error("response cntr_tm %s is newer than previous %s",
		  				chart[0].get('cntr_tm'), merged_chart[-1].get('cntr_tm'))
				raise ApiError("API Error, wrong time order")

		if req_items > 0: # 항목 수 지정한 경우
			merged_chart.extend(chart)
			merged_chart.sort(key = lambda e: e.get('cntr_tm', ''), reverse = True)
			debug("merged length %d", len(merged_chart))

			if len(merged_chart) >= req_items: # 필요한 수량 이상의 데이터 확보
				merged_chart[req_items:] = [] # days 개수만 남기고 불필요한 끝부분의 요소 제거
				debug("shrinked to length %d", len(merged_chart))
				break
			# 아직 충분히 채워지지 않으면 계속 반복 요청

		elif to_time: # 종료 시간 지정한 경우
			reached_to_time = False

			for i,e in enumerate(chart):
				if to_time > e.get('cntr_tm'):
					debug("trim [%d] cntr_tm %s element and after", i, e.get('cntr_tm'))
					chart[i:] = [] # i번째 이후는 모두 제거
					reached_to_time = True
					break
			if chart[-1].get('cntr_tm') == to_time:
				debug("last element is from %s", to_time)
				reached_to_time = True

			merged_chart.extend(chart)
			merged_chart.sort(key = lambda e: e.get('cntr_tm', ''), reverse = True)
			debug("merged length %d", len(merged_chart))

			if reached_to_time:
				break
			# 아직 충분히 채워지지 않으면 계속 반복 요청

		else:
			# 1회 query 로 충분.
			debug("one-time query")
			merged_chart.extend(chart)
			break

		# repeat again
		kwargs['next_key'] = jr.get('next_key')

	debug('final merged chart: len %d, %s ~ %s', len(merged_chart),
	   			merged_chart[-1].get('cntr_tm'), merged_chart[0].get('cntr_tm'))

	return merged_chart



# 단위 시험
if __name__ == '__main__':
	from utils_log import LogInit
	LogInit()

	stock_code = '005930'
	min_scope = '1'

	if len(sys.argv) >= 2:
		stock_code = sys.argv[1]

	if len(sys.argv) >= 3:
		min_scope = sys.argv[2]

	kwargs = {}
	if len(sys.argv) >= 4:
		if '=' in sys.argv[3]:
			vs = sys.argv[3].split('=')
			if len(vs) == 2:
				kwargs[vs[0]] = vs[1]
	info('kwargs: %s', kwargs)

	try:
		chart = GetMinuteChart(stock_code, min_scope, **kwargs)
		info('total %d items', len(chart))

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
last_tic_cnt	마지막틱갯수	String	N
stk_tic_chart_qry	주식틱차트조회	LIST	N
- cur_prc	현재가	String	N	20
- trde_qty	거래량	String	N	20
- cntr_tm	체결시간	String	N	20
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

...
00:19:13 D query_chart_minute GetMinuteChart: (1) stk_cd: 005930, min_scope: 1, num merged 900
00:19:13 D query_chart_base RequestChartData: ---- request: header
{'Content-Type': 'application/json;charset=UTF-8', 'authorization': 'Bearer <token>', 'cont-yn': 'Y', 'next-key': 'A0059302..', 'api-id': 'ka10080'}
00:19:13 D urllib3.connectionpool _new_conn: Starting new HTTPS connection (1): api.kiwoom.com:443
00:19:13 D urllib3.connectionpool _make_request: https://api.kiwoom.com:443 "POST /api/dostk/chart HTTP/1.1" 200 None

00:19:13 D query_chart_base RequestChartData: ---- response
00:19:13 D query_chart_base RequestChartData: Code: 200
00:19:13 D query_chart_base RequestChartData: Header: {'Date': 'Wed, 07 May 2025 15:19:13 GMT', 'Content-Type': 'application/json;charset=UTF-8', 'Transfer-Encoding': 'chunked', 'Connection': 'keep-alive', 'next-key': 'A0059302025042810480000010000', 'Access-Control-Expose-Headers': 'api-id,cont-yn,next-key,resp-cnt,user-data', 'resp-cnt': '900', 'Access-Control-Allow-Origin': '*', 'cont-yn': 'Y', 'user-data': '', 'Vary': 'Origin, Access-Control-Request-Method, Access-Control-Request-Headers', 'api-id': 'ka10080'}
00:19:13 D query_chart_base RequestChartData: there are more data
00:19:13 D query_chart_minute GetMinuteChart: responsed 900 items, 20250428104900 ~ 20250430130400
00:19:13 D query_chart_minute GetMinuteChart: merged length 1800
00:19:13 D query_chart_minute GetMinuteChart: shrinked to length 1000
00:19:13 D query_chart_minute GetMinuteChart: final merged chart: len 1000, 20250430112500 ~ 20250507153000
00:19:13 I query_chart_minute <module>: total 1000 items
00:19:13 D query_chart_minute <module>: latest:
{
  "cur_prc": "+54600",
  "trde_qty": "2587959",
  "cntr_tm": "20250507153000",
  "open_pric": "+54600",
  "high_pric": "+54600",
  "low_pric": "+54600",
  "upd_stkpc_tp": "",
  "upd_rt": "",
  "bic_inds_tp": "",
  "sm_inds_tp": "",
  "stk_infr": "",
  "upd_stkpc_event": "",
  "pred_close_pric": ""
}
00:19:13 D query_chart_minute <module>: oldest:
{
  "cur_prc": "-55500",
  "trde_qty": "7692",
  "cntr_tm": "20250430112500",
  "open_pric": "-55550",
  "high_pric": "-55600",
  "low_pric": "-55500",
  "upd_stkpc_tp": "",
  "upd_rt": "",
  "bic_inds_tp": "",
  "sm_inds_tp": "",
  "stk_infr": "",
  "upd_stkpc_event": "",
  "pred_close_pric": ""
}

'''
