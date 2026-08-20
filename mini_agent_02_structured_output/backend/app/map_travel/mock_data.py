import re
from typing import Any

from app.map_travel.schemas import MapTravelContent


CITY_DATA: dict[str, dict[str, list[dict[str, Any]]]] = {
    "부산": {
        "landmarks": [
            {
                "name": "해운대해수욕장",
                "description": "해변 산책과 바다 풍경을 즐길 수 있는 장소입니다.",
                "latitude": 35.1587,
                "longitude": 129.1604,
                "category": "beach",
            },
            {
                "name": "광안리해수욕장",
                "description": "광안대교 풍경으로 유명한 부산의 대표 해변입니다.",
                "latitude": 35.1532,
                "longitude": 129.1187,
                "category": "beach",
            },
        ],
        "foods": [
            {
                "name": "돼지국밥",
                "estimated_price_krw": 10000,
                "description": "부산을 대표하는 따뜻한 국밥입니다.",
                "latitude": 35.1631,
                "longitude": 129.1635,
            },
            {
                "name": "밀면",
                "estimated_price_krw": 9000,
                "description": "시원한 육수와 쫄깃한 면을 즐기는 부산 음식입니다.",
                "latitude": 35.1568,
                "longitude": 129.1208,
            },
        ],
    },
    "서울": {
        "landmarks": [
            {
                "name": "경복궁",
                "description": "조선 시대의 역사와 건축을 살펴볼 수 있는 궁궐입니다.",
                "latitude": 37.5796,
                "longitude": 126.9770,
                "category": "palace",
            }
        ],
        "foods": [
            {
                "name": "비빔밥",
                "estimated_price_krw": 12000,
                "description": "채소와 고추장을 함께 비벼 먹는 한식입니다.",
                "latitude": 37.5778,
                "longitude": 126.9769,
            }
        ],
    },
    "제주": {
        "landmarks": [
            {
                "name": "성산일출봉",
                "description": "제주의 동쪽 바다와 화산 지형을 볼 수 있는 장소입니다.",
                "latitude": 33.4580,
                "longitude": 126.9425,
                "category": "nature",
            }
        ],
        "foods": [
            {
                "name": "고기국수",
                "estimated_price_krw": 10000,
                "description": "돼지고기 육수와 면을 함께 즐기는 제주 음식입니다.",
                "latitude": 33.4591,
                "longitude": 126.9368,
            }
        ],
    },
    "강릉": {
        "landmarks": [
            {
                "name": "경포해변",
                "description": "동해 바다와 넓은 백사장을 즐길 수 있는 해변입니다.",
                "latitude": 37.8057,
                "longitude": 128.9070,
                "category": "beach",
            }
        ],
        "foods": [
            {
                "name": "초당순두부",
                "estimated_price_krw": 12000,
                "description": "부드러운 순두부를 맛보는 강릉의 대표 음식입니다.",
                "latitude": 37.7916,
                "longitude": 128.9147,
            }
        ],
    },
}

DURATION_PATTERN = re.compile(r"(\d+)\s*박\s*(\d+)\s*일")


def parse_duration(message: str) -> tuple[int, int, bool]:
    if "당일치기" in message or "당일 여행" in message:
        return 0, 1, False
    match = DURATION_PATTERN.search(message)
    if match:
        nights = int(match.group(1))
        return nights, nights + 1, False
    return 0, 1, True


def create_mock_map_travel(message: str) -> MapTravelContent:
    destination = next((city for city in CITY_DATA if city in message), "부산")
    nights, days, used_default = parse_duration(message)
    duration_label = "당일치기" if nights == 0 else f"{nights}박 {days}일"
    cautions = ["가격과 영업시간은 방문 전에 확인하세요."]
    if used_default:
        cautions.append("여행 기간이 없어 당일치기를 기본값으로 적용했습니다.")

    return MapTravelContent(
        destination=destination,
        nights=nights,
        days=days,
        summary=f"{destination}의 대표 장소와 음식을 즐기는 {duration_label} 여행입니다.",
        landmarks=CITY_DATA[destination]["landmarks"],
        foods=CITY_DATA[destination]["foods"],
        cautions=cautions,
    )

