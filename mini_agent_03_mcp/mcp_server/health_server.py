"""8011 포트에서 독립 실행되는 건강 습관 관리 Streamable HTTP MCP Server입니다."""
import os
from mcp.server.fastmcp import FastMCP

HEALTH_MCP_HOST  = os.getenv("HEALTH_MCP_HOST", "192.168.1.12")
HEALTH_MCP_PORT  = int(os.getenv("HEALTH_MCP_PORT", "8011"))

mcp = FastMCP(
    "mini-agent-health",
    instructions="앉아있는 시간, 카페인 섭취 습관, 건강 습관 가이드를 제공하는 교육용 서버입니다.",
    host=HEALTH_MCP_HOST,
    port=HEALTH_MCP_PORT,
    stateless_http=True,
    json_response=True,
)
@mcp.tool()
def check_sitting_habit(
    sitting_minutes: int,
) -> dict:
    """연속으로 앉아 있었던 시간을 기준으로 건강 습관을 확인합니다."""

    if sitting_minutes < 0:
        raise ValueError("sitting_minutes는 0 이상이어야 합니다.")

    if sitting_minutes < 30:
        status = "좋음"
        message = "현재 앉아있는 시간은 비교적 적절합니다."

    elif sitting_minutes < 60:
        status = "주의"
        message = "잠시 일어나서 가볍게 움직여보세요."
    else:
        status = "개선 필요"
        message = "오래 앉아 있었습니다. 걷거나 스트레칭하는 것을 권장합니다."

    return {
        "sitting_minutes": sitting_minutes,
        "status": status,
        "message": message,
        "source": "health-sitting-service",
    }
@mcp.tool()
def check_caffeine_timing(
    cups: int,
    last_caffeine_hour: int,
) -> dict:
    """하루 카페인 섭취량과 마지막 섭취 시간을 확인합니다."""

    if cups < 0:
        raise ValueError("cups는 0 이상이어야 합니다.")

    if last_caffeine_hour < 0 or last_caffeine_hour > 23:
        raise ValueError("last_caffeine_hour는 0부터 23 사이여야 합니다.")

    if cups <= 2 and last_caffeine_hour < 15:
        status = "좋음"
        message = "카페인 섭취 습관이 비교적 적절합니다."

    elif last_caffeine_hour >= 18:
        status = "주의"
        message = "늦은 시간의 카페인 섭취는 줄여보는 것이 좋습니다."

    else:
        status = "보통"
        message = "카페인 섭취량과 시간을 조금 조절해보세요."

    return {
        "cups": cups,
        "last_caffeine_hour": last_caffeine_hour,
        "status": status,
        "message": message,
        "source": "health-caffeine-service",
    }

@mcp.resource("health://guide/daily-habit")
def daily_health_guide() -> str:
    """교육용 일상 건강 습관 가이드입니다."""
    return (
        "장시간 앉아 있을 때는 중간중간 몸을 움직이고, "
        "늦은 시간의 카페인 섭취와 장시간 화면 사용을 줄이는 습관을 권장합니다."
    )
if os.name == "main":
    mcp.run(transport="streamable-http")