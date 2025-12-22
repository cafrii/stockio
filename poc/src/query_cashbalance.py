'''
query_cashbalance.py

예수금 정보 조회

'''


import requests
import json
from imports import *



# 예수금상세현황요청
def fn_kt00001(token, data=None, **kwargs):
	'''
	예수금상세현황요청

	Args:
		token:
		data: json-serializable python object
		kwargs:
			cont_yn: default 'N'
			next_key: default ''
	'''
	cont_yn = kwargs.get('cont_yn', 'N')
	next_key = kwargs.get('next_key', '')

	host = KIWOOM_API_HOST
	endpoint = '/api/dostk/acnt'
	url =  host + endpoint

	headers = {
		'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
		'authorization': f'Bearer {token}', # 접근토큰
		'cont-yn': cont_yn, # 연속조회여부
		'next-key': next_key, # 연속조회키
		'api-id': 'kt00001', # TR명
	}
	if data is None:
		data = {
			'qry_tp': '3', # 조회구분 3:추정조회, 2:일반조회
		}
	resp = requests.post(url, headers=headers, json=data)

	debug('Code: %s', resp.status_code)
	debug('Header: %s', resp.headers)
	debug('Body: %s', resp.json())

	if resp.status_code != 200:
		error("wrong status_code %d", resp.status_code)
		raise ApiError(f"API Error, wrong status_code {resp.status_code}")

	# next-key, cont-yn 값이 있을 경우, 연속해서 계속 출력해야 하는 모양인데..
	# fn_kt00001(token=token, data=params, cont_yn='Y', next_key='nextkey..')

	return resp.json()


#export
def GetCashBalance() -> int:
	'''
	Returns:
		cash balance as int

	Raises:
		ConfigError:
		AuthenticationError:

	'''
	token = GetToken() # 접근토큰
	debug("using token %s..", token[:5])

	jr = fn_kt00001(token=token)
	'''
	보통 api 통신이 성공한 경우 다음과 같이 응답된다.
		"return_code": 0,
		"return_msg": "조회가 완료되었습니다"
		... # 그 외 다른 정보들..
	'''
	if jr.get('return_code') != 0:
		error("return_code: %d: %s", jr.get('return_code'), jr.get('return_msg'))
		raise ApiError(f"API Error, {jr.get('return_code')}: {jr.get('return_msg')}")

	debug("resp:\n%s", json.dumps(jr, indent=2, ensure_ascii=False))

	'''
	api 에러의 예시:
		'return_msg': '인증에 실패했습니다[8005:Token이 유효하지 않습니다]', 'return_code': 3
		...

	'''

	# 원화 예수금 잔액 정보는 entr 인 것으로 보임.
	return int(jr.get('entr', '0'))




# 실행 구간
if __name__ == '__main__':
	from utils_log import LogInit
	LogInit()

	try:
		deposit = GetCashBalance()
		print(deposit)
	except Exception as e:
		error("%s %s", e.__class__, e)





