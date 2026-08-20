from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas import ProviderName


class MapTravelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName | None = None
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def trim_and_validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("여행 질문을 입력해 주세요.")
        return value


class Landmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category: str = Field(min_length=1)


class FoodRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    estimated_price_krw: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class MapTravelContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1)
    nights: int = Field(ge=0)
    days: int = Field(ge=1)
    summary: str = Field(min_length=1, max_length=500)
    landmarks: list[Landmark] = Field(min_length=1, max_length=10)
    foods: list[FoodRecommendation] = Field(default_factory=list, max_length=10)
    cautions: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_duration(self) -> "MapTravelContent":
        if self.days != self.nights + 1:
            raise ValueError("여행 기간은 days == nights + 1 관계여야 합니다.")
        return self


class MapTravelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    model: str = Field(min_length=1)
    content: MapTravelContent
    latency_ms: int = Field(ge=0)

