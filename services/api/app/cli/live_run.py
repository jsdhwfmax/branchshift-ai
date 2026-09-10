"""Run the actual provider pipeline and retain its evidence without a web server."""
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import replace
from pathlib import Path

from app.config import settings
from app.domain.models import TERMINAL_RUN_STATUSES, CreateRunRequest, RunStatus
from app.orchestrator.run_manager import RunManager
from app.providers.redaction import redact
from app.storage.repositories import RunRepository


async def execute(repo_url: str, output: Path, *, project_path: str | None = None) -> bool:
    output.mkdir(parents=True, exist_ok=True)
    config = replace(settings, mode="live", database_url=f"sqlite:///{output / 'runs.db'}")
    repository = RunRepository(config.database_url)
    manager = RunManager(repository, config)
    try:
        run = await manager.create(CreateRunRequest.model_validate({
            "repo_url": repo_url, "project_path": project_path,
        }))
        print(f"RUN_ID={run.id}", flush=True)
        cursor = 0
        while True:
            for event in await repository.wait_for_events(run.id, cursor, timeout=1):
                cursor = event.id
                print(f"[{event.type}] {event.message}", flush=True)
            run = await repository.require_run(run.id)
            if run.status in TERMINAL_RUN_STATUSES:
                break
        await manager.wait(run.id)
        run = await repository.require_run(run.id)
        document = redact(
            json.dumps(run.model_dump(mode="json"), indent=2),
            [config.nebius_api_key, config.tavily_api_key],
        )
        evidence_path = output / f"{run.id}.json"
        evidence_path.write_text(document + "\n")
        if run.patch:
            (output / f"{run.id}.patch").write_text(run.patch)
        print(f"STATUS={run.status.value}\nEVIDENCE={evidence_path.resolve()}", flush=True)
        if run.failure_reason:
            print(f"FAILURE={run.failure_reason}", flush=True)
        return run.status is RunStatus.COMPLETED
    finally:
        await manager.shutdown()
        repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-url", default="https://github.com/jsdhwfmax/branchshift-ai")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--project-path", help="Python project directory relative to repository root"
    )
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(execute(
        args.repo_url, args.output, project_path=args.project_path,
    )) else 1)


if __name__ == "__main__":
    main()
