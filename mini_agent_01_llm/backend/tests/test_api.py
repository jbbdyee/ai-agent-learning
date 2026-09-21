import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Support running pytest from either the project root or the backend directory.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.providers import ProviderResult
from app.schemas import TravelImageAnalysis


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_health_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["stage"] == "mini_agent_01_llm"
    assert body["default_provider"]


def test_provider_list_does_not_expose_api_keys(client: TestClient) -> None:
    response = client.get("/api/providers")

    assert response.status_code == 200
    body = response.json()
    assert {item["provider"] for item in body["providers"]} == {
        "mock", "openai", "gemini", "ollama"
    }
    assert "api_key" not in response.text.lower()


def test_concept_compare_returns_both_decisions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routers.agent_router.compare_decisions",
        lambda message: {
            "message": message,
            "workflow": {"route": "general", "reason": "no rule", "confidence": 0.5},
            "semantic_router": {
                "route": "weather", "reason": "weather meaning", "confidence": 0.85
            },
            "note": "comparison",
        },
    )

    response = client.post("/api/concepts/compare", json={"message": "부산 날씨"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "부산 날씨"
    assert body["workflow"]["route"] == "general"
    assert body["semantic_router"]["route"] == "weather"


def test_travel_classifier_requests_missing_destination(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routers.agent_router.classify_travel_request",
        lambda _message: {
            "intent": "travel_plan",
            "reason": "destination is missing",
            "confidence": 0.87,
            "missing_information": ["destination"],
            "next_action": "ask_user",
            "follow_up_question": "어디로 여행하시나요?",
        },
    )

    response = client.post("/api/travel/classify", json={"message": "여행을 준비해 줘"})

    assert response.status_code == 200
    assert response.json()["missing_information"] == ["destination"]
    assert response.json()["next_action"] == "ask_user"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/concepts/compare", {"message": ""}),
        ("/api/travel/classify", {"message": ""}),
        ("/api/generate", {"provider": "unknown", "message": "hello"}),
        ("/api/providers/compare", {"providers": [], "message": "hello"}),
        ("/api/media/tts", {"text": "", "voice": "coral"}),
    ],
)
def test_invalid_requests_return_422(
    client: TestClient, path: str, payload: dict
) -> None:
    response = client.post(path, json=payload)

    assert response.status_code == 422
    assert response.json()["detail"]


def test_generate_returns_provider_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_generate(provider: str, system_prompt: str, message: str) -> ProviderResult:
        assert (provider, system_prompt, message) == (
            "mock", "Answer briefly.", "서울 여행지를 추천해 줘"
        )
        return ProviderResult("mock", "test-model", "남산을 추천합니다.", 12)

    monkeypatch.setattr("app.routers.agent_router.generate", fake_generate)
    response = client.post(
        "/api/generate",
        json={
            "provider": "mock",
            "system_prompt": "Answer briefly.",
            "message": "서울 여행지를 추천해 줘",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "provider": "mock", "model": "test-model",
        "content": "남산을 추천합니다.", "latency_ms": 12,
    }


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [(ValueError("provider is not configured"), 422), (RuntimeError("timeout"), 502)],
)
def test_generate_maps_provider_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
    exception: Exception, expected_status: int,
) -> None:
    def fail(*_args: object) -> ProviderResult:
        raise exception

    monkeypatch.setattr("app.routers.agent_router.generate", fail)
    response = client.post(
        "/api/generate", json={"provider": "openai", "message": "hello"}
    )

    assert response.status_code == expected_status
    assert str(exception) in response.json()["detail"]


def test_provider_compare_preserves_successes_and_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_generate(provider: str, *_args: str) -> ProviderResult:
        if provider == "openai":
            raise ValueError("missing key")
        return ProviderResult("mock", "test-model", "mock answer", 1)

    monkeypatch.setattr("app.routers.agent_router.generate", fake_generate)
    response = client.post(
        "/api/providers/compare",
        json={"providers": ["mock", "openai"], "message": "compare"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] == 2
    assert body["results"][0]["status"] == "success"
    assert body["results"][0]["content"] == "mock answer"
    assert body["results"][1]["status"] == "error"
    assert body["results"][1]["error"] == "missing key"


def test_image_analysis_returns_structured_result(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_analyze(content_type: str, content: bytes, question: str) -> TravelImageAnalysis:
        assert (content_type, content, question) == (
            "image/png", b"fake-image", "무엇이 보이나요?"
        )
        return TravelImageAnalysis(
            scene_type="landmark", summary="부산의 명소입니다.",
            travel_tips=["운영 시간을 확인하세요."],
        )

    monkeypatch.setattr("app.routers.media_router.analyze_image", fake_analyze)
    response = client.post(
        "/api/media/image-analysis",
        data={"question": "무엇이 보이나요?"},
        files={"image": ("travel.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["scene_type"] == "landmark"
    assert response.json()["visible_text"] == []


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [(ValueError("invalid image"), 422), (RuntimeError("service unavailable"), 502)],
)
def test_image_analysis_maps_service_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
    exception: Exception, expected_status: int,
) -> None:
    def fail(*_args: object) -> TravelImageAnalysis:
        raise exception

    monkeypatch.setattr("app.routers.media_router.analyze_image", fail)
    response = client.post(
        "/api/media/image-analysis",
        files={"image": ("travel.png", b"fake-image", "image/png")},
    )

    assert response.status_code == expected_status
    assert str(exception) in response.json()["detail"]


def test_tts_returns_mp3_with_synthetic_voice_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_create_speech(text: str, voice: str | None, instructions: str) -> bytes:
        assert (text, voice, instructions) == ("안녕하세요", "coral", "친절하게")
        return b"fake-mp3"

    monkeypatch.setattr("app.routers.media_router.create_speech", fake_create_speech)
    response = client.post(
        "/api/media/tts",
        json={"text": "안녕하세요", "voice": "coral", "instructions": "친절하게"},
    )

    assert response.status_code == 200
    assert response.content == b"fake-mp3"
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.headers["x-synthetic-voice"] == "true"


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [(ValueError("missing key"), 422), (RuntimeError("service unavailable"), 502)],
)
def test_tts_maps_service_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
    exception: Exception, expected_status: int,
) -> None:
    def fail(*_args: object) -> bytes:
        raise exception

    monkeypatch.setattr("app.routers.media_router.create_speech", fail)
    response = client.post("/api/media/tts", json={"text": "hello"})

    assert response.status_code == expected_status
    assert str(exception) in response.json()["detail"]