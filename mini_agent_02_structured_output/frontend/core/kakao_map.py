import base64
import json
from typing import Any
from urllib.parse import urlencode

from core.api_client import BACKEND_URL


def build_kakao_map_url(landmarks: list[dict[str, Any]], foods: list[dict[str, Any]]) -> str:
    """Return the backend-hosted HTTPS map URL for Streamlit's iframe."""
    places = [
        place
        for place in [
            *(_to_place(item, "landmark") for item in landmarks),
            *(_to_place(item, "food") for item in foods),
        ]
        if place is not None
    ]
    payload = base64.urlsafe_b64encode(
        json.dumps(places, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return f"{BACKEND_URL}/api/structured/map-travel/map?{urlencode({'places': payload})}"


def _to_place(item: dict[str, Any], kind: str) -> dict[str, Any] | None:
    try:
        latitude = float(item["latitude"])
        longitude = float(item["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {
        "kind": kind,
        "name": str(item.get("name", "이름 없음")),
        "description": str(item.get("description", "설명이 없습니다.")),
        "latitude": latitude,
        "longitude": longitude,
    }
