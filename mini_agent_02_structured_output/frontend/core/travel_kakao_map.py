from typing import Any

from core.kakao_map import build_kakao_map_url
from core.travel_tool_types import TravelPlanResponse


def extract_travel_places(
    result: TravelPlanResponse,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Tool 결과에서 지도용 관광지와 맛집 목록을 분리합니다."""
    attractions: list[dict[str, Any]] = []
    restaurants: list[dict[str, Any]] = []

    for tool_result in result["tool_results"]:
        if not tool_result["success"]:
            continue

        data = tool_result["data"]

        if tool_result["name"] == "recommend_attractions":
            attractions.extend(data.get("attractions", []))

        if tool_result["name"] == "recommend_restaurants":
            restaurants.extend(data.get("restaurants", []))

    return attractions, restaurants


def build_travel_kakao_map_url(result: TravelPlanResponse) -> str:
    """2-5 Tool Use 응답을 기존 카카오맵 iframe URL로 변환합니다."""
    attractions, restaurants = extract_travel_places(result)
    return build_kakao_map_url(attractions, restaurants)