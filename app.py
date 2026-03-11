import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from services.g2b_api import (
    fetch_bid_list,
    parse_all_bids,
    parse_response_debug,
    filter_ai_education_bids,
)

load_dotenv()

api_key = os.getenv("UPSTAGE_API_KEY")

st.set_page_config(page_title="EduBid Guide", page_icon="📘", layout="wide")
st.title("EduBid Guide")
st.caption("나라장터 AI 관련 교육운영 공고 기반 제안·가격 작성 가이드 및 초안 피드백")

if not api_key:
    st.error("UPSTAGE_API_KEY가 없습니다. .env 파일을 확인하세요.")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.upstage.ai/v1"
)


def classify_bid_type(bid):
    if not bid:
        return "AI 교육운영 일반형"

    title = bid.get("공고명", "")

    if "수학여행" in title or "현장체험" in title:
        return "수학여행/현장체험형"
    if "멘토링" in title:
        return "멘토링형"
    if "캠프" in title:
        return "캠프형"
    if "직무" in title or "역량" in title:
        return "직무역량교육형"
    if "온라인교육" in title:
        return "온라인교육형"
    if "AI" in title or "인공지능" in title:
        return "AI교육형"
    if "데이터" in title or "빅데이터" in title:
        return "데이터교육형"
    if "디지털" in title or "SW" in title or "소프트웨어" in title:
        return "디지털/SW교육형"
    if "교육" in title:
        return "교육프로그램형"

    return "AI 교육운영 일반형"


