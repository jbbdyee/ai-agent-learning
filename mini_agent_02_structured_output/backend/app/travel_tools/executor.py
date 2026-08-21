from collections.abc import Callable

from pydantic import ValidationError

from app.travel_tools.definitions import recommend_attractions, recommend_restaurants
from app.travel_tools.schemas import (
    AttractionRecommendationResult,
    RestaurantRecommendationResult,
    ToolCall,
    ToolExecutionResult,
    TravelRecommendationInput,
)


ToolFunction = Callable[[TravelRecommendationInput], AttractionRecommendationResult | RestaurantRecommendationResult]
TOOLS: dict[str, ToolFunction] = {
    "recommend_attractions": recommend_attractions,
    "recommend_restaurants": recommend_restaurants,
}


class ToolNotAllowedError(Exception):
    """Allowlist에 없는 Tool 실행 요청입니다."""


def execute_tool_call(tool_call: ToolCall) -> ToolExecutionResult:
    """Allowlist와 Pydantic 검증을 통과한 Tool Call만 실행합니다."""
    tool = TOOLS.get(tool_call.name)
    if tool is None:
        raise ToolNotAllowedError(f"허용되지 않은 Tool입니다: {tool_call.name}")

    try:
        arguments = TravelRecommendationInput.model_validate(tool_call.arguments)
    except ValidationError as error:
        return ToolExecutionResult(
            tool_call_id=tool_call.id,
            name=tool_call.name,
            success=False,
            error=str(error.errors()[0]["msg"]),
        )

    return ToolExecutionResult(
        tool_call_id=tool_call.id,
        name=tool_call.name,
        success=True,
        data=tool(arguments),
    )
