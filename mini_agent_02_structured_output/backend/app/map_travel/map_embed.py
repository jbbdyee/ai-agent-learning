import base64
import html
import json
import os
from typing import Any
from urllib.parse import quote


def decode_places(encoded_places: str) -> list[dict[str, Any]]:
    """Decode the URL-safe map payload and retain only valid map coordinates."""
    try:
        padding = "=" * (-len(encoded_places) % 4)
        raw_places = json.loads(
            base64.urlsafe_b64decode(encoded_places + padding).decode("utf-8")
        )
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("지도 장소 데이터가 올바르지 않습니다.") from error

    if not isinstance(raw_places, list) or len(raw_places) > 20:
        raise ValueError("지도 장소 데이터가 올바르지 않습니다.")

    places = [place for item in raw_places if (place := _to_place(item)) is not None]
    if not places:
        raise ValueError("지도에 표시할 유효한 좌표가 없습니다.")
    return places


def build_map_html(places: list[dict[str, Any]]) -> str:
    """Build a Kakao Maps page served from the backend's HTTPS origin."""
    app_key = os.getenv("KAKAO_MAP_JAVASCRIPT_KEY", "").strip()
    if not app_key:
        return _message_html("카카오맵 JavaScript 키가 서버에 설정되지 않았습니다.")

    places_json = json.dumps(places, ensure_ascii=False).replace("</", "<\\/")
    sdk_url = "https://dapi.kakao.com/v2/maps/sdk.js?appkey=" + quote(app_key, safe="")
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .map-error {{ align-items: center; background: #fff4f4; color: #a61b1b; display: flex; font-family: sans-serif; height: 100%; justify-content: center; padding: 1rem; text-align: center; }}
    .info-window {{ font-family: sans-serif; line-height: 1.4; max-width: 240px; padding: 8px 10px; }}
    .info-window strong {{ display: block; margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="{html.escape(sdk_url, quote=True)}"></script>
  <script>
    const places = {places_json};
    const mapElement = document.getElementById('map');
    function showError(message) {{
      mapElement.className = 'map-error';
      mapElement.textContent = message;
    }}
    try {{
      if (!window.kakao || !kakao.maps || typeof kakao.maps.LatLng !== 'function') {{
        throw new Error('Kakao Maps SDK를 불러오지 못했습니다. 도메인과 JavaScript 키를 확인하세요.');
      }}
      const first = places[0];
      const map = new kakao.maps.Map(mapElement, {{
        center: new kakao.maps.LatLng(first.latitude, first.longitude), level: 7,
      }});
      const bounds = new kakao.maps.LatLngBounds();
      places.forEach((place) => {{
        const position = new kakao.maps.LatLng(place.latitude, place.longitude);
        const marker = new kakao.maps.Marker({{ map, position, title: place.name }});
        const content = document.createElement('div');
        content.className = 'info-window';
        const title = document.createElement('strong');
        title.textContent = place.kind === 'landmark' ? `관광지 · ${{place.name}}` : `음식 · ${{place.name}}`;
        const description = document.createElement('span');
        description.textContent = place.description;
        content.append(title, description);
        const infoWindow = new kakao.maps.InfoWindow({{ content, removable: true }});
        kakao.maps.event.addListener(marker, 'click', () => infoWindow.open(map, marker));
        bounds.extend(position);
      }});
      if (places.length > 1) map.setBounds(bounds);
    }} catch (error) {{
      showError(error.message || '카카오맵을 초기화하지 못했습니다.');
    }}
  </script>
</body>
</html>"""


def _to_place(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    try:
        latitude = float(item["latitude"])
        longitude = float(item["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {
        "kind": "landmark" if item.get("kind") == "landmark" else "food",
        "name": str(item.get("name", "이름 없음")),
        "description": str(item.get("description", "설명이 없습니다.")),
        "latitude": latitude,
        "longitude": longitude,
    }


def _message_html(message: str) -> str:
    return f"<p class='map-error'>{html.escape(message)}</p>"
