from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas import ProviderName

CityName = Literal["서울", "부산", "제주", "강릉", "인천", "대전", "대구", "광주", "전주", "경주"]
TravelToolName = Literal["recommend_attractions", "recommend_restaurants"]


class TravelPlanParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: CityName = Field(description="여행 지역")
    check_in: date = Field(description="여행 일정 시작일(오늘 이후)")
    check_out: date = Field(description="여행 일정 종료일(시작일 이후)")
    guests: int = Field(ge=1, le=10, description="여행 인원")

    @model_validator(mode="after")
    def validate_dates(self) -> "TravelPlanParameters":
        if self.check_in < date.today():
            raise ValueError("여행 일정 시작일은 오늘 이후여야 합니다.")
        if self.check_out <= self.check_in:
            raise ValueError("여행 일정 종료일은 시작일 이후여야 합니다.")
        return self


class TravelPlanRequest(TravelPlanParameters):
    model_config = ConfigDict(extra="forbid")
    provider: ProviderName | None = Field(default=None, description="사용할 LLM Provider")


class TravelRecommendationInput(TravelPlanParameters):
    model_config = ConfigDict(extra="forbid")


class Attraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100, description="관광지 이름")
    description: str = Field(min_length=1, max_length=500, description="관광지 추천 설명")
    latitude: float = Field(ge=-90, le=90, description="위도")
    longitude: float = Field(ge=-180, le=180, description="경도")
    category: str | None = Field(default=None, min_length=1, max_length=50, description="관광지 분류")


class Restaurant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100, description="맛집 이름")
    description: str = Field(min_length=1, max_length=500, description="맛집 추천 설명")
    latitude: float = Field(ge=-90, le=90, description="위도")
    longitude: float = Field(ge=-180, le=180, description="경도")
    estimated_price_krw: int = Field(ge=0, description="1인 기준 예상 가격(원)")


class AttractionRecommendationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attractions: list[Attraction] = Field(min_length=1, max_length=10, description="추천 관광지 목록")


class RestaurantRecommendationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    restaurants: list[Restaurant] = Field(min_length=1, max_length=10, description="추천 맛집 목록")


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=100, description="Tool 호출 식별자")
    name: TravelToolName = Field(description="허용된 Tool 이름")
    arguments: TravelRecommendationInput = Field(description="검증된 Tool 인자")


class ToolExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool_call_id: str = Field(min_length=1, max_length=100, description="원본 Tool 호출 식별자")
    name: TravelToolName = Field(description="실행한 Tool 이름")
    success: bool = Field(description="Tool 실행 성공 여부")
    data: AttractionRecommendationResult | RestaurantRecommendationResult | None = Field(default=None, description="정규화된 Tool 실행 결과")
    error: str | None = Field(default=None, min_length=1, max_length=500, description="안전한 오류 메시지")

    @model_validator(mode="after")
    def validate_result(self) -> "ToolExecutionResult":
        if self.success and self.data is None:
            raise ValueError("성공한 Tool 실행에는 data가 필요합니다.")
        if self.success and self.error is not None:
            raise ValueError("성공한 Tool 실행에는 error를 포함할 수 없습니다.")
        if not self.success and self.error is None:
            raise ValueError("실패한 Tool 실행에는 error가 필요합니다.")
        if not self.success and self.data is not None:
            raise ValueError("실패한 Tool 실행에는 data를 포함할 수 없습니다.")
        if self.name == "recommend_attractions" and self.data is not None and not isinstance(self.data, AttractionRecommendationResult):
            raise ValueError("관광지 Tool 결과 타입이 올바르지 않습니다.")
        if self.name == "recommend_restaurants" and self.data is not None and not isinstance(self.data, RestaurantRecommendationResult):
            raise ValueError("맛집 Tool 결과 타입이 올바르지 않습니다.")
        return self


class TravelPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: ProviderName = Field(description="사용된 LLM Provider")
    model: str = Field(min_length=1, max_length=200, description="사용된 모델")
    request: TravelPlanParameters = Field(description="검증된 여행 조건")
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=10, description="Provider가 제안한 Tool 호출")
    tool_results: list[ToolExecutionResult] = Field(default_factory=list, max_length=10, description="Tool 실행 결과")
    answer: str = Field(min_length=1, max_length=4000, description="최종 여행 답변")
    latency_ms: int = Field(ge=0, description="전체 처리 시간(ms)")
