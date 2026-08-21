from datetime import date, timedelta
from typing import get_type_hints

from fastapi.testclient import TestClient

from app.main import app
from app.routers.travel_tool_router import create_travel_plan, travel_tool_router
from app.travel_tools import service
from app.travel_tools.schemas import TravelPlanResponse


client = TestClient(app)


def request_payload() -> dict:
    return {
        "provider": "mock",
        "city": "부산",
        "check_in": (date.today() + timedelta(days=1)).isoformat(),
        "check_out": (date.today() + timedelta(days=3)).isoformat(),
        "guests": 2,
    }


def response_model() -> TravelPlanResponse:
    payload = request_payload()
    return TravelPlanResponse.model_validate(
        {
            "provider": "mock",
            "model": "deterministic-travel-tool-mock",
            "request": {
                "city": payload["city"],
                "check_in": payload["check_in"],
                "check_out": payload["check_out"],
                "guests": payload["guests"],
            },
            "tool_calls": [],
            "tool_results": [],
            "answer": "부산 여행 정보를 확인했습니다.",
            "latency_ms": 0,
        }
    )


def test_travel_plan_returns_response_contract(monkeypatch) -> None:
    monkeypatch.setattr(service, "create_travel_plan", lambda _: response_model())

    response = client.post("/api/tools/travel-plan", json=request_payload())

    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert response.json()["request"]["city"] == "부산"


def test_invalid_requests_return_422() -> None:
    invalid_payloads = [
        {**request_payload(), "guests": 0},
        {**request_payload(), "guests": 11},
        {**request_payload(), "city": "수원"},
        {**request_payload(), "extra": True},
        {
            **request_payload(),
            "check_out": request_payload()["check_in"],
        },
    ]

    for payload in invalid_payloads:
        assert client.post("/api/tools/travel-plan", json=payload).status_code == 422


def test_provider_failure_returns_safe_502(monkeypatch) -> None:
    def fail_provider(_):
        raise service.TravelProviderError("OPENAI_API_KEY=secret provider detail")

    monkeypatch.setattr(service, "create_travel_plan", fail_provider)
    response = client.post("/api/tools/travel-plan", json=request_payload())

    assert response.status_code == 502
    assert "secret" not in response.text
    assert "OPENAI_API_KEY" not in response.text


def test_tool_failure_returns_safe_503(monkeypatch) -> None:
    def fail_tool(_):
        raise service.TravelToolExecutionError("internal tool stack secret")

    monkeypatch.setattr(service, "create_travel_plan", fail_tool)
    response = client.post("/api/tools/travel-plan", json=request_payload())

    assert response.status_code == 503
    assert "secret" not in response.text
    assert "다시 시도" in response.json()["detail"]


def test_router_declares_response_model_and_return_type() -> None:
    route = next(
        route
        for route in travel_tool_router.routes
        if getattr(route, "path", None) == "/api/tools/travel-plan"
    )

    assert route.response_model is TravelPlanResponse
    assert get_type_hints(create_travel_plan)["return"] is TravelPlanResponse


def test_openapi_exposes_travel_tool_contract() -> None:
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/api/tools/travel-plan"]["post"]
    schemas = openapi["components"]["schemas"]

    assert operation["tags"] == ["02 · Tool Use"]
    assert operation["requestBody"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/TravelPlanRequest")
    assert operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/TravelPlanResponse")
    assert schemas["TravelPlanParameters"]["properties"]["guests"]["minimum"] == 1
    assert schemas["TravelPlanParameters"]["properties"]["guests"]["maximum"] == 10
    assert len(schemas["TravelPlanParameters"]["properties"]["city"]["enum"]) == 10


def test_existing_map_travel_route_remains_available() -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/structured/map-travel" in paths
