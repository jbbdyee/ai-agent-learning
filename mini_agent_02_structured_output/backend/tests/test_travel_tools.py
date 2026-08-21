from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.travel_tools.executor import ToolNotAllowedError, execute_tool_call
from app.travel_tools.provider_service import run_tool_loop
from app.travel_tools.schemas import ToolCall, TravelRecommendationInput


def make_input() -> TravelRecommendationInput:
    return TravelRecommendationInput(
        city="부산",
        check_in=date.today() + timedelta(days=1),
        check_out=date.today() + timedelta(days=3),
        guests=2,
    )


def test_mock_tool_loop_returns_attractions_and_restaurants() -> None:
    _, calls, results, answer = run_tool_loop("mock", make_input())

    assert [call.name for call in calls] == ["recommend_attractions", "recommend_restaurants"]
    assert all(result.success for result in results)
    assert results[0].data is not None
    assert results[1].data is not None
    assert len(results[0].data.attractions) == 3
    assert len(results[1].data.restaurants) == 3
    assert "관광지" in answer and "맛집" in answer


def test_executor_rejects_extra_tool_arguments() -> None:
    with pytest.raises(ValidationError):
        ToolCall(
            id="call_invalid_001",
            name="recommend_attractions",
            arguments={**make_input().model_dump(mode="json"), "payment": True},
        )


def test_executor_rejects_disallowed_tool_name() -> None:
    class UnsafeToolCall:
        id = "call_unsafe_001"
        name = "delete_database"
        arguments = {}

    with pytest.raises(ToolNotAllowedError):
        execute_tool_call(UnsafeToolCall())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("check_in", "check_out", "guests"),
    [
        (date.today() + timedelta(days=1), date.today() + timedelta(days=1), 2),
        (date.today() + timedelta(days=3), date.today() + timedelta(days=1), 2),
        (date.today() + timedelta(days=1), date.today() + timedelta(days=3), 0),
        (date.today() + timedelta(days=1), date.today() + timedelta(days=3), 11),
    ],
)
def test_tool_input_validates_dates_and_guests(
    check_in: date, check_out: date, guests: int
) -> None:
    with pytest.raises(ValidationError):
        TravelRecommendationInput(
            city="부산", check_in=check_in, check_out=check_out, guests=guests
        )
