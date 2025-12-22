

import sys, os
import json
from logging import debug as log, info



def test_json():
    tj = json.loads('''
    {
        "expires_dt": "20250504211039",
        "return_msg": "정상적으로 처리되었습니다",
        "token_type": "Bearer",
        "return_code": 0,
        "token": "qmoOCBHVMnl5J3m0hLLPa8O1h7K07uq6PUnOWxW46ibtJdoihkjRdCcsoHJEr76ka_rn7YeqiyKlCLL2i75vgg"
    }
    ''')
    print(tj)
    if token := tj.get('token', None):
        print(token)
    else:
        print('no token info')

def test_time():
    import time
    now = time.strftime('%Y%m%d%H%M%S')
    print(f'now: {now}')

def test_log():
    info('this is info message')
    log('this is log message')



if __name__ == '__main__':
    from utils_log import LogInit
    LogInit()

    # test_json()
    # test_time()
    test_log()

    sys.exit(0)