from fastapi import FastAPI

from app.routers.agent_router import agent_router
from app.routers.map_travel_router import map_travel_router
from app.routers.media_router import media_router
from app.routers.travel_tool_router import travel_tool_router


app = FastAPI(title="Mini Agent 02 · Prompt와 Structured Output")
app.include_router(agent_router)
app.include_router(media_router)
app.include_router(map_travel_router)
app.include_router(travel_tool_router)
