"""
범용 웹 스크래핑 서비스

증권사 API로 제공되지 않는 시세(금, 향후 가상자산 등)를 페이지에서 추출한다.
특정 자산에 종속되지 않는 **범용 엔진**이며, 대상 정의는 전부 설정 파일
(`config/scrape_targets.yaml`)에 외부화되어 있다. → URL·XPath 하드코딩 없음.

구성:
    ScrapeConfig  : 설정 파일 로드/파싱 (mtime 감지 → 파일 수정 시 자동 재로드)
    Scraper       : HTML 조회(+TTL 캐시) → XPath 추출 → 숫자 정규화

조회 방식은 대상별 `render` 설정으로 선택한다 (기본 `auto`):
    never  : 정적 HTTP GET만 사용 (가장 가벼움)
    auto   : 정적으로 먼저 시도 → 실패하면 그 대상만 headless 렌더링으로 재시도
    always : 항상 headless 렌더링 (CSR·봇차단이 확실한 대상)

새 자산 추가 절차: YAML에 group/target만 추가하면 코드 수정 없이 동작한다.
"""
import os
import time
import httpx
import logging
import threading
from typing import Any, Dict, List, Optional

import yaml
from lxml import html as lxml_html

from app.core.config import config
from app.services.base import normalize_price
from app.services.renderer import get_renderer, RenderError

logger = logging.getLogger(__name__)

#: 조회 방식 (대상별 `render` 설정값)
RENDER_NEVER = "never"    # 정적 HTTP GET만
RENDER_AUTO = "auto"      # 정적 → 실패 시 렌더링 폴백
RENDER_ALWAYS = "always"  # 항상 렌더링
RENDER_MODES = (RENDER_NEVER, RENDER_AUTO, RENDER_ALWAYS)


class ScrapeError(Exception):
    """스크래핑 공통 에러"""
    pass


class ScrapeConfigError(ScrapeError):
    """설정 파일 문제 (없음/형식 오류/대상 미정의)"""
    pass


class ScrapeFetchError(ScrapeError):
    """대상 페이지 요청 실패"""
    pass


class ScrapeExtractError(ScrapeError):
    """XPath 추출 실패 (페이지 구조 변경 가능성)"""
    pass


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------
class ScrapeConfig:
    """스크래핑 대상 설정 (YAML) 로더"""

    def __init__(self, path: Optional[str] = None):
        self.path = path or config.SCRAPE_CONFIG_PATH
        self._data: Dict[str, Any] = {}
        self._loaded_mtime: Optional[float] = None
        self._lock = threading.Lock()

    def _load_if_needed(self):
        """파일이 없거나 수정되었으면 로드 (운영 중 설정 갱신 즉시 반영)"""
        if not os.path.isfile(self.path):
            raise ScrapeConfigError(f"스크래핑 설정 파일이 없습니다: {self.path}")

        mtime = os.path.getmtime(self.path)
        if self._loaded_mtime == mtime and self._data:
            return

        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ScrapeConfigError(f"스크래핑 설정 파싱 실패({self.path}): {e}")

            if not isinstance(data, dict) or "groups" not in data:
                raise ScrapeConfigError(
                    f"스크래핑 설정에 'groups' 항목이 없습니다: {self.path}"
                )

            self._data = data
            self._loaded_mtime = mtime
            logger.info(f"스크래핑 설정 로드: {self.path}")

    @property
    def defaults(self) -> Dict[str, Any]:
        self._load_if_needed()
        return self._data.get("defaults") or {}

    def groups(self) -> List[str]:
        """정의된 그룹 목록 (예: ["gold", "crypto"])"""
        self._load_if_needed()
        return list((self._data.get("groups") or {}).keys())

    def targets(self, group: str) -> List[str]:
        """그룹 내 대상 키 목록 (예: ["international", "krx"])"""
        self._load_if_needed()
        g = (self._data.get("groups") or {}).get(group) or {}
        return list(g.keys())

    def get_target(self, group: str, target: str) -> Dict[str, Any]:
        """
        대상 설정 조회 (defaults 병합)

        Raises:
            ScrapeConfigError: 그룹/대상 미정의, 필수 항목 누락
        """
        self._load_if_needed()
        groups = self._data.get("groups") or {}

        if group not in groups:
            raise ScrapeConfigError(
                f"정의되지 않은 그룹입니다: '{group}'. 사용 가능: {list(groups.keys())}"
            )

        entries = groups.get(group) or {}
        if target not in entries:
            raise ScrapeConfigError(
                f"정의되지 않은 대상입니다: '{group}.{target}'. "
                f"사용 가능: {list(entries.keys())}"
            )

        merged = dict(self.defaults)
        merged.update(entries.get(target) or {})

        for required in ("url", "xpath"):
            if not merged.get(required):
                raise ScrapeConfigError(
                    f"'{group}.{target}' 설정에 '{required}'가 없습니다 ({self.path})"
                )

        merged["group"] = group
        merged["target"] = target
        return merged


