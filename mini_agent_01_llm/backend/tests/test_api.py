from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.config import settings
from app.schemas import TravelImageAnalysis, VideoAnalysis, VideoFrameObservation
from app.services.media_service import (
    _frame_positions,
    extract_video_frames,
    validate_image,
    validate_video,
)


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["stage"] == "mini_agent_01_llm"


def test_provider_list_does_not_expose_keys() -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    body = response.json()
    assert {item["provider"] for item in body["providers"]} == {
        "mock",
        "openai",
        "gemini",
        "ollama",
    }
    assert "api_key" not in response.text.lower()


def test_concept_compare_shows_rule_and_semantic_difference() -> None:
    response = client.post(
        "/api/concepts/compare",
        json={"message": "내일 비가 올까요?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["workflow"]["route"] == "general"
    assert body["semantic_router"]["route"] == "weather"


def test_travel_classifier_asks_for_missing_destination() -> None:
    response = client.post(
        "/api/travel/classify",
        json={"message": "여행을 준비해 줘."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "travel_plan"
    assert body["next_action"] == "ask_user"
    assert "destination" in body["missing_information"]


def test_low_confidence_requests_clarification() -> None:
    response = client.post(
        "/api/travel/classify",
        json={"message": "도와주세요."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "needs_clarification"
    assert body["next_action"] == "ask_user"


def test_mock_provider_generate() -> None:
    response = client.post(
        "/api/generate",
        json={"provider": "mock", "message": "부산 여행"},
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"


def test_provider_compare_preserves_each_result() -> None:
    response = client.post(
        "/api/providers/compare",
        json={"providers": ["mock"], "message": "부산 여행"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 1
    assert body["results"][0]["status"] == "success"


def test_missing_openai_key_is_explicit() -> None:
    response = client.post(
        "/api/generate",
        json={"provider": "openai", "message": "부산 여행을 추천해 주세요."},
    )
    if response.status_code == 200:
        return
    assert response.status_code == 422
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_image_analysis_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routers.media_router.analyze_image",
        lambda *_: TravelImageAnalysis(
            scene_type="landmark",
            summary="부산의 해변입니다.",
            travel_tips=["운영 시간을 확인하세요."],
        ),
    )
    response = client.post(
        "/api/media/image-analysis",
        files={"image": ("travel.png", b"fake", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["scene_type"] == "landmark"


def test_image_analysis_reports_validation_error(monkeypatch) -> None:
    def reject_image(*_) -> TravelImageAnalysis:
        raise ValueError("지원하지 않는 이미지입니다.")

    monkeypatch.setattr("app.routers.media_router.analyze_image", reject_image)
    response = client.post(
        "/api/media/image-analysis",
        files={"image": ("camera.jpg", b"invalid", "image/jpeg")},
    )
    assert response.status_code == 422
    assert "지원하지 않는 이미지" in response.json()["detail"]


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("image/jpeg", b"\xff\xd8\xffcamera"),
        ("image/png", b"\x89PNG\r\n\x1a\ncamera"),
        ("image/gif", b"GIF89acamera"),
        ("image/webp", b"RIFF\x00\x00\x00\x00WEBPcamera"),
    ],
)
def test_image_validation_accepts_supported_signatures(
    content_type: str,
    content: bytes,
) -> None:
    validate_image(content_type, content)


def test_image_validation_rejects_empty_or_mismatched_content() -> None:
    with pytest.raises(ValueError, match="빈 이미지"):
        validate_image("image/jpeg", b"")
    with pytest.raises(ValueError, match="일치하지 않습니다"):
        validate_image("image/jpeg", b"not-a-jpeg")
    with pytest.raises(ValueError, match="이미지만"):
        validate_image("text/plain", b"plain text")


def test_image_validation_rejects_oversized_image() -> None:
    oversized = b"\xff\xd8\xff" + b"0" * (settings.max_image_size_mb * 1024 * 1024)
    with pytest.raises(ValueError, match="이하여야"):
        validate_image("image/jpeg", oversized)


def test_video_analysis_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routers.media_router.analyze_video",
        lambda *_: (
            VideoAnalysis(
                summary="사람이 방 안을 이동합니다.",
                objects=["사람", "의자"],
                frame_observations=[
                    VideoFrameObservation(timestamp_seconds=1.5, summary="사람이 보입니다.")
                ],
                changes_over_time=["사람의 위치가 달라집니다."],
                speech_text="사람이 방 안을 이동하고 있습니다.",
            ),
            6,
            12.0,
        ),
    )
    response = client.post(
        "/api/media/video-analysis",
        files={"video": ("camera.mp4", b"fake", "video/mp4")},
        data={"question": "무엇이 보이나요?", "frame_count": "6"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["extracted_frame_count"] == 6
    assert body["duration_seconds"] == 12.0
    assert body["frame_observations"][0]["timestamp_seconds"] == 1.5


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("video/mp4", b"\x00\x00\x00\x18ftypisomvideo"),
        ("video/quicktime", b"\x00\x00\x00\x14ftypqt  video"),
        ("video/webm", b"\x1aE\xdf\xa3video"),
    ],
)
def test_video_validation_accepts_supported_signatures(
    content_type: str,
    content: bytes,
) -> None:
    validate_video(content_type, content)


def test_video_validation_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="빈 영상"):
        validate_video("video/mp4", b"")
    with pytest.raises(ValueError, match="일치하지 않습니다"):
        validate_video("video/mp4", b"not-a-video")
    with pytest.raises(ValueError, match="영상만"):
        validate_video("application/octet-stream", b"data")


def test_video_frame_positions_are_even_and_unique() -> None:
    positions = _frame_positions(total_frames=100, requested_count=6)
    assert len(positions) == 6
    assert positions == sorted(set(positions))
    assert positions[0] == 5
    assert positions[-1] == 94


def test_short_video_does_not_duplicate_frame_positions() -> None:
    positions = _frame_positions(total_frames=3, requested_count=6)
    assert positions == sorted(set(positions))
    assert len(positions) <= 3


def test_video_frame_count_must_stay_in_allowed_range() -> None:
    with pytest.raises(ValueError, match="대표 프레임 수"):
        _frame_positions(total_frames=100, requested_count=2)


def test_extract_video_frames_and_remove_temporary_file(tmp_path, monkeypatch) -> None:
    cv2 = pytest.importorskip("cv2")
    numpy = pytest.importorskip("numpy")
    source_path = tmp_path / "source.mp4"
    writer = cv2.VideoWriter(
        str(source_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (64, 48),
    )
    if not writer.isOpened():
        pytest.skip("테스트 환경에서 MP4 인코더를 사용할 수 없습니다.")
    for index in range(30):
        frame = numpy.full((48, 64, 3), index * 8, dtype=numpy.uint8)
        writer.write(frame)
    writer.release()

    monkeypatch.setattr("app.services.media_service.tempfile.tempdir", str(tmp_path))
    existing_files = {path.name for path in tmp_path.iterdir()}
    frames, duration = extract_video_frames(
        "video/mp4",
        source_path.read_bytes(),
        requested_count=3,
    )

    assert len(frames) == 3
    assert duration == pytest.approx(3.0)
    assert [frame.timestamp_seconds for frame in frames] == sorted(
        frame.timestamp_seconds for frame in frames
    )
    assert {path.name for path in tmp_path.iterdir()} == existing_files


def test_tts_marks_synthetic_audio(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.media_router.create_speech", lambda *_: b"mp3")
    response = client.post("/api/media/tts", json={"text": "안녕하세요.", "voice": "coral"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["x-synthetic-voice"] == "true"
