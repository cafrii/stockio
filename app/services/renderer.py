"""
headless 브라우저 렌더링 모듈 (lazy 로딩 대응)

정적 HTTP GET으로는 값을 얻을 수 없는 페이지를 위한 확장 경로다.
해당하는 경우:
  - 클라이언트 사이드 렌더링(CSR) — HTML에는 값이 없고 JS 실행 후에 채워짐
  - 봇 차단(403) — 실제 브라우저 UA/환경이 필요함
  - 리다이렉트 후 렌더링

playwright는 **선택적 의존성**이다. 설치되어 있지 않아도 정적 스크래핑은 정상
동작하며, 렌더링이 필요한 시점에만 명확한 안내 에러를 발생시킨다.

브라우저는 싱글톤으로 재사용한다(매 요청 기동 시 1~2초 손해).
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RenderError(Exception):
    """렌더링 실패"""
    pass


class RenderUnavailableError(RenderError):
    """playwright 미설치 등으로 렌더링 경로를 쓸 수 없음"""
    pass


#: 봇 차단 회피를 위한 기본 UA (headless 기본 UA는 'HeadlessChrome'이라 차단되는 사이트가 있음)
DEFAULT_RENDER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)


class PageRenderer:
    """playwright 기반 페이지 렌더러 (브라우저 싱글톤 재사용)"""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._lock: Optional[asyncio.Lock] = None
        # 브라우저가 바인딩된 이벤트 루프. 루프가 바뀌면 재기동해야 한다.
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_lock(self) -> asyncio.Lock:
        """현재 루프에 맞는 Lock 반환 (Lock도 루프에 바인딩되므로 지연 생성)"""
        loop = asyncio.get_running_loop()
        if self._lock is None or self._loop is not loop:
            self._lock = asyncio.Lock()
        return self._lock

    async def _discard_browser(self):
        """현재 브라우저/플레이라이트 핸들 폐기 (다른 루프 소유라 정리 실패해도 무시)"""
        for closer in (
            getattr(self._browser, "close", None),
            getattr(self._playwright, "stop", None),
        ):
            if closer is None:
                continue
            try:
                await asyncio.wait_for(closer(), timeout=5)
            except Exception:
                pass
        self._browser = None
        self._playwright = None

    async def _ensure_browser(self):
        """브라우저 기동 (이미 살아 있고 같은 루프면 재사용)"""
        loop = asyncio.get_running_loop()

        # 다른 이벤트 루프에서 만들어진 브라우저는 이 루프에서 await 시 멈춘다.
        # (예: 테스트 클라이언트가 요청마다 새 루프를 만드는 경우)
        if self._browser is not None and self._loop is not loop:
            logger.warning("[render] 이벤트 루프 변경 감지 → 브라우저 재기동")
            await self._discard_browser()

        if self._browser is not None and self._browser.is_connected():
            return self._browser

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RenderUnavailableError(
                "headless 렌더링에 playwright가 필요합니다. "
                "설치: pip install playwright && playwright install chromium"
            )

        try:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                # 자동화 탐지 신호 축소 (봇 차단 사이트 대응)
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._loop = loop
            logger.info("[render] headless 브라우저 기동")
        except Exception as e:
            raise RenderError(f"headless 브라우저 기동 실패: {e}")

        return self._browser

    async def render(
        self,
        url: str,
        timeout: float = 30.0,
        user_agent: Optional[str] = None,
        wait_ms: int = 2500,
        wait_for: Optional[str] = None,
    ) -> str:
        """
        페이지를 렌더링하여 최종 HTML 반환

        Args:
            url: 대상 URL
            timeout: 페이지 이동 제한 시간(초)
            user_agent: UA (미지정 시 실제 크롬 UA 사용)
            wait_ms: 렌더링 완료 대기 시간(ms)
            wait_for: 이 CSS selector가 나타날 때까지 대기(지정 시 wait_ms보다 우선)

        Returns:
            렌더링된 HTML 문자열

        Raises:
            RenderUnavailableError / RenderError
        """
        async with self._get_lock():
            browser = await self._ensure_browser()

        context = None
        try:
            context = await browser.new_context(
                user_agent=user_agent or DEFAULT_RENDER_UA,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
            )
            page = await context.new_page()

            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=timeout * 1000
            )
            status = response.status if response else None

            # 값이 채워질 때까지 대기
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=timeout * 1000)
                except Exception:
                    logger.warning(f"[render] wait_for selector 미출현: {wait_for}")
            else:
                await page.wait_for_timeout(wait_ms)

            html = await page.content()
            logger.info(
                f"[render] 렌더링 완료: {url} (HTTP {status}, {len(html)} bytes, final={page.url})"
            )

            if status is not None and status >= 400:
                raise RenderError(f"렌더링 응답 오류({url}): HTTP {status}")

            return html

        except RenderError:
            raise
        except Exception as e:
            raise RenderError(f"렌더링 실패({url}): {e}")
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

    async def close(self):
        """브라우저 종료 (앱 shutdown 시 호출)"""
        if self._browser is None and self._playwright is None:
            return  # 렌더링을 한 번도 쓰지 않은 경우 no-op
        await self._discard_browser()
        self._loop = None
        logger.info("[render] headless 브라우저 종료")


# 싱글톤 인스턴스
_renderer: Optional[PageRenderer] = None


def get_renderer() -> PageRenderer:
    """렌더러 싱글톤 인스턴스 반환"""
    global _renderer
    if _renderer is None:
        _renderer = PageRenderer()
    return _renderer


def is_render_available() -> bool:
    """playwright 설치 여부"""
    try:
        import playwright.async_api  # noqa: F401
        return True
    except ImportError:
        return False
