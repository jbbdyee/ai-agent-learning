from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.map_travel.provider_service import (
    MapTravelOutputValidationError,
    MapTravelProviderError,
)
from app.map_travel.map_embed import build_map_html, decode_places
from app.map_travel.schemas import MapTravelRequest, MapTravelResponse
from app.map_travel.service import create_map_travel


map_travel_router = APIRouter(tags=["02 · Structured Output"])


@map_travel_router.get("/api/structured/map-travel/map", response_class=HTMLResponse)
def render_map(places: str = Query(min_length=2, max_length=12000)) -> HTMLResponse:
    try:
        return HTMLResponse(build_map_html(decode_places(places)))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@map_travel_router.post(
    "/api/structured/map-travel",
    response_model=MapTravelResponse,
)
def create_map_travel_response(payload: MapTravelRequest) -> MapTravelResponse:
    try:
        return create_map_travel(payload)
    except (MapTravelOutputValidationError, ValidationError) as error:
        raise HTTPException(
            status_code=422,
            detail="Provider 응답이 지도 여행 데이터 계약을 충족하지 않습니다.",
        ) from error
    except MapTravelProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="선택한 Provider의 지도 여행 생성에 실패했습니다.",
        ) from error

