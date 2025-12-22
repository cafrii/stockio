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
                  "price": 71000,
                  "timestamp": "2025-12-22T14:30:00",
                  "market": "KOSPI"
              }

    Returns:
        XML 문자열
        <?xml version="1.0" encoding="UTF-8"?>
        <stock>
          <code>005930</code>
          <price>71000</price>
          <timestamp>2025-12-22T14:30:00</timestamp>
          <market>KOSPI</market>
        </stock>
    """
    root = ET.Element("stock")

    # 데이터 추가
    code_elem = ET.SubElement(root, "code")
    code_elem.text = str(data.get("code", ""))

    price_elem = ET.SubElement(root, "price")
    price_elem.text = str(data.get("price", ""))

    timestamp_elem = ET.SubElement(root, "timestamp")
    timestamp_elem.text = str(data.get("timestamp", ""))

    if "market" in data:
        market_elem = ET.SubElement(root, "market")
        market_elem.text = str(data.get("market", ""))

    return prettify_xml(root)


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
