from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.providers.base import ProviderUnavailable

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class NebiusModelProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        enable_thinking: bool = False,
    ) -> None:
        if not api_key:
            raise ProviderUnavailable("NEBIUS_API_KEY is not configured")
        self._api_key = api_key
        self._chat_url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._transport = transport
        self._enable_thinking = enable_thinking
        self.usage: dict[str, int] = {
            "requests": 0, "input_tokens": 0, "output_tokens": 0,
        }

    async def complete_json(
        self, *, system: str, user: str, schema: type[SchemaT]
    ) -> SchemaT:
        payload = {
            "model": self._model,
            "max_tokens": 16_384 if self._enable_thinking else 8_192,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "chat_template_kwargs": {"enable_thinking": self._enable_thinking},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=120.0 if self._enable_thinking else 60.0,
            ) as client:
                self.usage["requests"] += 1
                response = await client.post(
                    self._chat_url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailable(
                f"Nebius request failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("Nebius request failed") from exc

        try:
            envelope = response.json()
            usage = envelope.get("usage", {})
            for provider_name, local_name in (
                ("prompt_tokens", "input_tokens"),
                ("completion_tokens", "output_tokens"),
            ):
                count = usage.get(provider_name)
                if isinstance(count, int) and count >= 0:
                    self.usage[local_name] += count
            message = envelope["choices"][0]["message"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderUnavailable("Model returned an invalid response envelope") from exc
        if message.get("refusal"):
            raise ProviderUnavailable(f"Model refused request: {message['refusal']}")
        content = message.get("content")
        if not content:
            raise ProviderUnavailable("Model returned no structured content")
        try:
            return schema.model_validate_json(content)
        except ValueError as exc:
            raise ProviderUnavailable("Model returned invalid structured content") from exc
