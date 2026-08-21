from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from clients.map_travel_client import generate_map_travel
from core.api_client import BackendAPIError
from core.kakao_map import build_kakao_map_url


st.title("🗺️ Kakao Map Travel")
st.caption("구조화된 여행 추천 결과를 카카오맵과 함께 확인합니다.")

provider = st.selectbox("Provider", ["mock", "gemini", "openai", "ollama"])
message = st.text_area(
    "여행 요청",
    "부산에 2박 3일 여행을 가고자 해. 관광지와 음식을 추천해 주세요.",
    max_chars=4000,
)
if provider in {"gemini", "openai"}:
    st.info("선택한 Provider는 Cloud API 호출 비용이 발생할 수 있습니다.")

if st.button("여행 추천 생성", type="primary", disabled=not message.strip()):
    try:
        with st.spinner("여행 추천을 생성하는 중입니다..."):
            st.session_state.map_travel_result = generate_map_travel(provider, message.strip())
    except BackendAPIError as error:
        st.error(str(error))

result: dict[str, Any] | None = st.session_state.get("map_travel_result")
if result:
    content = result.get("content", {})
    landmarks = content.get("landmarks", [])
    foods = content.get("foods", [])
    nights = content.get("nights", 0)
    days = content.get("days", 1)
    duration = "당일치기" if nights == 0 and days == 1 else f"{nights}박 {days}일"

    st.subheader(content.get("destination", "여행 추천"))
    st.caption(f"{result.get('provider', '')} · {result.get('model', '')} · {result.get('latency_ms', 0)} ms")
    st.metric("해석된 여행 기간", duration)
    st.write(content.get("summary", ""))

    st.subheader("카카오맵")
    components.iframe(build_kakao_map_url(landmarks, foods), height=460, scrolling=False)
    st.caption("파란 마커는 관광지, 주황 마커는 음식 추천입니다.")

    st.subheader("추천 관광지")
    if landmarks:
        for landmark in landmarks:
            with st.container(border=True):
                st.markdown(f"**{landmark.get('name', '이름 없음')}** · {landmark.get('category', '기타')}")
                st.write(landmark.get("description", "설명이 없습니다."))
    else:
        st.info("추천 관광지가 없습니다.")

    st.subheader("추천 음식")
    if foods:
        st.dataframe(
            [
                {
                    "음식": food.get("name", "이름 없음"),
                    "예상 가격": f"{int(food.get('estimated_price_krw', 0)):,}원",
                    "설명": food.get("description", "설명이 없습니다."),
                }
                for food in foods
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("추천 음식이 없습니다.")

    cautions = content.get("cautions", [])
    if cautions:
        st.warning("\n".join(f"- {caution}" for caution in cautions))
    st.caption("위치, 가격, 영업시간은 실제 방문 전에 다시 확인하세요.")

    with st.expander("구조화 JSON 보기"):
        st.json(content)
