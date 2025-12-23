"""
토큰 발급 테스트 스크립트 (비동기)
"""
import sys
sys.path.insert(0, '..')

import asyncio
from app.services.kiwoom import get_kiwoom_client


async def main():
    """비동기 메인 함수"""
    print("=== 키움 API 토큰 발급 테스트 (비동기) ===\n")

    try:
        client = get_kiwoom_client()
        print("클라이언트 생성 완료")
        print(f"API 호스트: {client.api_host}")
        print(f"APPKEY: {client.appkey[:10]}...")
        print()

        print("토큰 발급 요청 중...")
        token = await client.get_token()

        print("✅ 토큰 발급 성공!")
        print(f"토큰: {token[:20]}...")
        print(f"만료 시간: {client._token_expire_at}")
        print()

        # 캐시된 토큰 재사용 테스트
        print("캐시된 토큰 재사용 테스트...")
        token2 = await client.get_token()

        if token == token2:
            print("✅ 캐시된 토큰 재사용 성공!")
        else:
            print("❌ 토큰이 다릅니다")

    except Exception as e:
        print(f"❌ 에러 발생: {e.__class__.__name__}")
        print(f"   {e}")
        sys.exit(1)

    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(main())
