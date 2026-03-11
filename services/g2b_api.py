import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")

EDU_KEYWORDS = [
    "교육", "연수", "훈련", "아카데미", "캠프", "멘토링",
    "운영", "위탁", "프로그램", "직무", "역량", "강화"
]

AI_KEYWORDS = [
    "AI", "인공지능", "데이터", "빅데이터", "디지털",
    "DX", "AX", "SW", "소프트웨어", "코딩", "프로그래밍",
    "머신러닝", "딥러닝", "생성형", "GPT", "LLM"
]


def fetch_bid_list(num_of_rows=50, days_back=7, page_count=3):
    """
    나라장터 공고 XML을 페이지별로 가져옵니다.
    return: [xml_text_1, xml_text_2, ...]
    """
    url = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days_back)

    xml_results = []

    for page in range(1, page_count + 1):
        params = {
            "ServiceKey": SERVICE_KEY,
            "inqryDiv": "1",
            "inqryBgnDt": start_dt.strftime("%Y%m%d0000"),
            "inqryEndDt": end_dt.strftime("%Y%m%d2359"),
            "pageNo": str(page),
            "numOfRows": str(num_of_rows),
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        xml_results.append(response.text)

    return xml_results


def parse_response_debug(raw_xml):
    """
    첫 페이지 XML 기준 디버그 정보 추출
    """
    debug = {
        "resultCode": "",
        "resultMsg": "",
        "totalCount": "",
        "preview": raw_xml[:500]
    }

    try:
        root = ET.fromstring(raw_xml)
        debug["resultCode"] = (root.findtext(".//resultCode") or "").strip()
        debug["resultMsg"] = (root.findtext(".//resultMsg") or "").strip()
        debug["totalCount"] = (root.findtext(".//totalCount") or "").strip()
    except Exception as e:
        debug["resultMsg"] = f"XML parse error: {e}"

    return debug


def _safe_find_text(item, tag_name):
    value = item.findtext(tag_name)
    return value.strip() if value else ""


def parse_all_bids(raw_xml_list):
    """
    여러 페이지 XML을 합쳐 공고 목록으로 변환
    """
    all_bids = []

    for raw_xml in raw_xml_list:
        try:
            root = ET.fromstring(raw_xml)
        except ET.ParseError:
            continue

        items = root.findall(".//item")

        for item in items:
            all_bids.append({
                "공고명": _safe_find_text(item, "bidNtceNm"),
                "공고번호": _safe_find_text(item, "bidNtceNo"),
                "공고기관": _safe_find_text(item, "ntceInsttNm"),
                "수요기관": _safe_find_text(item, "dminsttNm"),
                "마감일": _safe_find_text(item, "bidClseDt"),
                "예산": _safe_find_text(item, "asignBdgtAmt") or _safe_find_text(item, "presmptPrce"),
            })

    # 공고번호 기준 중복 제거
    deduped = {}
    for bid in all_bids:
        bid_no = bid["공고번호"] or bid["공고명"]
        deduped[bid_no] = bid

    return list(deduped.values())


def filter_ai_education_bids(all_bids):
    """
    AI 관련 + 교육운영 관련 공고만 필터
    """
    filtered = []

    for bid in all_bids:
        text = f'{bid["공고명"]} {bid["공고기관"]} {bid["수요기관"]}'.lower()

        has_edu = any(keyword.lower() in text for keyword in EDU_KEYWORDS)
        has_ai = any(keyword.lower() in text for keyword in AI_KEYWORDS)

        if has_edu and has_ai:
            filtered.append(bid)

    return filtered