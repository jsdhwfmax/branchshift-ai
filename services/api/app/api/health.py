from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/integrations")
async def integration_health(request: Request) -> dict[str, object]:
    config = request.app.state.settings
    return {
        "mode": "mock" if config.is_mock else "live",
        "ready": config.is_mock
        or bool(config.nebius_api_key and config.tavily_api_key and config.contree_api_url),
        "integrations": {
            "nemotron": {"configured": bool(config.nebius_api_key)},
            "tavily": {"configured": bool(config.tavily_api_key)},
            "contree": {
                "configured": bool(config.nebius_api_key and config.contree_api_url)
            },
        },
    }

