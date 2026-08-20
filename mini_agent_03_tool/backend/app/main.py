from fastapi import FastAPI

from app.routers.agent_router import agent_router


OPENAPI_TAGS = [
    {"name": "01. LLM 기초", "description": "LLM 호출, Provider 비교, 여행 의도 분류 및 멀티모달 API"},
    {"name": "02. Structured Output", "description": "프롬프트 구성, Pydantic 검증 및 구조화 출력 API"},
    {"name": "03. Tool Use", "description": "Tool 조회, 선택, 검증, 실행 및 전체 Tool Loop API"},
]


app = FastAPI(title="Mini Agent 03 · Tool Use", openapi_tags=OPENAPI_TAGS)
app.include_router(agent_router)
