from typing import Any

from core.api_client import request


def generate_map_travel(provider: str, message: str) -> dict[str, Any]:
    """Request map-ready travel recommendations from the backend."""
    return request(
        "POST",
        "/api/structured/map-travel",
        json={"provider": provider, "message": message},
    )
