"""MCP Tool의 입력 검증 계약을 확인하는 회귀 테스트입니다."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp_server.business_tools_server import (  # noqa: E402
    check_restaurant_open,
    search_indoor_places,
    search_outdoor_places,
    search_product,
    search_restaurants,
)


def test_blank_city_is_rejected() -> None:
    for search_places in (search_indoor_places, search_outdoor_places):
        result = search_places("   ")

        assert result["success"] is False
        assert result["error"] == "INVALID_CITY"


def test_blank_product_query_is_rejected() -> None:
    result = search_product("   ")

    assert result["success"] is False
    assert result["error"] == "INVALID_QUERY"
    assert result["items"] == []


def test_restaurant_search_and_open_status() -> None:
    search_result = search_restaurants(" 서울 ", " 한식 ")

    assert search_result["success"] is True
    assert search_result["items"][0]["restaurant_id"] == "R-SEOUL-KOREAN"

    status_result = check_restaurant_open(" r-seoul-korean ")

    assert status_result["success"] is True
    assert status_result["is_open"] is True


def test_restaurant_search_requires_city_and_cuisine() -> None:
    result = search_restaurants("   ", "한식")

    assert result["success"] is False
    assert result["error"] == "INVALID_SEARCH_CONDITION"
    assert result["items"] == []
