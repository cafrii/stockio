"""
시세 조회 디버그 테스트
"""
import sys
sys.path.insert(0, '.')

import json
from app.services.kiwoom import get_kiwoom_client

if __name__ == "__main__":
    print("=== 키움 API 시세 조회 디버그 ===\n")

    try:
        client = get_kiwoom_client()

        # 토큰 발급
        token = client.get_token()
        print(f"토큰: {token[:20]}...\n")

        # API 직접 호출하여 응답 확인
        import requests
        import time

        url = f"{client.api_host}/api/dostk/chart"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "cont-yn": "N",
            "next-key": "",
            "api-id": "ka10081",
        }
        data = {
            "stk_cd": "005930",
            "base_dt": time.strftime("%Y%m%d"),
            "upd_stkpc_tp": "1",
        }

        print("API 호출 중...")
        print(f"URL: {url}")
        print(f"Headers: {json.dumps({k: v[:20] + '...' if k == 'authorization' else v for k, v in headers.items()}, indent=2)}")
        print(f"Data: {json.dumps(data, indent=2)}\n")

        response = requests.post(url, headers=headers, json=data, timeout=10)

        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}\n")

        result = response.json()
        print("응답 본문 (처음 2000자):")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
        print("\n...")

        # 주요 필드 확인
        print("\n=== 주요 필드 확인 ===")
        print(f"return_code: {result.get('return_code')}")
        print(f"return_msg: {result.get('return_msg')}")
        print(f"stk_cd: {result.get('stk_cd')}")

        chart_data = result.get('stk_dt_pole_chart_qry')
        print(f"stk_dt_pole_chart_qry 타입: {type(chart_data)}")
        if isinstance(chart_data, list) and len(chart_data) > 0:
            print(f"차트 데이터 개수: {len(chart_data)}")
            print(f"첫 번째 데이터 키들: {list(chart_data[0].keys())}")
            print(f"첫 번째 데이터:")
            print(json.dumps(chart_data[0], indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 에러 발생: {e.__class__.__name__}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
