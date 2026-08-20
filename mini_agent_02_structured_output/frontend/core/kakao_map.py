import html
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_kakao_map_key() -> str:
    return os.getenv("KAKAO_MAP_JAVASCRIPT_KEY", "").strip()


def build_kakao_map_html(landmarks: list[dict[str, Any]], foods: list[dict[str, Any]]) -> str:
    """Build an isolated Kakao Maps component for valid recommendation coordinates."""
    app_key = get_kakao_map_key()
    if not app_key:
        return "<p class='map-message'>카카오맵 JavaScript 키가 설정되지 않았습니다.</p>"

    places = [
        place
        for place in [
            *(_to_place(item, "landmark") for item in landmarks),
            *(_to_place(item, "food") for item in foods),
        ]
        if place is not None
    ]
    if not places:
        return "<p class='map-message'>지도에 표시할 유효한 좌표가 없습니다.</p>"

    places_json = json.dumps(places, ensure_ascii=False).replace("</", "<\\/")
    sdk_url = "https://dapi.kakao.com/v2/maps/sdk.js?appkey=" + quote(app_key, safe="")
    return f"""
<!doctype html>
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

    function markerImage(color) {{
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="44" viewBox="0 0 34 44"><path fill="${{color}}" stroke="#fff" stroke-width="2" d="M17 1C8.7 1 2 7.7 2 16c0 11.2 15 26 15 26s15-14.8 15-26C32 7.7 25.3 1 17 1z"/><circle fill="#fff" cx="17" cy="16" r="5"/></svg>`;
      return new kakao.maps.MarkerImage(
        'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
        new kakao.maps.Size(34, 44),
        {{ offset: new kakao.maps.Point(17, 44) }},
      );
    }}

    try {{
      if (!window.kakao || !kakao.maps) {{
        throw new Error('Kakao Maps SDK를 불러오지 못했습니다. 도메인과 JavaScript 키를 확인하세요.');
      }}
      const first = places[0];
      const map = new kakao.maps.Map(mapElement, {{
        center: new kakao.maps.LatLng(first.latitude, first.longitude),
        level: 7,
      }});
      const bounds = new kakao.maps.LatLngBounds();

      places.forEach((place) => {{
        const position = new kakao.maps.LatLng(place.latitude, place.longitude);
        const marker = new kakao.maps.Marker({{
          map,
          position,
          title: place.name,
          image: markerImage(place.kind === 'landmark' ? '#2563eb' : '#ea580c'),
        }});
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
</html>
"""


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
