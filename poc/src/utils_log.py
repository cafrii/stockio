# -*- coding: utf-8 -*-
"""
utils_log.py

"""

import logging
import time, os

_logging_init = False
_root_logger = None




class CustomFormatter(logging.Formatter):
	"""
	"""
	def __init__(self):
		format = '%(asctime)s %(levelname)s %(name)s %(funcName)s: %(message)s'
		datefmt = '%H:%M:%S'
		super().__init__(format, datefmt, style='%')

	def format(self, record):
		# 파일 이름에서 .py 확장자 제거
		if record.name == 'root':
			record.name = os.path.splitext(record.filename)[0]
		record.levelname = record.levelname[:1]
		return super().format(record)


def get_logger(name, level=logging.INFO) -> logging.Logger:
	"""
	get logger by name
	name 이 None 이면 root logger 를 설정하고 반환한다.
	"""
	global _root_logger
	# logging.warning("******** get_logger: %s", name)

	if not _root_logger:
		# logging.warning("******** get_logger: add handler for root logger")
		_root_logger = logging.getLogger()
		_root_logger.handlers = []  # 기존 핸들러 제거
		handler = logging.StreamHandler()
		formatter = CustomFormatter()
		handler.setFormatter(formatter)
		_root_logger.addHandler(handler)
		_root_logger.setLevel(logging.DEBUG)

	mylogger = logging.getLogger(name)

	if level > 0:
		logging.info("logger (%s): set level to %d", name, level)
		mylogger.setLevel(level)

	return mylogger




"""
conventional print style logging

"""


"""
config log levels from environment var.

	env var name: 'dbg'
	env var value format:
		<modulename>:<level>[,<modulename>:<level>,...]

	modulename: any python logger name
	level: one of critical,error,warning,info,debug

ex:
	dbg=root:warning,utils.text:debug,widgets.textinput:debug python xxx.py
	dbg=root:debug  python xxx.py

"""
def set_level_from_env():
	# get env var
	val = os.getenv('dbg', '').strip()

	if not val: # empty string
		return

	# split to each token pair
	for pair in val.split(sep=','):
		pair = pair.strip()
		if not pair:
			continue # skip blanks
		# pair has format <name>:<value>
		name,level = pair.split(sep=':')
		if not name or not level:
			continue

		# change level string to number
		numeric_level = getattr(logging, level.upper(), None)

		if not isinstance(numeric_level, int):
			# invalid level string
			logging.warning("level '%s' invalid", level)
			continue

		# search logger
		if name not in logging.root.manager.loggerDict:
			if 'cml.'+name in logging.root.manager.loggerDict:
				# ok, we assume that user skips 'cml.' prefix for easy typting.
				name = 'cml.' + name

		logging.info("logger[%s] level set to %d (%s)", name, numeric_level, level)
		logger = logging.getLogger(name)
		logger.setLevel(numeric_level)



def LogInit():
	global _logging_init
	if _logging_init:
		return

	# root 로거 설정
	logger = get_logger(None, logging.INFO)
	 # 이 기본 로깅 함수들은 모두 root logger 를 사용한다.

	# 루트 로거 레벨 재설정하려면 이후에 다음과 같이 호출.
	# logging.getLogger().setLevel(logging.DEBUG)

	# 환경 변수 옵션에 따른 추가 설정
	set_level_from_env()

	_logging_init = True
