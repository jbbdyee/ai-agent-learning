from datetime import date, timedelta
from typing import cast

import streamlit as st
import streamlit.components.v1 as components

from clients.travel_tool_client import create_travel_plan
from core.api_client import BackendAPIError
from core.travel_kakao_map import (
    build_travel_kakao_map_url,
    extract_travel_places,
)
from core.travel_tool_types import TravelPlanResponse


CITIES = ["서울", "부산", "제주", "강릉", "인천", "대전", "대구", "광주", "전주", "경주"]
PROVIDERS = ["mock", "gemini", "openai", "ollama"]
RESULT_STATE_KEY = "travel_tool_use_result"


def validate_inputs(check_in: date, check_out: date, guests: int) -> list[str]:
    errors: list[str] = []
    if check_in <= date.today():
        errors.append("여행 시작일은 오늘 이후여야 합니다.")
    if check_out <= check_in:
        errors.append("여행 종료일은 시작일 이후여야 합니다.")
    if not 1 <= guests <= 10:
        errors.append("여행 인원은 1명부터 10명까지 선택할 수 있습니다.")
    return errors


def user_error_message(error: BackendAPIError) -> str:
    message = str(error)
    if "(422)" in message:
        return f"입력값을 확인해 주세요. {message}"
    if "(502)" in message:
        return f"Provider 호출에 실패했습니다. 잠시 후 다시 시도해 주세요. {message}"
    if "(503)" in message:
        return f"여행 정보 조회에 실패했습니다. 잠시 후 다시 시도해 주세요. {message}"
    return message

mock_response: TravelPlanResponse = {
    "provider": "mock",
    "model": "deterministic-travel-tool-mock",
    "request": {
        "city": "부산",
        "check_in": "2026-08-25",
        "check_out": "2026-08-27",
        "guests": 2,
    },
    "tool_calls": [
        {
            "id": "call_attraction_001",
            "name": "recommend_attractions",
            "arguments": {
                "city": "부산",
                "check_in": "2026-08-25",
                "check_out": "2026-08-27",
                "guests": 2,
            },
        },
        {
            "id": "call_restaurant_001",
            "name": "recommend_restaurants",
            "arguments": {
                "city": "부산",
                "check_in": "2026-08-25",
                "check_out": "2026-08-27",
                "guests": 2,
            },
        },
    ],
    "tool_results": [
        {
            "tool_call_id": "call_attraction_001",
            "name": "recommend_attractions",
            "success": True,
            "data": {
                "attractions": [
                    {
                        "name": "해운대해수욕장",
                        "description": "해변 산책과 바다 풍경을 즐길 수 있습니다.",
                        "latitude": 35.1587,
                        "longitude": 129.1604,
                    }
                ]
            },
        },
        {
            "tool_call_id": "call_restaurant_001",
            "name": "recommend_restaurants",
            "success": True,
            "data": {
                "restaurants": [
                    {
                        "name": "해운대 돼지국밥",
                        "description": "부산식 돼지국밥을 즐길 수 있습니다.",
                        "latitude": 35.1631,
                        "longitude": 129.1635,
                        "estimated_price_krw": 10000,
                    }
                ]
            },
        },
    ],
    "answer": "부산 2명 여행에 맞는 관광지와 맛집을 추천했습니다.",
    "latency_ms": 0,
}


st.title("🧭 여행 계획 Tool Use")
st.caption("관광지·맛집 추천 Tool 실행 결과를 지도에서 확인합니다.")

today = date.today()
default_check_in = today + timedelta(days=1)
default_check_out = default_check_in + timedelta(days=2)

provider = st.selectbox("Provider", PROVIDERS, index=0)
city = st.selectbox("여행 지역", CITIES, index=0)

date_column, guest_column = st.columns(2)
with date_column:
    check_in = st.date_input(
        "여행 시작일",
        value=default_check_in,
        min_value=default_check_in,
    )
    check_out = st.date_input(
        "여행 종료일",
        value=default_check_out,
        min_value=default_check_in,
    )
