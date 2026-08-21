from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.travel_tools.schemas import (
    AttractionRecommendationResult,
    RestaurantRecommendationResult,
    ToolCall,
    ToolExecutionResult,
    TravelPlanRequest,
)


def valid_request(**overrides):
    payload = {
        "provider": "mock",
        "city": "부산",
        "check_in": date.today() + timedelta(days=1),
        "check_out": date.today() + timedelta(days=3),
        "guests": 2,
    }
    payload.update(overrides)
    return payload


def attraction_result(**overrides):
    payload = {
        "attractions": [
            {
                "name": "해운대해수욕장",
                "description": "바다 산책을 즐길 수 있는 대표 관광지입니다.",
                "latitude": 35.1587,
                "longitude": 129.1604,
            }
        ]
    }
    payload.update(overrides)
    return payload


def restaurant_result(**overrides):
    payload = {
        "restaurants": [
            {
                "name": "부산 맛집",
                "description": "지역 음식을 맛볼 수 있습니다.",
                "latitude": 35.16,
                "longitude": 129.16,
                "estimated_price_krw": 15000,
            }
        ]
    }
    payload.update(overrides)
    return payload


def test_accepts_valid_request_and_optional_provider() -> None:
    request = TravelPlanRequest.model_validate(valid_request())
    without_provider = valid_request()
    without_provider.pop("provider")

    assert request.city == "부산"
    assert TravelPlanRequest.model_validate(without_provider).provider is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"check_in": date.today() - timedelta(days=1)},
        {"check_out": date.today() + timedelta(days=1)},
        {
            "check_in": date.today() + timedelta(days=2),
            "check_out": date.today() + timedelta(days=1),
        },
        {"guests": 0},
        {"guests": 11},
        {"city": "수원"},
        {"provider": "unknown"},
        {"extra": True},
    ],
)
def test_rejects_invalid_request(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        TravelPlanRequest.model_validate(valid_request(**overrides))


def test_rejects_unknown_tool_and_extra_arguments() -> None:
    arguments = valid_request()
    arguments.pop("provider")

    with pytest.raises(ValidationError):
        ToolCall(id="call-1", name="delete_booking", arguments=arguments)

    arguments["secret"] = "value"
    with pytest.raises(ValidationError):
        ToolCall(id="call-1", name="recommend_attractions", arguments=arguments)


@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", 91), ("latitude", -91), ("longitude", 181), ("longitude", -181)],
)
def test_rejects_invalid_attraction_coordinates(field: str, value: float) -> None:
    payload = attraction_result()
    payload["attractions"][0][field] = value
    with pytest.raises(ValidationError):
        AttractionRecommendationResult.model_validate(payload)


def test_rejects_negative_restaurant_price_and_extra_fields() -> None:
    payload = restaurant_result()
    payload["restaurants"][0]["estimated_price_krw"] = -1
    with pytest.raises(ValidationError):
        RestaurantRecommendationResult.model_validate(payload)

    payload = restaurant_result(extra=True)
    with pytest.raises(ValidationError):
        RestaurantRecommendationResult.model_validate(payload)


def test_tool_result_requires_consistent_success_payload() -> None:
    valid = ToolExecutionResult(
        tool_call_id="call-1",
        name="recommend_attractions",
        success=True,
        data=attraction_result(),
    )
    assert valid.success is True

    invalid_payloads = [
        {"success": True, "data": None},
        {"success": True, "data": attraction_result(), "error": "error"},
        {"success": False, "data": None, "error": None},
        {"success": False, "data": attraction_result(), "error": "error"},
    ]
    for payload in invalid_payloads:
        with pytest.raises(ValidationError):
            ToolExecutionResult(
                tool_call_id="call-1",
                name="recommend_attractions",
                **payload,
            )


def test_tool_result_name_matches_data_type() -> None:
    with pytest.raises(ValidationError, match="맛집 Tool 결과 타입"):
        ToolExecutionResult(
            tool_call_id="call-1",
            name="recommend_restaurants",
            success=True,
            data=attraction_result(),
        )
