'''
query_chart_tick.py

틱 차트 정보 조회

'''


import requests
import json
import time
from imports import *
from query_chart_base import RequestTickChart, IsValidDtm



#export
def GetTickChart(stk_cd:str, tic_scope:str='30', **kwargs) -> list[dict]:
	'''
	Get tick chart (candle stick?)
	Args:
		- stock_code: 종목 코드. 문자열
		- tic_scope: 틱 범위.

	Returns:
		- 지정한 날짜를 기준으로 과거의 지정 종목의 틱 차트 정보를 리턴.
		- list of python dictionary
		- 날짜 역순으로 정렬되어 있을 것으로 가정함.

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

	ticks = kwargs.get('ticks', 0)
	ticks = int(ticks) if isinstance(ticks, str) else ticks

	if ticks > 0 and to_time:
		# ticks 또는 to_time 둘 중 하나만 있어야 함.
		warning("both 'to_time' and 'ticks' args exist. to_time will be ignored.")
		to_time = None

	# # remove our-own kwargs keys to reuse it.
	kwargs.pop('to_time') if 'to_time' in kwargs else None
	kwargs.pop('ticks') if 'ticks' in kwargs else None

	# 최초 요청 시 디폴트 kwargs
	kwargs.pop('next-key') if 'next-key' in kwargs else None

	# 수정주가구분 옵션은 기본적으로 비활성화 되어 있는데, 원하는 경우 켤 수 있음.
	# kwargs['upd_stkpc_tp'] = '0'

	merged_chart = []
	req_ticks = ticks # requested_ticks

	for cnt in range(100):
		# safety limit. 900 x 100 = 90000

		debug("(%d) stk_cd: %s, tic_scope: %s, num merged %d", cnt, stk_cd, tic_scope, len(merged_chart))

		jr = RequestTickChart(token, stk_cd, tic_scope, **kwargs)

		if jr.get('return_code') != 0:
			error("return_code: %d: %s", jr.get('return_code'), jr.get('return_msg'))
			raise ApiError(f"API Error, {jr.get('return_code')}: {jr.get('return_msg')}")

		if jr.get('stk_cd') != stk_cd:
			error("response has wrong stock code %s", jr.get('stk_cd'))
			raise ApiError(f"API Error, wrong stock code")

		chart = jr.get('stk_tic_chart_qry')
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

		num_ticks = len(chart)
		if num_ticks == 0:
			warning("empty data?")
			break
		debug("responsed %d ticks, %s ~ %s",
			num_ticks, chart[-1].get('cntr_tm'), chart[0].get('cntr_tm'))

		if merged_chart:
			# 항상 더 과거의 데이터를 추가하는 방식이어야 함.
			# 이 정도까지 검사를 해야 하는가? 그냥 서버의 데이터를 믿으면 안되나?
			if merged_chart[-1].get('cntr_tm') < chart[0].get('cntr_tm'):
				error("response cntr_tm %s is newer than previous %s",
		  				chart[0].get('cntr_tm'), merged_chart[-1].get('cntr_tm'))
				raise ApiError("API Error, wrong time order")

		if req_ticks > 0: # 틱 수 지정한 경우
			merged_chart.extend(chart)
			merged_chart.sort(key = lambda e: e.get('cntr_tm', ''), reverse = True)
			debug("merged length %d", len(merged_chart))

			if len(merged_chart) >= req_ticks: # 필요한 수량 이상의 데이터 확보
				merged_chart[req_ticks:] = [] # days 개수만 남기고 불필요한 끝부분의 요소 제거
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
	tic_scope = '30'

	if len(sys.argv) >= 2:
		stock_code = sys.argv[1]

	if len(sys.argv) >= 3:
		tic_scope = sys.argv[2]

	kwargs = {}
	if len(sys.argv) >= 4:
		if '=' in sys.argv[3]:
			vs = sys.argv[3].split('=')
			if len(vs) == 2:
				kwargs[vs[0]] = vs[1]
	info('kwargs: %s', kwargs)

	try:
		chart = GetTickChart(stock_code, tic_scope, **kwargs)
		info('total %d tick chart', len(chart))

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


tic_scope 별 1회 응답
30: merged chart: len 900, 20250507134637 ~ 20250507151955
10: merged chart: len 900, 20250507144947 ~ 20250507151959  약 33분
 5: merged chart: len 900, 20250507150437 ~ 20250507151959  약 15분
 3: merged chart: len 900, 20250507151129 ~ 20250507153011
 1: merged chart: len 900, 20250507151754 ~ 20250507153011

response 로그 예시



'''
