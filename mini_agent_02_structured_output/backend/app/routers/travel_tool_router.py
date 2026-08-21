from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.travel_tools import service
from app.travel_tools.schemas import TravelPlanRequest, TravelPlanResponse


travel_tool_router = APIRouter(tags=["02 · Tool Use"])


@travel_tool_router.post(
    "/api/tools/travel-plan",
    response_model=TravelPlanResponse,
)
def create_travel_plan(payload: TravelPlanRequest) -> TravelPlanResponse:
    try:
        return service.create_travel_plan(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail="Tool 인자가 여행 데이터 계약을 충족하지 않습니다.",
        ) from error
    except service.TravelProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="선택한 Provider의 여행 계획 생성에 실패했습니다.",
        ) from error
    except service.TravelToolExecutionError as error:
        raise HTTPException(
            status_code=503,
            detail="여행 정보 조회 Tool 실행에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error
