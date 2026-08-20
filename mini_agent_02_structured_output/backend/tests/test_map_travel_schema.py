import pytest
from pydantic import ValidationError

from app.map_travel.schemas import MapTravelContent, MapTravelRequest


def valid_content(**overrides):
    payload = {
        "destination": "부산",
        "nights": 2,
        "days": 3,
        "summary": "부산 2박 3일 여행",
        "landmarks": [
            {
                "name": "해운대해수욕장",
                "description": "부산의 대표 해변",
                "latitude": 35.1587,
                "longitude": 129.1604,
                "category": "beach",
            }
        ],
        "foods": [
            {
                "name": "돼지국밥",
                "estimated_price_krw": 10000,
                "description": "부산의 대표 음식",
                "latitude": 35.1631,
                "longitude": 129.1635,
            }
        ],
        "cautions": ["방문 전 정보를 확인하세요."],
    }
    payload.update(overrides)
    return payload


def test_accepts_day_trip_and_two_nights_three_days() -> None:
    day_trip = MapTravelContent.model_validate(
        valid_content(nights=0, days=1, summary="부산 당일치기 여행")
    )
    overnight = MapTravelContent.model_validate(valid_content())

    assert (day_trip.nights, day_trip.days) == (0, 1)
    assert (overnight.nights, overnight.days) == (2, 3)


def test_rejects_invalid_duration_relation() -> None:
    with pytest.raises(ValidationError, match=r"days == nights \+ 1"):
        MapTravelContent.model_validate(valid_content(nights=2, days=4))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("landmarks", []),
        ("landmarks", valid_content()["landmarks"] * 11),
        ("foods", valid_content()["foods"] * 11),
    ],
)
def test_rejects_invalid_collection_sizes(field: str, value: list) -> None:
    with pytest.raises(ValidationError):
        MapTravelContent.model_validate(valid_content(**{field: value}))


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("landmarks", "latitude", 91),
        ("landmarks", "longitude", -181),
        ("foods", "latitude", -91),
        ("foods", "longitude", 181),
        ("foods", "estimated_price_krw", -1),
    ],
)
def test_rejects_invalid_coordinates_and_price(
    collection: str, field: str, value: int
) -> None:
    payload = valid_content()
    payload[collection][0][field] = value
    with pytest.raises(ValidationError):
        MapTravelContent.model_validate(payload)


def test_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        MapTravelContent.model_validate(valid_content(password="secret"))


def test_request_trims_message_and_rejects_blank_or_too_long() -> None:
    request = MapTravelRequest(message="  부산 당일치기  ")
    assert request.message == "부산 당일치기"

    with pytest.raises(ValidationError):
        MapTravelRequest(message="   ")
    with pytest.raises(ValidationError):
        MapTravelRequest(message="가" * 4001)
