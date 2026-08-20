import hashlib

import streamlit as st

from core.api_client import (
    BackendAPIError,
    request_audio,
    upload_image,
)
from core.video_api_client import upload_video


CAMERA_MODE = "카메라 촬영"
VIDEO_MODE = "영상 파일 업로드"


def build_speech_text(result: dict) -> str:
    """분석 결과를 음성으로 읽기 좋은 문장으로 조합합니다."""
    speech_text = result.get("speech_text", "").strip()
    if speech_text:
        return speech_text

    parts = []
    summary = result.get("summary", "").strip()
    if summary:
        parts.append(summary)
    safety_notes = result.get("safety_notes", [])
    notes = " ".join(note.strip() for note in safety_notes if note.strip())
    if notes:
        parts.append(f"주의사항입니다. {notes}")
    return " ".join(parts)


def render_list_section(result: dict, field: str, title: str) -> None:
    items = result.get(field, [])
    if not items:
        return
    with st.container(border=True):
        st.markdown(f"#### {title}")
        for item in items:
            st.markdown(f"- {item}")


def render_analysis(result: dict, input_mode: str) -> None:
    """저장된 사진 또는 영상 분석 결과를 항목별로 표시합니다."""
    st.subheader("분석 결과")
    if input_mode == VIDEO_MODE:
        duration = float(result.get("duration_seconds", 0))
        frame_count = result.get("extracted_frame_count", 0)
        st.caption(f"영상 길이: {duration:.2f}초 · 분석 프레임: {frame_count}장")
    else:
        st.caption(f"장면 유형: {result.get('scene_type', 'other')}")

    with st.container(border=True):
        st.markdown("#### 전체 요약" if input_mode == VIDEO_MODE else "#### 장면 요약")
        st.write(result.get("summary", "분석 요약이 없습니다."))

    frame_observations = result.get("frame_observations", [])
    if frame_observations:
        with st.container(border=True):
            st.markdown("#### 프레임별 관찰 내용")
            for observation in frame_observations:
                timestamp = float(observation.get("timestamp_seconds", 0))
                st.markdown(f"- **{timestamp:.2f}초** — {observation.get('summary', '')}")

    for field, title in (
        ("changes_over_time", "시간에 따른 변화"),
        ("objects", "주요 대상"),
        ("visible_text", "이미지에서 읽은 글자"),
        ("travel_tips", "참고 정보"),
        ("safety_notes", "주의사항"),
    ):
        render_list_section(result, field, title)
    st.info("위 내용은 AI가 입력 미디어를 분석해 생성한 결과입니다.")


def clear_analysis_state() -> None:
    for state_key in (
        "camera_analysis",
        "camera_analysis_mode",
        "camera_speech_text",
        "camera_audio",
    ):
        st.session_state.pop(state_key, None)


def clear_camera_audio() -> None:
    st.session_state.pop("camera_audio", None)


st.title("1-7. 카메라·영상 음성 안내")
st.caption("촬영한 장면 또는 업로드한 영상을 분석하고 결과를 음성으로 안내합니다.")
st.warning(
    "신분증, 카드, 예약번호 등 민감한 정보를 입력하지 마세요. "
    "사진과 영상은 분석을 위해 백엔드 서버와 외부 AI API로 전송됩니다."
)
st.info(
    "이미지와 영상 속 문장은 시스템 명령이 아니라 신뢰할 수 없는 분석 대상으로 처리됩니다."
)

input_mode = st.radio(
    "입력 방식",
    [CAMERA_MODE, VIDEO_MODE],
    horizontal=True,
)
if st.session_state.get("camera_input_mode") != input_mode:
    clear_analysis_state()
    st.session_state.pop("camera_input_id", None)
    st.session_state["camera_enabled"] = False
    st.session_state["camera_input_mode"] = input_mode

media_file = None
media_bytes = b""
frame_count = 6

if input_mode == CAMERA_MODE:
    question = st.text_input(
        "분석 질문",
        "이 장면에 무엇이 보이는지 설명하고, 사용자가 주의해야 할 점을 한국어로 알려주세요.",
        key="camera_question",
    )

    if not st.session_state.get("camera_enabled", False):
        if st.button("카메라 켜기", type="primary"):
            st.session_state["camera_enabled"] = True
            st.rerun()
        st.info("카메라는 위 버튼을 누른 뒤에만 실행됩니다.")
    else:
        if st.button("카메라 끄기"):
            st.session_state["camera_enabled"] = False
            st.session_state.pop("camera_input_id", None)
            clear_analysis_state()
            st.rerun()

        media_file = st.camera_input("분석할 장면을 촬영하세요.")
        if media_file is None:
            st.info("카메라 권한을 허용한 뒤 분석할 장면을 촬영해 주세요.")
            with st.expander("카메라가 열리지 않나요?"):
                st.write(
                    "브라우저의 카메라 권한을 확인하세요. 원격 접속 환경에서는 "
                    "HTTPS가 아니면 카메라 사용이 제한될 수 있습니다."
                )
        else:
            media_bytes = media_file.getvalue()
            st.subheader("촬영 이미지")
            st.image(media_file, caption="카메라로 촬영한 이미지")