'''
Response Body
Element	한글명	type	Required	Length	Description
entr	예수금	String	N	15
profa_ch	주식증거금현금	String	N	15
bncr_profa_ch	수익증권증거금현금	String	N	15
nxdy_bncr_sell_exct	익일수익증권매도정산대금	String	N	15
fc_stk_krw_repl_set_amt	해외주식원화대용설정금	String	N	15
crd_grnta_ch	신용보증금현금	String	N	15
crd_grnt_ch	신용담보금현금	String	N	15
add_grnt_ch	추가담보금현금	String	N	15
etc_profa	기타증거금	String	N	15
uncl_stk_amt	미수확보금	String	N	15
shrts_prica	공매도대금	String	N	15
crd_set_grnta	신용설정평가금	String	N	15
chck_ina_amt	수표입금액	String	N	15
etc_chck_ina_amt	기타수표입금액	String	N	15
crd_grnt_ruse	신용담보재사용	String	N	15
knx_asset_evltv	코넥스기본예탁금	String	N	15
elwdpst_evlta	ELW예탁평가금	String	N	15
crd_ls_rght_frcs_amt	신용대주권리예정금액	String	N	15
lvlh_join_amt	생계형가입금액	String	N	15
lvlh_trns_alowa	생계형입금가능금액	String	N	15
repl_amt	대용금평가금액(합계)	String	N	15
remn_repl_evlta	잔고대용평가금액	String	N	15
trst_remn_repl_evlta	위탁대용잔고평가금액	String	N	15
bncr_remn_repl_evlta	수익증권대용평가금액	String	N	15
profa_repl	위탁증거금대용	String	N	15
crd_grnta_repl	신용보증금대용	String	N	15
crd_grnt_repl	신용담보금대용	String	N	15
add_grnt_repl	추가담보금대용	String	N	15
rght_repl_amt	권리대용금	String	N	15
pymn_alow_amt	출금가능금액	String	N	15
wrap_pymn_alow_amt	랩출금가능금액	String	N	15
ord_alow_amt	주문가능금액	String	N	15
bncr_buy_alowa	수익증권매수가능금액	String	N	15
20stk_ord_alow_amt	20%종목주문가능금액	String	N	15
30stk_ord_alow_amt	30%종목주문가능금액	String	N	15
40stk_ord_alow_amt	40%종목주문가능금액	String	N	15
100stk_ord_alow_amt	100%종목주문가능금액	String	N	15
ch_uncla	현금미수금	String	N	15
ch_uncla_dlfe	현금미수연체료	String	N	15
ch_uncla_tot	현금미수금합계	String	N	15
crd_int_npay	신용이자미납	String	N	15
int_npay_amt_dlfe	신용이자미납연체료	String	N	15
int_npay_amt_tot	신용이자미납합계	String	N	15
etc_loana	기타대여금	String	N	15
etc_loana_dlfe	기타대여금연체료	String	N	15
etc_loan_tot	기타대여금합계	String	N	15
nrpy_loan	미상환융자금	String	N	15
loan_sum	융자금합계	String	N	15
ls_sum	대주금합계	String	N	15
crd_grnt_rt	신용담보비율	String	N	15
mdstrm_usfe	중도이용료	String	N	15
min_ord_alow_yn	최소주문가능금액	String	N	15
loan_remn_evlt_amt	대출총평가금액	String	N	15
dpst_grntl_remn	예탁담보대출잔고	String	N	15
sell_grntl_remn	매도담보대출잔고	String	N	15
d1_entra	d+1추정예수금	String	N	15
d1_slby_exct_amt	d+1매도매수정산금	String	N	15
d1_buy_exct_amt	d+1매수정산금	String	N	15
d1_out_rep_mor	d+1미수변제소요금	String	N	15
d1_sel_exct_amt	d+1매도정산금	String	N	15
d1_pymn_alow_amt	d+1출금가능금액	String	N	15
d2_entra	d+2추정예수금	String	N	15
d2_slby_exct_amt	d+2매도매수정산금	String	N	15
d2_buy_exct_amt	d+2매수정산금	String	N	15
d2_out_rep_mor	d+2미수변제소요금	String	N	15
d2_sel_exct_amt	d+2매도정산금	String	N	15
d2_pymn_alow_amt	d+2출금가능금액	String	N	15
50stk_ord_alow_amt	50%종목주문가능금액	String	N	15
60stk_ord_alow_amt	60%종목주문가능금액	String	N	15
stk_entr_prst	종목별예수금	LIST	N
- crnc_cd	통화코드	String	N	3
- fx_entr	외화예수금	String	N	15
- fc_krw_repl_evlta	원화대용평가금	String	N	15
- fc_trst_profa	해외주식증거금	String	N	15
- pymn_alow_amt	출금가능금액	String	N	15
- pymn_alow_amt_entr	출금가능금액(예수금)	String	N	15
- ord_alow_amt_entr	주문가능금액(예수금)	String	N	15
- fc_uncla	외화미수(합계)	String	N	15
- fc_ch_uncla	외화현금미수금	String	N	15
- dly_amt	연체료	String	N	15
- d1_fx_entr	d+1외화예수금	String	N	15
- d2_fx_entr	d+2외화예수금	String	N	15
- d3_fx_entr	d+3외화예수금	String	N	15
- d4_fx_entr	d+4외화예수금	String	N	15



# 실행 결과 예시. response.json() 을 jsondump.
# 테스트를 위해 77원을 이 계좌에 이체한 후 실행.

{
  "entr": "000000000000077",
  "profa_ch": "000000000000000",
  "bncr_profa_ch": "000000000000000",
  "nxdy_bncr_sell_exct": "000000000000000",
  "fc_stk_krw_repl_set_amt": "000000000000000",
  "crd_grnta_ch": "000000000000000",
  "crd_grnt_ch": "000000000000000",
  "add_grnt_ch": "000000000000000",
  "etc_profa": "000000000000000",
  "uncl_stk_amt": "000000000000000",
  "shrts_prica": "000000000000000",
  "crd_set_grnta": "000000000000000",
  "chck_ina_amt": "000000000000000",
  "etc_chck_ina_amt": "000000000000000",
  "crd_grnt_ruse": "000000000000000",
  "knx_asset_evltv": "000000000000000",
  "elwdpst_evlta": "000000000000077",
  "crd_ls_rght_frcs_amt": "000000000000000",
  "lvlh_join_amt": "000000000000000",
  "lvlh_trns_alowa": "000000000000000",
  "repl_amt": "000000000000000",
  "remn_repl_evlta": "000000000000000",
  "trst_remn_repl_evlta": "000000000000000",
  "bncr_remn_repl_evlta": "000000000000000",
  "profa_repl": "000000000000000",
  "crd_grnta_repl": "000000000000000",
  "crd_grnt_repl": "000000000000000",
  "add_grnt_repl": "000000000000000",
  "rght_repl_amt": "000000000000000",
  "pymn_alow_amt": "000000000000077",
  "wrap_pymn_alow_amt": "000000000000000",
  "ord_alow_amt": "000000000000077",
  "bncr_buy_alowa": "000000000000077",
  "20stk_ord_alow_amt": "000000000000385",
  "30stk_ord_alow_amt": "000000000000256",
  "40stk_ord_alow_amt": "000000000000192",
  "100stk_ord_alow_amt": "000000000000077",
  "ch_uncla": "000000000000000",
  "ch_uncla_dlfe": "000000000000000",
  "ch_uncla_tot": "000000000000000",
  "crd_int_npay": "000000000000000",
  "int_npay_amt_dlfe": "000000000000000",
  "int_npay_amt_tot": "000000000000000",
  "etc_loana": "000000000000000",
  "etc_loana_dlfe": "000000000000000",
  "etc_loan_tot": "000000000000000",
  "nrpy_loan": "000000000000000",
  "loan_sum": "000000000000000",
  "ls_sum": "000000000000000",
  "crd_grnt_rt": "0.00",
  "mdstrm_usfe": "000000000000000",
  "min_ord_alow_yn": "000000000000000",
  "loan_remn_evlt_amt": "000000000000000",
  "dpst_grntl_remn": "000000000000000",
  "sell_grntl_remn": "000000000000000",
  "d1_entra": "000000000000077",
  "d1_slby_exct_amt": "000000000000000",
  "d1_buy_exct_amt": "000000000000000",
  "d1_out_rep_mor": "000000000000000",
  "d1_sel_exct_amt": "000000000000000",
  "d1_pymn_alow_amt": "000000000000077",
  "d2_entra": "000000000000077",
  "d2_slby_exct_amt": "000000000000000",
  "d2_buy_exct_amt": "000000000000000",
  "d2_out_rep_mor": "000000000000000",
  "d2_sel_exct_amt": "000000000000000",
  "d2_pymn_alow_amt": "000000000000077",
  "50stk_ord_alow_amt": "000000000000154",
  "60stk_ord_alow_amt": "000000000000128",
  "stk_entr_prst": [
	{
	  "crnc_cd": "USD",
	  "fx_entr": "33.00",
	  "fc_krw_repl_evlta": "0.00",
	  "fc_trst_profa": "0.00",
	  "pymn_alow_amt_entr": "",
	  "ord_alow_amt_entr": "",
	  "fc_uncla": "0.00",
	  "fc_ch_uncla": "0.00",
	  "dly_amt": "0.00",
	  "d1_fx_entr": "0.00",
	  "d2_fx_entr": "0.00",
	  "d3_fx_entr": "0.00",
	  "d4_fx_entr": "0.00"
	}
  ],
  "return_code": 0,
  "return_msg": "조회가 완료되었습니다"
}
77

'''

