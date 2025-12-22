# -*- coding: utf-8 -*-
'''
utils_exception.py


'''

# custom exception

class ConfigError(Exception):
	'''
	api server url, appkey, secret not properly configured.
	'''
	pass

class ArgumentError(Exception):
	'''
	'''
	pass

class ApiError(Exception):
	'''
	general api error
	'''
	# def __init__(msg):
	# 	msg = f'API Error, {msg}'
	# 	super().__init__(msg)

	# return_msg:str
	# return_code:int
	pass

class AuthenticationError(ApiError):
	'''
	authenticate failed
	usually it occurred when invalid token is used.
	'''
	# '인증에 실패했습니다[8005:Token이 유효하지 않습니다]'
	# 3
	pass

'''
usage:
	if some error happens:
		raise AuthenticationError("Failed to get token")
		raise ApiError(f"API call failed: {jr.get('return_code')}-{jr.get('return_msg')}")

if __name__ == '__main__'
	try:
		GetCashBalance()
	except AuthenticationError as e:
		print(e)..

'''

class DateKeyError(ApiError):
	pass


class ApiMaintenanceException(Exception):
	'''
	api server maintenance exception
	'''
	pass