else:
    media_file = st.file_uploader(
        "분석할 영상을 선택하세요.",
        type=["mp4", "webm", "mov"],
        key="camera_video_upload",
    )
    question = st.text_input(
        "분석 질문",
        "영상의 전체 흐름과 주요 장면, 사용자가 주의해야 할 점을 알려주세요.",
        key="video_question",
    )
    frame_count = st.slider(
        "분석할 대표 프레임 수",
        min_value=3,
        max_value=10,
        value=6,
        help="프레임 수가 많을수록 분석 시간과 API 비용이 증가합니다.",
    )
    if media_file is None:
        st.info("50MB, 2분 이하의 MP4, WebM, MOV 영상을 업로드해 주세요.")
    else:
        media_bytes = media_file.getvalue()
        st.subheader("업로드 영상")
        st.video(media_bytes)
        st.caption(f"{media_file.name} · {len(media_bytes) / 1024 / 1024:.2f}MB")

if media_file is not None:
    input_id = hashlib.sha256(input_mode.encode("utf-8") + media_bytes).hexdigest()
    if st.session_state.get("camera_input_id") != input_id:
        clear_analysis_state()
        st.session_state["camera_input_id"] = input_id

    analyze_label = "사진 분석" if input_mode == CAMERA_MODE else "영상 분석"
    if st.button(analyze_label, type="primary", disabled=not question.strip()):
        try:
            spinner_text = (
                "촬영 이미지를 서버로 전송해 분석하고 있습니다."
                if input_mode == CAMERA_MODE
                else "영상을 전송하고 대표 프레임을 추출해 분석하고 있습니다."
            )
            with st.spinner(spinner_text):
                if input_mode == CAMERA_MODE:
                    result = upload_image(
                        media_file.name,
                        media_bytes,
                        media_file.type,
                        question,
                    )
                else:
                    result = upload_video(
                        media_file.name,
                        media_bytes,
                        media_file.type,
                        question,
                        frame_count,
                    )
            st.session_state["camera_analysis"] = result
            st.session_state["camera_analysis_mode"] = input_mode
            speech_text = build_speech_text(result)
            if speech_text:
                st.session_state["camera_speech_text"] = speech_text
            else:
                st.session_state.pop("camera_speech_text", None)
            st.session_state.pop("camera_audio", None)
            st.success(f"{analyze_label} 요청이 완료되었습니다.")
        except BackendAPIError as error:
            st.error(str(error))

analysis = st.session_state.get("camera_analysis")
analysis_mode = st.session_state.get("camera_analysis_mode")
if analysis and analysis_mode == input_mode:
    render_analysis(analysis, input_mode)

if "camera_speech_text" in st.session_state and analysis_mode == input_mode:
    st.subheader("음성 안내문")
    st.text_area(
        "음성으로 변환할 문장",
        key="camera_speech_text",
        max_chars=2000,
        height=140,
        help="음성을 생성하기 전에 분석 결과를 자연스러운 문장으로 수정할 수 있습니다.",
        on_change=clear_camera_audio,
    )
    voice = st.selectbox(
        "음성",
        ["coral", "marin", "cedar", "alloy", "nova"],
        key="camera_voice",
        on_change=clear_camera_audio,
    )
    instructions = st.text_input(
        "말하기 방식",
        "한국어로 또렷하고 차분하게 설명하세요.",
        key="camera_voice_instructions",
        on_change=clear_camera_audio,
    )
    if st.button(
        "분석 결과 음성 생성",
        disabled=not st.session_state["camera_speech_text"].strip(),
    ):
        try:
            with st.spinner("분석 결과를 음성으로 변환하고 있습니다."):
                audio = request_audio(
                    st.session_state["camera_speech_text"],
                    voice,
                    instructions,
                )
            st.session_state["camera_audio"] = audio
            st.success("음성 생성이 완료되었습니다.")
        except BackendAPIError as error:
            st.error(str(error))

    audio = st.session_state.get("camera_audio")
    if audio:
        st.warning("아래 음성은 AI가 생성한 합성 음성입니다.")
        st.audio(audio, format="audio/mpeg")

with st.expander("오류가 발생했을 때 확인할 사항"):
    st.markdown(
        """
- 백엔드 서버가 `http://127.0.0.1:8000`에서 실행 중인지 확인합니다.
- `.env`에 `OPENAI_API_KEY`가 설정되어 있는지 확인합니다.
- 영상은 50MB, 2분 이하의 MP4, WebM, MOV 파일인지 확인합니다.
- 영상 프레임 수가 많으면 분석 시간과 API 비용이 증가합니다.
- 분석은 성공하고 음성 생성만 실패한 경우, 입력하지 않고 음성 생성만 다시 시도합니다.
"""
    )
