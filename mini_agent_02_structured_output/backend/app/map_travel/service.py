from app.config import settings
from app.map_travel.provider_service import generate_map_travel
from app.map_travel.schemas import MapTravelRequest, MapTravelResponse


def create_map_travel(payload: MapTravelRequest) -> MapTravelResponse:
    selected_provider = payload.provider or settings.llm_provider
    result = generate_map_travel(selected_provider, payload.message)
    return MapTravelResponse.model_validate(
        {
            "provider": result.provider,
            "model": result.model,
            "content": result.content,
            "latency_ms": result.latency_ms,
        }
    )

