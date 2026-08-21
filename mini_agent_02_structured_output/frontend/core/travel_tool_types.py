from typing import Any, Literal, TypedDict


ToolName = Literal["recommend_attractions", "recommend_restaurants"]


class TravelRequest(TypedDict):
    city: str
    check_in: str  # "YYYY-MM-DD"
    check_out: str  # "YYYY-MM-DD"
    guests: int


class ToolCall(TypedDict):
    id: str
    name: ToolName
    arguments: TravelRequest


class Attraction(TypedDict):
    name: str
    description: str
    latitude: float
    longitude: float


class Restaurant(TypedDict):
    name: str
    description: str
    latitude: float
    longitude: float
    estimated_price_krw: int


class ToolExecutionResult(TypedDict):
    tool_call_id: str
    name: ToolName
    success: bool
    data: dict[str, list[Attraction] | list[Restaurant]]


class TravelPlanResponse(TypedDict):
    provider: Literal["mock", "gemini", "openai", "ollama"]
    model: str
    request: TravelRequest
    tool_calls: list[ToolCall]
    tool_results: list[ToolExecutionResult]
    answer: str
    latency_ms: int