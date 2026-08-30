from __future__ import annotations

import asyncio
import json
import time

from app.config import settings
from app.providers.contree import ContreeSandboxProvider


async def run_spike() -> dict[str, object]:
    started = time.monotonic()
    async with ContreeSandboxProvider(
        token=settings.nebius_api_key,
        base_url=settings.contree_api_url,
    ) as sandbox:
        baseline = await sandbox.create_base(
            settings.contree_image,
            "mkdir -p /workspace && printf 'baseline\\n' > /workspace/marker.txt",
        )

        async def branch(name: str) -> dict[str, object]:
            result = await sandbox.run(
                baseline,
                f"printf '{name}\\n' >> /workspace/marker.txt && cat /workspace/marker.txt",
                timeout_seconds=60,
            )
            expected = f"baseline\n{name}"
            actual = result.stdout.strip()
            if actual != expected:
                raise RuntimeError(f"Branch {name} returned unexpected marker content")
            return {
                "name": name,
                "checkpoint_id": result.state.checkpoint_id,
                "marker": actual,
                "elapsed_seconds": round(result.elapsed_seconds, 3),
            }

        branches = await asyncio.gather(
            branch("minimal"),
            branch("compatibility"),
            branch("refactor"),
        )
        identifiers = {item["checkpoint_id"] for item in branches}
        if len(identifiers) != 3:
            raise RuntimeError("Contree did not return three isolated child states")
        return {
            "baseline_checkpoint_id": baseline.checkpoint_id,
            "branches": branches,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


def main() -> None:
    if not settings.nebius_api_key:
        raise SystemExit("NEBIUS_API_KEY is required for the Sandbox spike")
    print(json.dumps(asyncio.run(run_spike()), indent=2))


if __name__ == "__main__":
    main()

