"""
XML 응답 빌더

Google Spreadsheet의 IMPORTXML 함수를 위한 XML 응답을 생성합니다.
"""
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from xml.dom import minidom


def prettify_xml(elem: ET.Element) -> str:
    """XML을 보기 좋게 포맷팅"""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def build_stock_price_xml(data: Dict[str, Any]) -> str:
    """
    주식 시세 데이터를 XML로 변환

    Args:
        data: 시세 데이터 딕셔너리
              {
                  "code": "005930",
                  "price": 54300,
                  "high52w": 88800,
                  "high52w_date": "20240711",
                  "timestamp": "2025-12-22T14:30:00",
                  "market": "KOSPI"
              }

    Returns:
        XML 문자열
        <?xml version="1.0" encoding="UTF-8"?>
        <stock>
          <code>005930</code>
          <price>54300</price>
          <high52w>88800</high52w>
          <low52w>49900</low52w>
          <high52w_date>20240711</high52w_date>
          <timestamp>2025-12-22T14:30:00</timestamp>
          <market>KOSPI</market>
        </stock>
    """
    root = ET.Element("stock")

    code_elem = ET.SubElement(root, "code")
    code_elem.text = str(data.get("code", ""))

    price_elem = ET.SubElement(root, "price")
    price_elem.text = str(data.get("price", ""))

    if data.get("high52w") is not None:
        high52w_elem = ET.SubElement(root, "high52w")
        high52w_elem.text = str(data.get("high52w"))

    if data.get("low52w") is not None:
        low52w_elem = ET.SubElement(root, "low52w")
        low52w_elem.text = str(data.get("low52w"))

    if data.get("high52w_date"):
        high52w_date_elem = ET.SubElement(root, "high52w_date")
        high52w_date_elem.text = str(data.get("high52w_date"))

    timestamp_elem = ET.SubElement(root, "timestamp")
    timestamp_elem.text = str(data.get("timestamp", ""))

    if "market" in data:
        market_elem = ET.SubElement(root, "market")
        market_elem.text = str(data.get("market", ""))

    if data.get("provider"):
        provider_elem = ET.SubElement(root, "provider")
        provider_elem.text = str(data.get("provider"))

    return prettify_xml(root)


def build_scrape_xml(data: Dict[str, Any], root_tag: str = "quote") -> str:
    """
    스크래핑 결과(금 시세 등)를 XML로 변환

    Args:
        data: scraper.scrape() 결과 딕셔너리
        root_tag: 루트 태그명 (예: "gold")

    Returns:
        XML 문자열
        <?xml version="1.0" encoding="UTF-8"?>
        <gold>
          <target>krx</target>
          <label>국내 금 시세 (KRX 금 현물)</label>
          <price>190990</price>
          <unit>원/g</unit>
          <currency>KRW</currency>
          <timestamp>2026-07-24T01:00:00</timestamp>
        </gold>
    """
    root = ET.Element(root_tag)
    _append_scrape_fields(root, data)
    return prettify_xml(root)


def build_scrape_list_xml(
    items: list, root_tag: str = "quotes", item_tag: str = "quote"
) -> str:
    """
    스크래핑 결과 여러 건을 XML로 변환

    Args:
        items: scraper.scrape() 결과 딕셔너리 리스트
        root_tag: 루트 태그명 (예: "golds")
        item_tag: 각 항목 태그명 (예: "gold")

    Returns:
        XML 문자열
    """
    root = ET.Element(root_tag)
    for data in items:
        item = ET.SubElement(root, item_tag)
        _append_scrape_fields(item, data)
    return prettify_xml(root)


def _append_scrape_fields(parent: ET.Element, data: Dict[str, Any]) -> None:
    """스크래핑 결과 딕셔너리를 XML 하위 요소로 추가 (공통 로직)"""
    target_elem = ET.SubElement(parent, "target")
    target_elem.text = str(data.get("target", ""))

    if data.get("label"):
        label_elem = ET.SubElement(parent, "label")
        label_elem.text = str(data.get("label"))

    # 구글시트 IMPORTXML 호환을 위해 시세 값의 태그명은 <price>로 통일
    price_elem = ET.SubElement(parent, "price")
    price_elem.text = str(data.get("value", ""))

    if data.get("unit"):
        unit_elem = ET.SubElement(parent, "unit")
        unit_elem.text = str(data.get("unit"))

    if data.get("currency"):
        currency_elem = ET.SubElement(parent, "currency")
        currency_elem.text = str(data.get("currency"))

    timestamp_elem = ET.SubElement(parent, "timestamp")
    timestamp_elem.text = str(data.get("timestamp", ""))

    # 어느 경로로 얻은 값인지 (static | render) — 운영/진단용
    if data.get("method"):
        method_elem = ET.SubElement(parent, "method")
        method_elem.text = str(data.get("method"))


def build_error_xml(
    message: str, code: Optional[int] = None, detail: Optional[str] = None
) -> str:
    """
    에러 응답 XML 생성

    Args:
        message: 에러 메시지
        code: HTTP 상태 코드 (선택)
        detail: 상세 에러 정보 (선택)

    Returns:
        XML 문자열
        <?xml version="1.0" encoding="UTF-8"?>
        <error>
          <message>종목 코드가 필요합니다</message>
          <code>400</code>
          <detail>...</detail>
        </error>
    """
    root = ET.Element("error")

    message_elem = ET.SubElement(root, "message")
    message_elem.text = message

    if code is not None:
        code_elem = ET.SubElement(root, "code")
        code_elem.text = str(code)

    if detail:
        detail_elem = ET.SubElement(root, "detail")
        detail_elem.text = detail

    return prettify_xml(root)


def build_simple_xml(tag: str, value: str) -> str:
    """
    단순한 XML 생성

    Args:
        tag: XML 태그명
        value: 값

    Returns:
        XML 문자열
        <?xml version="1.0" encoding="UTF-8"?>
        <tag>value</tag>
    """
    root = ET.Element(tag)
    root.text = value
    return prettify_xml(root)
