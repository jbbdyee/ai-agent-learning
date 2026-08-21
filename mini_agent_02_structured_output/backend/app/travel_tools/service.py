from time import perf_counter

from app.config import settings
from app.travel_tools.provider_service import run_tool_loop
from app.travel_tools.schemas import TravelPlanRequest, TravelPlanResponse, TravelRecommendationInput


class TravelProviderError(RuntimeError):
    """Raised when a configured LLM provider cannot produce a tool proposal."""


class TravelToolExecutionError(RuntimeError):
    """Raised when an allowed travel tool cannot be executed."""


def create_travel_plan(payload: TravelPlanRequest) -> TravelPlanResponse:
    """Run a Provider tool proposal through the shared safe Tool executor."""
    selected_provider = payload.provider or settings.llm_provider
    started = perf_counter()
    request = TravelRecommendationInput.model_validate(payload.model_dump(exclude={"provider"}))
    try:
        model, tool_calls, tool_results, answer = run_tool_loop(selected_provider, request)
    except Exception as error:
        raise TravelProviderError("여행 Provider의 Tool 제안 생성에 실패했습니다.") from error
    if not all(result.success for result in tool_results):
        raise TravelToolExecutionError("여행 추천 Tool 실행에 실패했습니다.")
    return TravelPlanResponse(
        provider=selected_provider, model=model, request=request,
        tool_calls=tool_calls, tool_results=tool_results, answer=answer,
        latency_ms=max(0, int((perf_counter() - started) * 1000)),
    )
