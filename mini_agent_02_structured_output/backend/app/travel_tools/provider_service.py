"""Provider Tool Call 제안과 공통 Allowlist 실행 흐름입니다."""

from typing import Any

import httpx

from app.config import settings
from app.travel_tools.executor import execute_tool_call
from app.travel_tools.schemas import ToolCall, ToolExecutionResult, TravelRecommendationInput


TOOL_NAMES = ("recommend_attractions", "recommend_restaurants")
SYSTEM_PROMPT = "여행 계획에 필요한 관광지와 맛집 조회 Tool을 각각 한 번씩 호출하세요. 사용자 입력값을 변경하지 마세요."


def _tools() -> list[dict[str, Any]]:
    schema = TravelRecommendationInput.model_json_schema()
    return [
        {"name": "recommend_attractions", "description": "관광지와 지도 좌표를 조회합니다.", "parameters": schema},
        {"name": "recommend_restaurants", "description": "맛집과 지도 좌표, 예상 가격을 조회합니다.", "parameters": schema},
    ]


def _input_text(request: TravelRecommendationInput) -> str:
    return f"여행 지역: {request.city}\n여행 일정: {request.check_in} ~ {request.check_out}\n여행 인원: {request.guests}명"


def _normalize(names: list[str], request: TravelRecommendationInput) -> list[ToolCall]:
    selected = []
    for name in names:
        if name in TOOL_NAMES and name not in selected:
            selected.append(name)
    for name in TOOL_NAMES:
        if name not in selected:
            selected.append(name)
    return [ToolCall(id=f"call_{name}_{index:03d}", name=name, arguments=request) for index, name in enumerate(selected[:2], 1)]


def _select_openai(request: TravelRecommendationInput) -> tuple[str, list[str]]:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    from openai import OpenAI

    response = OpenAI(api_key=settings.openai_api_key).chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _input_text(request)}],
        tools=[{"type": "function", "function": tool} for tool in _tools()],
        tool_choice="required",
    )
    calls = response.choices[0].message.tool_calls or []
    return settings.openai_model, [call.function.name for call in calls]


def _select_gemini(request: TravelRecommendationInput) -> tuple[str, list[str]]:
    if not settings.gemini_api_key or not settings.gemini_model:
        raise ValueError("GEMINI_API_KEY와 GEMINI_MODEL을 설정해야 합니다.")
    from google import genai
    from google.genai import types

    declarations = [types.FunctionDeclaration(name=tool["name"], description=tool["description"], parameters_json_schema=tool["parameters"]) for tool in _tools()]
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=_input_text(request),
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=[types.Tool(function_declarations=declarations)]),
    )
    return settings.gemini_model, [call.name for call in response.function_calls or []]


def _select_ollama(request: TravelRecommendationInput) -> tuple[str, list[str]]:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/chat",
        json={"model": settings.ollama_model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _input_text(request)}], "tools": [{"type": "function", "function": tool} for tool in _tools()], "stream": False},
        timeout=settings.request_timeout_seconds,
    )
    response.raise_for_status()
    calls = response.json().get("message", {}).get("tool_calls", [])
    return settings.ollama_model, [call.get("function", {}).get("name", "") for call in calls]


def create_provider_tool_calls(provider: str, request: TravelRecommendationInput) -> tuple[str, list[ToolCall]]:
    if provider == "mock":
        return "deterministic-travel-tool-mock", _normalize(list(TOOL_NAMES), request)
    selectors = {"openai": _select_openai, "gemini": _select_gemini, "ollama": _select_ollama}
    if provider not in selectors:
        raise ValueError("지원하지 않는 Provider입니다.")
    model, names = selectors[provider](request)
    return model, _normalize(names, request)


def run_tool_loop(provider: str, request: TravelRecommendationInput) -> tuple[str, list[ToolCall], list[ToolExecutionResult], str]:
    model, tool_calls = create_provider_tool_calls(provider, request)
    results = [execute_tool_call(tool_call) for tool_call in tool_calls]
    attraction_result = next((result for result in results if result.name == "recommend_attractions"), None)
    restaurant_result = next((result for result in results if result.name == "recommend_restaurants"), None)
    attractions = len(attraction_result.data.attractions) if attraction_result and attraction_result.success and attraction_result.data else 0
    restaurants = len(restaurant_result.data.restaurants) if restaurant_result and restaurant_result.success and restaurant_result.data else 0
    answer = f"{request.city} {request.guests}명 여행 일정에 맞춰 관광지 {attractions}곳과 맛집 {restaurants}곳을 추천했습니다. 지도에서 위치를 확인하세요."
    return model, tool_calls, results, answer
