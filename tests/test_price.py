"""
시세 조회 테스트 스크립트 (비동기)
"""
import sys
sys.path.insert(0, '..')

import asyncio
from app.services.kiwoom import get_kiwoom_client


async def main():
    """비동기 메인 함수"""
    print("=== 키움 API 시세 조회 테스트 (비동기) ===\n")

    try:
        client = get_kiwoom_client()
        print("클라이언트 생성 완료\n")

        # 삼성전자 시세 조회
        print("삼성전자(005930) 시세 조회 중...")
        price_data = await client.get_stock_price("005930", "KOSPI")

        print("✅ 시세 조회 성공!")
        print(f"  종목 코드: {price_data['code']}")
        print(f"  현재가: {price_data['price']:,}원")
        print(f"  조회 시각: {price_data['timestamp']}")
        print(f"  기준 날짜: {price_data.get('date', 'N/A')}")
        print(f"  시장: {price_data['market']}")

    except Exception as e:
        print(f"❌ 에러 발생: {e.__class__.__name__}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