with guest_column:
    guests = int(
        st.number_input(
            "여행 인원",
            min_value=1,
            max_value=10,
            value=2,
            step=1,
        )
    )

if provider in {"gemini", "openai"}:
    st.info("선택한 Provider는 Cloud API 호출 비용이 발생할 수 있습니다.")

validation_errors = validate_inputs(check_in, check_out, guests)
for validation_error in validation_errors:
    st.warning(validation_error)

if st.button(
    "계획 생성",
    type="primary",
    disabled=bool(validation_errors),
    use_container_width=True,
):
    try:
        with st.spinner("여행 계획을 생성하는 중입니다..."):
            api_response = create_travel_plan(
                provider=provider,
                city=city,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
            )
        st.session_state[RESULT_STATE_KEY] = api_response
        st.success("여행 계획 응답을 받았습니다.")
    except BackendAPIError as error:
        st.session_state.pop(RESULT_STATE_KEY, None)
        st.error(user_error_message(error))

result = cast(
    TravelPlanResponse,
    st.session_state.get(RESULT_STATE_KEY, mock_response),
)
request = result["request"]

request_columns = st.columns(4)
request_columns[0].metric("여행 지역", request["city"])
request_columns[1].metric("여행 일정", f'{request["check_in"]} ~ {request["check_out"]}')
request_columns[2].metric("여행 인원", f'{request["guests"]}명')
request_columns[3].metric("실행 Tool", f'{len(result["tool_calls"])}개')

st.subheader("여행 계획")
st.write(result["answer"])
st.caption(
    f'{result["provider"]} · {result["model"]} · {result["latency_ms"]} ms'
)

attractions, restaurants = extract_travel_places(result)

st.subheader("카카오맵")
if attractions or restaurants:
    components.iframe(
        build_travel_kakao_map_url(result),
        height=460,
        scrolling=False,
    )
    st.caption("파란 마커는 관광지, 주황 마커는 맛집입니다.")
else:
    st.info("지도에 표시할 추천 장소가 없습니다.")

st.subheader("추천 관광지")
if attractions:
    for attraction in attractions:
        with st.container(border=True):
            st.markdown(f'**{attraction["name"]}**')
            st.write(attraction["description"])
            st.caption(
                f'위도 {attraction["latitude"]:.4f} · '
                f'경도 {attraction["longitude"]:.4f}'
            )
else:
    st.info("추천 관광지가 없습니다.")

st.subheader("추천 맛집")
if restaurants:
    for restaurant in restaurants:
        with st.container(border=True):
            st.markdown(f'**{restaurant["name"]}**')
            st.write(restaurant["description"])
            st.caption(
                f'예상 가격 {restaurant["estimated_price_krw"]:,}원 · '
                f'위도 {restaurant["latitude"]:.4f} · '
                f'경도 {restaurant["longitude"]:.4f}'
            )
else:
    st.info("추천 맛집이 없습니다.")

st.caption("위치, 가격, 영업시간은 실제 방문 전에 다시 확인하세요.")

st.subheader("실행 Trace")
for tool_call in result["tool_calls"]:
    matching_result = next(
        (
            tool_result
            for tool_result in result["tool_results"]
            if tool_result["tool_call_id"] == tool_call["id"]
        ),
        None,
    )
    status = "성공" if matching_result and matching_result["success"] else "실패"
    with st.expander(f'{tool_call["name"]} · {status}', expanded=False):
        st.caption(f'Call ID: {tool_call["id"]}')
        st.markdown("**Tool arguments**")
        st.json(tool_call["arguments"])
        st.markdown("**Tool result**")
        st.json(matching_result or {"success": False, "data": {}})

with st.expander("전체 API 응답 JSON", expanded=False):
    st.json(result)
