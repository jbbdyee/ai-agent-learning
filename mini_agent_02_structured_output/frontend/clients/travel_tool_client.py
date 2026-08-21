from datetime import date
from typing import Any

from core.api_client import request


def create_travel_plan(
    provider: str,
    city: str,
    check_in: date,
    check_out: date,
    guests: int,
) -> dict[str, Any]:
    """Request a validated travel plan from the 2-5 Tool Use API."""
    return request(
        "POST",
        "/api/tools/travel-plan",
        json={
            "provider": provider,
            "city": city,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": guests,
        },
    )
