from pydantic import ValidationError

from app.map_travel.prompt import build_map_travel_system_prompt, wrap_travel_request
from app.map_travel.schemas import MapTravelContent
from app.providers import ProviderResult, generate_structured


class MapTravelOutputValidationError(Exception):
    """Provider의 구조화 결과가 MapTravelContent 계약을 위반했습니다."""


class MapTravelProviderError(Exception):
    """Provider 인증, 연결 또는 호출에 실패했습니다."""


def generate_map_travel(provider: str, message: str) -> ProviderResult:
    try:
        result = generate_structured(
            provider,
            build_map_travel_system_prompt(),
            wrap_travel_request(message),
            "map_travel",
        )
        content = MapTravelContent.model_validate(result.content)
        return ProviderResult(
            provider=result.provider,
            model=result.model,
            content=content.model_dump(),
            latency_ms=result.latency_ms,
        )
    except ValidationError as error:
        raise MapTravelOutputValidationError(
            "Provider 응답이 지도 여행 Schema를 충족하지 않습니다."
        ) from error
    except MapTravelOutputValidationError:
        raise
    except Exception as error:
        raise MapTravelProviderError(str(error)) from error

