from __future__ import annotations

import json
from typing import TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.providers.base import ProviderUnavailable

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class NebiusModelProvider:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        if not api_key:
            raise ProviderUnavailable("NEBIUS_API_KEY is not configured")
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete_json(
        self, *, system: str, user: str, schema: type[SchemaT]
    ) -> SchemaT:
        completion = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        )
        message = completion.choices[0].message
        if getattr(message, "refusal", None):
            raise ProviderUnavailable(f"Model refused request: {message.refusal}")
        if not message.content:
            raise ProviderUnavailable("Model returned no structured content")
        return schema.model_validate(json.loads(message.content))

