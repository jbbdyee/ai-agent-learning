from backend.app.main import health


def test_health_reports_registered_mcp_servers() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["mcp_servers"] == {
        "travel": "streamable-http",
        "policy": "stdio",
        "health": "streamable-http",
    }