# ---------------------------------------------------------------------------
# 스크래퍼
# ---------------------------------------------------------------------------
class Scraper:
    """설정 기반 범용 스크래퍼 (HTML TTL 캐시 포함)"""

    def __init__(self, scrape_config: Optional[ScrapeConfig] = None):
        self.config = scrape_config or ScrapeConfig()
        # (url, rendered) -> (fetched_at, html_text)
        # 정적 HTML과 렌더링 HTML은 내용이 다르므로 캐시 키를 분리한다.
        self._html_cache: Dict[tuple, tuple] = {}

    def _get_cached_html(self, key: tuple, ttl: int) -> Optional[str]:
        entry = self._html_cache.get(key)
        if not entry:
            return None
        fetched_at, text = entry
        if time.time() - fetched_at > ttl:
            return None
        logger.debug(f"[scrape] HTML 캐시 사용: {key}")
        return text

    def invalidate_cache(self, url: Optional[str] = None) -> int:
        """
        HTML 캐시 무효화

        Args:
            url: 지정 시 해당 URL만, 미지정 시 전체

        Returns:
            제거된 캐시 항목 수
        """
        if url is None:
            count = len(self._html_cache)
            self._html_cache.clear()
        else:
            keys = [k for k in self._html_cache if k[0] == url]
            for k in keys:
                del self._html_cache[k]
            count = len(keys)
        if count:
            logger.info(f"[scrape] 캐시 무효화: {url or '전체'} ({count}건)")
        return count

    async def fetch_html(
        self,
        url: str,
        timeout: float,
        user_agent: str,
        cache_ttl: int,
        force_refresh: bool = False,
    ) -> str:
        """정적 HTTP GET으로 HTML 조회 (TTL 캐시 → 동일 URL 중복 요청 방지)"""
        key = (url, False)
        if not force_refresh:
            cached = self._get_cached_html(key, cache_ttl)
            if cached is not None:
                return cached

        headers = {"User-Agent": user_agent} if user_agent else {}
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers, timeout=timeout)
        except httpx.HTTPError as e:
            raise ScrapeFetchError(f"페이지 요청 실패({url}): {e}")

        if response.status_code != 200:
            raise ScrapeFetchError(f"페이지 응답 오류({url}): HTTP {response.status_code}")

        text = response.text
        self._html_cache[key] = (time.time(), text)
        return text

    async def render_html(
        self,
        url: str,
        timeout: float,
        user_agent: str,
        cache_ttl: int,
        wait_ms: int,
        wait_for: Optional[str],
        force_refresh: bool = False,
    ) -> str:
        """headless 브라우저로 렌더링하여 HTML 조회 (TTL 캐시 적용)"""
        key = (url, True)
        if not force_refresh:
            cached = self._get_cached_html(key, cache_ttl)
            if cached is not None:
                return cached

        try:
            text = await get_renderer().render(
                url=url,
                timeout=timeout,
                # 렌더링 시 UA는 렌더러 기본값(실제 크롬)을 쓰는 편이 봇 차단 회피에 유리.
                # 설정에서 명시적으로 준 경우에만 덮어쓴다.
                user_agent=user_agent or None,
                wait_ms=wait_ms,
                wait_for=wait_for,
            )
        except RenderError as e:
            raise ScrapeFetchError(str(e))

        self._html_cache[key] = (time.time(), text)
        return text

    @staticmethod
    def extract(html_text: str, xpath: str) -> str:
        """
        XPath로 텍스트 추출

        Raises:
            ScrapeExtractError: 매칭 실패(페이지 구조 변경 의심) 또는 빈 값
        """
        try:
            tree = lxml_html.fromstring(html_text)
            nodes = tree.xpath(xpath)
        except Exception as e:
            raise ScrapeExtractError(f"XPath 처리 실패: {e}")

        if not nodes:
            raise ScrapeExtractError(
                "XPath에 해당하는 요소를 찾지 못했습니다. "
                "페이지 구조가 변경되었을 수 있습니다. "
                "(config/scrape_targets.yaml의 xpath 갱신 필요)"
            )

        node = nodes[0]
        text = node.text_content() if hasattr(node, "text_content") else str(node)
        text = (text or "").strip()

        if not text:
            raise ScrapeExtractError("추출된 값이 비어 있습니다. (lazy 로딩/구조 변경 의심)")
        return text

    async def _try_static(self, conf: Dict[str, Any], force_refresh: bool) -> str:
        """정적 경로로 값 추출"""
        html_text = await self.fetch_html(
            url=conf["url"],
            timeout=float(conf.get("timeout", 10)),
            user_agent=conf.get("user_agent", ""),
            cache_ttl=int(conf.get("cache_ttl", 60)),
            force_refresh=force_refresh,
        )
        return self.extract(html_text, conf["xpath"])

    async def _try_render(self, conf: Dict[str, Any], force_refresh: bool) -> str:
        """렌더링 경로로 값 추출"""
        html_text = await self.render_html(
            url=conf["url"],
            # 렌더링은 정적보다 오래 걸리므로 최소 30초는 확보
            timeout=float(conf.get("render_timeout", max(float(conf.get("timeout", 10)), 30))),
            user_agent=conf.get("render_user_agent", ""),
            cache_ttl=int(conf.get("cache_ttl", 60)),
            wait_ms=int(conf.get("wait_ms", 2500)),
            wait_for=conf.get("wait_for"),
            force_refresh=force_refresh,
        )
        return self.extract(html_text, conf["xpath"])

    async def scrape(
        self, group: str, target: str, force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        대상 1건 스크래핑

        조회 방식은 설정의 `render`(never|auto|always)를 따른다.
        `auto`는 정적으로 먼저 시도하고, 실패한 대상에 한해 렌더링으로 재시도한다.

        Args:
            group: 그룹 키
            target: 대상 키
            force_refresh: True면 캐시를 무시하고 새로 조회

        Returns:
            {
                "group", "target", "label", "raw", "value",
                "unit", "currency", "url", "method", "timestamp"
            }
        """
        conf = self.config.get_target(group, target)

        mode = str(conf.get("render", RENDER_AUTO)).strip().lower()
        if mode not in RENDER_MODES:
            raise ScrapeConfigError(
                f"'{group}.{target}'의 render 값이 올바르지 않습니다: '{mode}'. "
                f"사용 가능: {list(RENDER_MODES)}"
            )

        method = None
        raw = None

        if mode == RENDER_ALWAYS:
            raw = await self._try_render(conf, force_refresh)
            method = "render"

        elif mode == RENDER_NEVER:
            raw = await self._try_static(conf, force_refresh)
            method = "static"

        else:  # auto — 정적 우선, 실패 시 해당 대상만 렌더링 폴백
            try:
                raw = await self._try_static(conf, force_refresh)
                method = "static"
            except ScrapeError as static_err:
                logger.info(
                    f"[scrape] {group}.{target} 정적 실패 → 렌더링 폴백 시도 ({static_err})"
                )
                try:
                    raw = await self._try_render(conf, force_refresh)
                    method = "render"
                except ScrapeError as render_err:
                    # 두 경로 모두 실패 → 원인을 함께 보여준다
                    raise ScrapeExtractError(
                        f"정적/렌더링 모두 실패. 정적: {static_err} | 렌더링: {render_err}"
                    )

        value = normalize_price(raw)  # "4,049.30" → 4049.3 / "190,990" → 190990
        if value is None:
            raise ScrapeExtractError(f"추출값을 숫자로 변환할 수 없습니다: '{raw}'")

        logger.info(
            f"[scrape] 성공: {group}.{target} = {value} ({conf.get('unit', '')}) [{method}]"
        )

        return {
            "group": group,
            "target": target,
            "label": conf.get("label", ""),
            "raw": raw,
            "value": value,
            "unit": conf.get("unit", ""),
            "currency": conf.get("currency", ""),
            "url": conf["url"],
            "method": method,  # static | render — 어느 경로로 얻었는지
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    async def scrape_group(
        self, group: str, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """그룹 내 모든 대상 스크래핑 (HTML 캐시 덕분에 동일 URL은 1회만 요청)"""
        results = []
        for target in self.config.targets(group):
            results.append(await self.scrape(group, target, force_refresh=force_refresh))
        return results


# 싱글톤 인스턴스
_scraper: Optional[Scraper] = None


def get_scraper() -> Scraper:
    """스크래퍼 싱글톤 인스턴스 반환"""
    global _scraper
    if _scraper is None:
        _scraper = Scraper()
    return _scraper
