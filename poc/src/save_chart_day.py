'''
작업중! 미완성!


'''


import requests
import json
import time

import pandas as pd
from datetime import datetime

from imports import *


def convert_to_dataframe(raw_data, index_key, key_to_column):
	"""
	딕셔너리 리스트를 pandas DataFrame으로 변환.

	Args:
	- raw_data: 딕셔너리 리스트
	- key_to_column:
	- required_keys: DataFrame에 포함할 키 리스트 (선택적, 기본값 None 이면 모든 키 사용)
	- def_val: 키가 누락된 경우 사용할 기본값 딕셔너리 (선택적)

	Returns:
	- pandas DataFrame
	"""
	if required_keys is None:
		# required_keys가 지정되지 않은 경우, 첫 번째 딕셔너리의 키를 기준으로 설정
		required_keys = raw_data[0].keys() if raw_data else []

	if def_val is None:
		def_val = {}

	# 유효한 데이터만 저장할 리스트
	valid_rows = []

	for idx, item in enumerate(raw_data):
		if index_key not in item:
			error("missing required index key in item[%d] %s", idx, item)
			continue

		row = {index_key: item[index_key]}

		# 필요한 키만 선택하고, 누락된 키는 기본값으로 채움
		for key,col in key_to_column.items():
			if key in item:
				row[col] = item[key]

		# 모든 키가 유효한 경우에만 추가? 유효성 체크는 pd 변환 이후로..
		valid_rows.append(row)

	# pandas DataFrame 생성
	if not valid_rows:
		raise ValueError("No valid data to create DataFrame")

	df = pd.DataFrame(valid_rows)

	return df


# export
def ConvertDayPolChartToDf():
	'''
	인자로 받는

	'''
	index_key = 'dt'

	key_to_column = {
		'open_pric':'Open',
		'high_pric':'High',
		'low_pric':'Low',
		'cur_pric':'Close',
		'trde_qty':'Volume',
	}

	df = convert_to_dataframe(raw_data, index_key, key_to_column)

	# 'dt' 컬럼을 datetime으로 변환
	try:
		df['dt'] = pd.to_datetime(df['dt'], format='%Y%m%d')
	except ValueError as e:
		error("Failed to convert 'dt' to datetime: %s", e)
		# TODO: 어느 행에서 문제가 발생했는지를 알려주는 게 도움이 될까?
		raise DateKeyError(f'Date key value error')

	# 'dt'를 인덱스로 설정
	df.set_index('dt', inplace=True)

	return df


#export
def FetchAndStoreChart(stk_cd:str, base_dt:str=''):
	'''

	'''
	pass




if __name__ == "__main__":
	from utils_log import LogInit
	LogInit()

	if len(sys.argv) >= 2 and sys.argv[1] == 'test-conv':
		info('**** testing dataframe conversion')

		raw_data = [
			{'dt': '20250104', 'open_pric': '15', 'high_pric': '25'},
			{'dt': '20250101', 'open_pric': '10', 'high_pric': '20', 'unknown': 'test'}, # 미인식 키
			{                  'open_pric': '20', 'high_pric': '30'},  # 'dt'키 누락
			{'dt': '20250103', 'open_pric': '12', },  # 'high_pric'키 누락
		]
		index_key = 'dt'

		key_to_column = {
			'open_pric':'Open',
			'high_pric':'High',
			'low_pric':'Low',
			'cur_pric':'Close',
			'trde_qty':'Volume',
		}

		try:
			df = convert_to_dataframe(raw_data, index_key, key_to_column)
			print(df)

		except Exception as e:
			error(f"Error processing data: {e}")
			raise e

		sys.exit(0)


	debug('no test option')
	pass

