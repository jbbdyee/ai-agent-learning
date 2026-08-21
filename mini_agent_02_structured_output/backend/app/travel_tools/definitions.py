from app.travel_tools.mock_data import CITY_DATA
from app.travel_tools.schemas import (
    AttractionRecommendationResult,
    RestaurantRecommendationResult,
    TravelRecommendationInput,
)


def recommend_attractions(
    arguments: TravelRecommendationInput,
) -> AttractionRecommendationResult:
    """검증된 지역 입력에 맞는 모의 관광지 데이터를 조회합니다."""
    return AttractionRecommendationResult(
        attractions=CITY_DATA[arguments.city]["attractions"],
    )


def recommend_restaurants(
    arguments: TravelRecommendationInput,
) -> RestaurantRecommendationResult:
    """검증된 지역 입력에 맞는 모의 맛집 데이터를 조회합니다."""
    return RestaurantRecommendationResult(
        restaurants=CITY_DATA[arguments.city]["restaurants"],
    )
