"""
범용 웹 스크래핑 서비스

증권사 API로 제공되지 않는 시세(금, 향후 가상자산 등)를 페이지에서 추출한다.
특정 자산에 종속되지 않는 **범용 엔진**이며, 대상 정의는 전부 설정 파일
(`config/scrape_targets.yaml`)에 외부화되어 있다. → URL·XPath 하드코딩 없음.

구성:
    ScrapeConfig  : 설정 파일 로드/파싱 (mtime 감지 → 파일 수정 시 자동 재로드)
    Scraper       : HTML 조회(+TTL 캐시) → XPath 추출 → 숫자 정규화

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

logger = logging.getLogger(__name__)


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
        # url -> (fetched_at, html_text)
        self._html_cache: Dict[str, tuple] = {}

    def _get_cached_html(self, url: str, ttl: int) -> Optional[str]:
        entry = self._html_cache.get(url)
        if not entry:
            return None
        fetched_at, text = entry
        if time.time() - fetched_at > ttl:
            return None
        logger.debug(f"[scrape] HTML 캐시 사용: {url}")
        return text

    async def fetch_html(self, url: str, timeout: float, user_agent: str, cache_ttl: int) -> str:
        """대상 페이지 HTML 조회 (TTL 캐시 → 동일 URL 중복 요청 방지)"""
        cached = self._get_cached_html(url, cache_ttl)
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
        self._html_cache[url] = (time.time(), text)
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

    async def scrape(self, group: str, target: str) -> Dict[str, Any]:
        """
        대상 1건 스크래핑

        Returns:
            {
                "group", "target", "label", "raw", "value",
                "unit", "currency", "url", "timestamp"
            }
        """
        conf = self.config.get_target(group, target)

        html_text = await self.fetch_html(
            url=conf["url"],
            timeout=float(conf.get("timeout", 10)),
            user_agent=conf.get("user_agent", ""),
            cache_ttl=int(conf.get("cache_ttl", 60)),
        )

        raw = self.extract(html_text, conf["xpath"])
        value = normalize_price(raw)  # "4,049.30" → 4049.3 / "190,990" → 190990
        if value is None:
            raise ScrapeExtractError(f"추출값을 숫자로 변환할 수 없습니다: '{raw}'")

        logger.info(f"[scrape] 성공: {group}.{target} = {value} ({conf.get('unit', '')})")

        return {
            "group": group,
            "target": target,
            "label": conf.get("label", ""),
            "raw": raw,
            "value": value,
            "unit": conf.get("unit", ""),
            "currency": conf.get("currency", ""),
            "url": conf["url"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    async def scrape_group(self, group: str) -> List[Dict[str, Any]]:
        """그룹 내 모든 대상 스크래핑 (HTML 캐시 덕분에 동일 URL은 1회만 요청)"""
        results = []
        for target in self.config.targets(group):
            results.append(await self.scrape(group, target))
        return results


# 싱글톤 인스턴스
_scraper: Optional[Scraper] = None


def get_scraper() -> Scraper:
    """스크래퍼 싱글톤 인스턴스 반환"""
    global _scraper
    if _scraper is None:
        _scraper = Scraper()
    return _scraper
