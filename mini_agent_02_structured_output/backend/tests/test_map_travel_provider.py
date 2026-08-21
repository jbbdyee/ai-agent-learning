import pytest

from app.map_travel.mock_data import create_mock_map_travel
from app.map_travel.provider_service import generate_map_travel
from app.map_travel.schemas import MapTravelContent
from app.providers import generate_structured


def test_mock_returns_deterministic_busan_content() -> None:
    first = generate_map_travel("mock", "부산에 2박 3일 여행을 가고자 해")
    second = generate_map_travel("mock", "부산에 2박 3일 여행을 가고자 해")

    assert first.model == "deterministic-map-travel-mock"
    assert first.content == second.content
    assert first.content["destination"] == "부산"
    assert (first.content["nights"], first.content["days"]) == (2, 3)
    assert MapTravelContent.model_validate(first.content)


def test_mock_parses_day_trip() -> None:
    content = create_mock_map_travel("서울 당일치기 여행")
    assert content.destination == "서울"
    assert (content.nights, content.days) == (0, 1)


def test_mock_normalizes_n_nights_m_days() -> None:
    content = create_mock_map_travel("제주 2박 4일 여행")
    assert (content.nights, content.days) == (2, 3)


def test_mock_uses_day_trip_default_and_adds_caution() -> None:
    content = create_mock_map_travel("강릉 여행을 추천해 주세요")
    assert (content.nights, content.days) == (0, 1)
    assert any("기본값" in caution for caution in content.cautions)


def test_existing_structured_mocks_still_work() -> None:
    travel = generate_structured("mock", "system", "제주 여행", "travel_plan")
    ticket = generate_structured("mock", "system", "결제가 두 번 됐어요", "support_ticket")

    assert travel.content["destination"] == "제주"
    assert ticket.content["category"] == "billing"


def test_unknown_provider_is_exposed_as_provider_error() -> None:
    from app.map_travel.provider_service import MapTravelProviderError

    with pytest.raises(MapTravelProviderError):
        generate_map_travel("unknown", "부산 당일치기")

