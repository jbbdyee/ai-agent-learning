import base64
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.map_travel.provider_service import MapTravelProviderError
from app.providers import ProviderResult


client = TestClient(app)


def _map_places_payload() -> str:
    places = [
        {
            "kind": "landmark",
            "name": "해운대해수욕장",
            "description": "해변 산책",
            "latitude": 35.1587,
            "longitude": 129.1604,
        }
    ]
    return base64.urlsafe_b64encode(
        json.dumps(places, ensure_ascii=False).encode("utf-8")
    ).decode("ascii").rstrip("=")


def test_map_travel_mock_returns_contract() -> None:
    response = client.post(
        "/api/structured/map-travel",
        json={
            "provider": "mock",
            "message": "부산에 2박 3일 여행을 가고자 해. 관광지와 음식을 추천해 주세요.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["model"] == "deterministic-map-travel-mock"
    assert body["content"]["destination"] == "부산"
    assert (body["content"]["nights"], body["content"]["days"]) == (2, 3)
    assert body["content"]["landmarks"]
    assert body["content"]["foods"]
    assert "latitude" in body["content"]["foods"][0]
    assert "longitude" in body["content"]["foods"][0]


def test_provider_can_be_omitted(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.map_travel.service.settings",
        SimpleNamespace(llm_provider="mock"),
    )
    response = client.post(
        "/api/structured/map-travel",
        json={"message": "서울 당일치기 관광지와 음식을 추천해 주세요."},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert response.json()["content"]["nights"] == 0
    assert response.json()["content"]["days"] == 1


def test_invalid_requests_return_422() -> None:
    payloads = [
        {"provider": "mock", "message": ""},
        {"provider": "mock", "message": "   "},
        {"provider": "mock", "message": "가" * 4001},
        {"provider": "unknown", "message": "부산 당일치기"},
        {"provider": "mock", "message": "부산 당일치기", "extra": True},
    ]

    for payload in payloads:
        response = client.post("/api/structured/map-travel", json=payload)
        assert response.status_code == 422


def test_invalid_provider_output_returns_safe_422(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.map_travel.service.generate_map_travel",
        lambda *_: ProviderResult(
            provider="mock",
            model="broken-mock",
            content={"destination": "부산"},
            latency_ms=0,
        ),
    )

    response = client.post(
        "/api/structured/map-travel",
        json={"provider": "mock", "message": "부산 당일치기"},
    )

    assert response.status_code == 422
    assert "데이터 계약" in response.json()["detail"]


def test_provider_failure_returns_safe_502(monkeypatch) -> None:
    def fail_provider(*_):
        raise MapTravelProviderError("OPENAI_API_KEY=secret 내부 연결 오류")

    monkeypatch.setattr("app.map_travel.service.generate_map_travel", fail_provider)
    response = client.post(
        "/api/structured/map-travel",
        json={"provider": "openai", "message": "부산 당일치기"},
    )

    assert response.status_code == 502
    assert "secret" not in response.text
    assert "OPENAI_API_KEY" not in response.text
    assert "지도 여행 생성에 실패" in response.json()["detail"]


def test_openapi_exposes_map_travel_contract() -> None:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/structured/map-travel"]["post"]

    assert operation["tags"] == ["02 · Structured Output"]
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/MapTravelRequest")
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/MapTravelResponse")


def test_map_embed_is_served_as_html_from_backend_origin(monkeypatch) -> None:
    monkeypatch.setenv("KAKAO_MAP_JAVASCRIPT_KEY", "test-javascript-key")

    response = client.get(
        "/api/structured/map-travel/map", params={"places": _map_places_payload()}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "https://dapi.kakao.com/v2/maps/sdk.js?appkey=test-javascript-key" in response.text
    assert '"latitude": 35.1587' in response.text
    assert "new kakao.maps.LatLng(place.latitude, place.longitude)" in response.text


def test_map_embed_rejects_invalid_place_payload() -> None:
    response = client.get(
        "/api/structured/map-travel/map", params={"places": "not-valid-payload"}
    )

    assert response.status_code == 422


def test_existing_routes_remain_available() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/health" in paths
    assert "/api/structured/generate" in paths
    assert "/api/structured/compare" in paths