def generate_bid_diagnosis(client, bid):
    if not bid:
        return "공고를 선택하면 진단이 생성됩니다."

    bid_type = classify_bid_type(bid)

    prompt = f"""
당신은 공공기관의 AI 관련 교육운영 입찰 제안서 코치입니다.

아래 공고 정보를 보고,
이 공고에서 제안서 작성 시 가장 중요하게 봐야 할 포인트를
한국어로 1~2문장으로만 진단하세요.

반드시 지킬 조건:
- 추상적으로 쓰지 말 것
- 실제 작성 방향이 드러나게 쓸 것
- 가격, 운영계획, 유사실적, 리스크 중 무엇이 중요한지 드러낼 것
- 불확실한 내용은 단정하지 말고 "가능성", "중요할 수 있음"처럼 표현할 것

[공고명]
{bid.get("공고명", "")}

[공고기관]
{bid.get("공고기관", "")}

[수요기관]
{bid.get("수요기관", "")}

[예산]
{bid.get("예산", "")}

[마감일]
{bid.get("마감일", "")}

[1차 분류]
{bid_type}
"""

    try:
        response = client.chat.completions.create(
            model="solar-pro3",
            messages=[
                {"role": "system", "content": "당신은 공공입찰 제안서 작성 코치입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "이 공고는 AI 관련 교육운영 성격일 가능성이 있으며, 운영계획, 유사실적, 예산 타당성 정리가 중요할 수 있습니다."


def generate_writing_guide(client, bid_title, agency, bid_type, diagnosis):
    prompt = f"""
당신은 공공기관의 AI 관련 교육운영 용역 제안서 작성 코치입니다.

다음 공고 정보를 바탕으로 아래 형식으로 한국어로 작성하세요.

1. 반드시 강조해야 할 항목 5개
2. 가격/예산 작성 시 주의할 점 3개
3. 유사실적 작성 팁 3개
4. 이 공고에서 흔히 약해지는 포인트 3개

출력은 간단명료하게 하세요.
너무 추상적으로 쓰지 말고, 실제 제안서 작성에 바로 반영할 수 있게 쓰세요.

[공고명]
{bid_title}

[기관명]
{agency}

[공고 유형]
{bid_type}

[공고 진단]
{diagnosis}
"""

    response = client.chat.completions.create(
        model="solar-pro3",
        messages=[
            {"role": "system", "content": "당신은 공공입찰 제안서 작성 코치입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def generate_draft_feedback(client, bid_title, agency, bid_type, diagnosis, draft_text):
    prompt = f"""
당신은 공공기관의 AI 관련 교육운영 용역 제안서 평가자입니다.

다음 공고 정보와 초안을 비교해서
아래 형식으로 한국어로 작성하세요.

1. 잘한 점 3개
2. 빠진 점 5개
3. 수정 우선순위 3개
4. 이 초안이 실제 평가에서 약할 수 있는 이유 2개

출력은 간단명료하게 하세요.
말만 그럴듯하게 하지 말고, 실제로 부족한 부분을 콕 집어 쓰세요.

[공고명]
{bid_title}

[기관명]
{agency}

[공고 유형]
{bid_type}

[공고 진단]
{diagnosis}

[사용자 초안]
{draft_text}
"""

    response = client.chat.completions.create(
        model="solar-pro3",
        messages=[
            {"role": "system", "content": "당신은 공공입찰 제안서 평가자입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


# 세션 상태 초기화
if "selected_title" not in st.session_state:
    st.session_state.selected_title = None

if "bid_diagnosis" not in st.session_state:
    st.session_state.bid_diagnosis = ""

selected_bid = None
filtered_bids = []

st.subheader("1. 나라장터 AI 관련 교육운영 공고 목록")

try:
    raw_xml_list = fetch_bid_list(num_of_rows=50, days_back=7, page_count=3)
    debug_info = parse_response_debug(raw_xml_list[0])
    all_bids = parse_all_bids(raw_xml_list)
    filtered_bids = filter_ai_education_bids(all_bids)

    with st.expander("응답 디버그 보기"):
        st.json(debug_info)

    st.info(f"전체 공고 수: {len(all_bids)}건")
    st.info(f"AI 관련 교육운영 필터 후: {len(filtered_bids)}건")

    if all_bids:
        st.write("전체 공고 샘플 10건")
        st.dataframe(all_bids[:10], use_container_width=True)

    if filtered_bids:
        st.success(f"AI 관련 교육운영 공고 {len(filtered_bids)}건을 찾았습니다.")

        selected_title = st.selectbox(
            "분석할 공고를 선택하세요",
            options=[bid["공고명"] for bid in filtered_bids],
        )

        selected_bid = next(bid for bid in filtered_bids if bid["공고명"] == selected_title)

        st.write("선택한 공고")
        st.json(selected_bid)

        if st.session_state.selected_title != selected_title:
            st.session_state.selected_title = selected_title
            with st.spinner("공고 진단 생성 중..."):
                st.session_state.bid_diagnosis = generate_bid_diagnosis(client, selected_bid)

    else:
        st.warning("AI 관련 교육운영 공고를 찾지 못했습니다. 검색 기간이나 키워드를 넓혀보세요.")

except Exception as e:
    st.error(f"나라장터 공고 조회 중 에러 발생: {e}")

default_title = selected_bid["공고명"] if selected_bid else "AI 직무역량 강화 교육 운영 용역"
default_agency = selected_bid["공고기관"] if selected_bid else "예시기관"
default_bid_type = classify_bid_type(selected_bid)
default_diagnosis = st.session_state.bid_diagnosis if selected_bid else "공고를 선택하면 진단이 생성됩니다."

st.subheader("2. 공고 진단")
bid_title = st.text_input("공고명", default_title)
agency = st.text_input("기관명", default_agency)

st.write(f"공고 유형: {default_bid_type}")
st.info(default_diagnosis)

st.subheader("3. 내가 쓴 초안 입력")
draft_text = st.text_area(
    "초안 내용",
    height=250,
    value="""우리 회사는 AI 및 디지털 교육 운영 경험을 보유하고 있습니다.
체계적인 교육과정 설계와 운영을 통해 학습성과를 높이겠습니다.
전담 운영 인력과 강사진 관리 체계를 기반으로 안정적으로 운영하겠습니다."""
)

col1, col2 = st.columns(2)

with col1:
    if st.button("작성 가이드 생성"):
        with st.spinner("가이드 생성 중..."):
            try:
                result = generate_writing_guide(
                    client=client,
                    bid_title=bid_title,
                    agency=agency,
                    bid_type=default_bid_type,
                    diagnosis=default_diagnosis,
                )
                st.subheader("작성 가이드")
                st.write(result)
            except Exception as e:
                st.error(f"에러 발생: {e}")

with col2:
    if st.button("초안 피드백"):
        with st.spinner("피드백 생성 중..."):
            try:
                result = generate_draft_feedback(
                    client=client,
                    bid_title=bid_title,
                    agency=agency,
                    bid_type=default_bid_type,
                    diagnosis=default_diagnosis,
                    draft_text=draft_text,
                )
                st.subheader("초안 피드백")
                st.write(result)
            except Exception as e:
                st.error(f"에러 발생: {e}")