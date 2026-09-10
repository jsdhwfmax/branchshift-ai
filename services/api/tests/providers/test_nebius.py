import json
from typing import Literal

import httpx
from pydantic import BaseModel

from app.providers.nebius import NebiusModelProvider


class HealthCheck(BaseModel):
    status: Literal["ok"]


async def test_nebius_disables_thinking_for_structured_output():
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "usage": {"prompt_tokens": 15, "completion_tokens": 7},
                "choices": [
                    {"message": {"refusal": None, "content": '{"status":"ok"}'}}
                ]
            },
        )

    provider = NebiusModelProvider(
        api_key="test-key",
        base_url="https://api.tokenfactory.nebius.com/v1/",
        model="nvidia/Nemotron-3_5-Lightning",
        transport=httpx.MockTransport(handler),
    )

    result = await provider.complete_json(
        system="Return JSON.",
        user="Report status.",
        schema=HealthCheck,
    )

    assert result == HealthCheck(status="ok")
    assert captured["chat_template_kwargs"] == {"enable_thinking": False}
    assert captured["max_tokens"] == 8_192
    assert provider.usage == {"requests": 1, "input_tokens": 15, "output_tokens": 7}


async def test_reasoning_uses_larger_shared_output_budget_without_retaining_reasoning():
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["chat_template_kwargs"] == {"enable_thinking": True}
        assert payload["max_tokens"] == 16_384
        return httpx.Response(200, json={"choices": [{"message": {
            "content": '{"status":"ok"}', "reasoning_content": "internal reasoning",
        }}]})

    provider = NebiusModelProvider(
        "test-key", "https://api.tokenfactory.nebius.com/v1/", "nvidia/test",
        transport=httpx.MockTransport(handler), enable_thinking=True,
    )
    result = await provider.complete_json(system="Return JSON", user="Status", schema=HealthCheck)
    assert result.model_dump() == {"status": "ok"}
