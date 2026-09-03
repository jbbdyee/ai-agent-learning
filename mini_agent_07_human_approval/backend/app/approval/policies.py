from typing import Literal


Risk = Literal["read", "change", "forbidden"]

TOOL_POLICIES: dict[str, Risk] = {
    "search_product": "read",
    "check_inventory": "read",
    "calculate_order_total": "read",
    "place_order": "change",
}


def action_risk(tool_name: str) -> Risk:
    return TOOL_POLICIES.get(tool_name, "forbidden")