from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.domain.events import EVENTS
from app.domain.models import (
    TERMINAL_RUN_STATUSES,
    BranchResult,
    BranchStatus,
    Citation,
    CreateRunRequest,
    MigrationStrategy,
    RunStatus,
    RunSummary,
    http_url,
)
from app.orchestrator.baseline import BaselineRunner, repository_workdir
from app.orchestrator.branch_runner import BranchRunner
from app.orchestrator.evaluator import rank_results
from app.orchestrator.planner import MigrationPlanner
from app.orchestrator.research import MigrationResearch
from app.providers.contree import ContreeSandboxProvider
from app.providers.nebius import NebiusModelProvider
from app.providers.redaction import redact
from app.providers.tavily import TavilyResearchProvider
from app.storage.repositories import RunRepository

PYDANTIC_MIGRATION_URL = "https://docs.pydantic.dev/latest/migration/"
CONTREE_BRANCHING_URL = (
    "https://docs.tokenfactory.nebius.com/sandboxes/sdk/python_sdk/branching"
)

WINNING_PATCH = """diff --git a/src/sample_app/models.py b/src/sample_app/models.py
index 1ae36c2..6e23591 100644
--- a/src/sample_app/models.py
+++ b/src/sample_app/models.py
@@ -1,7 +1,7 @@
-from pydantic import BaseModel, validator
+from pydantic import BaseModel, field_validator
 
 class User(BaseModel):
-    @validator("name")
+    @field_validator("name")
     def name_must_not_be_blank(cls, value: str) -> str:
         if not value.strip():
             raise ValueError("name must not be blank")
@@ -12,4 +12,4 @@ class User(BaseModel):
-        return self.dict()
+        return self.model_dump()
"""


def mock_strategies() -> list[MigrationStrategy]:
    source = PYDANTIC_MIGRATION_URL
    return [
        MigrationStrategy(
            id="minimal",
            title="Surgical API swap",
            rationale="Replace only removed v1 APIs while preserving the public model surface.",
            ordered_steps=[
                "Replace validator with field_validator",
                "Replace dict() and parse_obj() at call sites",
                "Run the existing test contract unchanged",
            ],
            source_urls=[http_url(source)],
            target_files=["src/sample_app/models.py", "src/sample_app/api.py"],
        ),
        MigrationStrategy(
            id="compatibility",
            title="Compatibility bridge",
            rationale="Move imports through pydantic.v1 before upgrading call sites in stages.",
            ordered_steps=[
                "Introduce compatibility imports",
                "Upgrade serialization call sites",
                "Remove the bridge after the test gate passes",
            ],
            source_urls=[http_url(source)],
            target_files=["src/sample_app/models.py", "src/sample_app/api.py"],
        ),
        MigrationStrategy(
            id="refactor",
            title="Model-layer refactor",
            rationale="Adopt v2 configuration and validation patterns across the model layer.",
            ordered_steps=[
                "Convert class Config to ConfigDict",
                "Rewrite validators with explicit modes",
                "Normalize model validation and serialization",
            ],
            source_urls=[http_url(source)],
            target_files=["src/sample_app/models.py", "src/sample_app/api.py"],
        ),
    ]


MOCK_RESULTS = {
    "minimal": BranchResult(
        strategy_id="minimal",
        status=BranchStatus.PASSED,
        tests_collected=18,
        tests_passed=18,
        tests_failed=0,
        pip_check_passed=True,
        lint_findings=0,
        changed_files=3,
        changed_lines=34,
        elapsed_seconds=13.8,
        patch=WINNING_PATCH,
    ),
    "compatibility": BranchResult(
        strategy_id="compatibility",
        status=BranchStatus.PASSED,
        tests_collected=18,
        tests_passed=18,
        tests_failed=0,
        pip_check_passed=True,
        lint_findings=1,
        changed_files=5,
        changed_lines=61,
        elapsed_seconds=11.9,
        patch=WINNING_PATCH.replace("field_validator", "validator"),
    ),
    "refactor": BranchResult(
        strategy_id="refactor",
        status=BranchStatus.FAILED,
        tests_collected=18,
        tests_passed=16,
        tests_failed=2,
        pip_check_passed=True,
        lint_findings=0,
        changed_files=8,
        changed_lines=103,
        elapsed_seconds=17.2,
        patch=WINNING_PATCH,
    ),
}


class RunManager:
    def __init__(self, repository: RunRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings
        self._tasks: set[asyncio.Task[None]] = set()
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_runs)

    async def create(self, request: CreateRunRequest) -> RunSummary:
        summary = RunSummary(
            id=uuid4().hex[:12],
            repo_url=request.repo_url,
            target=request.target,
            mode="mock" if self._settings.is_mock else "live",
        )
        await self._repository.create_run(summary)
        task = asyncio.create_task(self._execute_guarded(summary.id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return summary

    async def _execute_guarded(self, run_id: str) -> None:
        async with self._semaphore:
            try:
                await asyncio.wait_for(
                    self._execute(run_id), timeout=self._settings.run_timeout_seconds
                )
            except Exception as exc:  # noqa: BLE001 - background task must persist failure
                summary = await self._repository.require_run(run_id)
                if summary.status not in TERMINAL_RUN_STATUSES:
                    summary.failure_reason = redact(
                        str(exc),
                        [self._settings.nebius_api_key, self._settings.tavily_api_key],
                    )[:500]
                    await self._repository.save_run(summary)
                    await self._repository.set_status(run_id, RunStatus.FAILED, "Run failed safely")
                    await self._repository.append_event(
                        run_id,
                        EVENTS.RUN_FAILED,
                        "The run stopped; partial evidence is preserved.",
                    )

    async def _step(self) -> None:
        if self._settings.mock_step_delay_seconds > 0:
            await asyncio.sleep(self._settings.mock_step_delay_seconds)

    async def _execute(self, run_id: str) -> None:
        if self._settings.is_mock:
            await self._execute_mock(run_id)
        else:
            await self._execute_live(run_id)

    async def _execute_mock(self, run_id: str) -> None:

        await self._repository.set_status(
            run_id, RunStatus.PREPARING, "Repository validated; baseline snapshot ready"
        )
        await self._step()
        await self._repository.set_status(
            run_id, RunStatus.PLANNING, "Retrieving official migration evidence"
        )
        citations = [
            Citation(
                title="Pydantic V2 migration guide",
                url=http_url(PYDANTIC_MIGRATION_URL),
                evidence=(
                    "Official mappings for validators, parsing, configuration, "
                    "and serialization."
                ),
            ),
            Citation(
                title="Contree branching workflows",
                url=http_url(CONTREE_BRANCHING_URL),
                evidence="Independent child states execute from one reproducible filesystem state.",
            ),
        ]
        await self._repository.append_event(
            run_id,
            EVENTS.RESEARCH_READY,
            "2 allowlisted official sources retained",
            payload={"citations": [item.model_dump(mode="json") for item in citations]},
        )
        await self._step()

        summary = await self._repository.require_run(run_id)
        summary.citations = citations
        summary.strategies = mock_strategies()
        await self._repository.save_run(summary)
        await self._repository.append_event(
            run_id,
            EVENTS.STRATEGIES_READY,
            "Nemotron produced 3 schema-valid strategies",
            payload={
                "strategies": [item.model_dump(mode="json") for item in summary.strategies]
            },
        )
        await self._repository.set_status(
            run_id, RunStatus.BRANCHING, "Three branches started from the same checkpoint"
        )

        async def run_branch(strategy: MigrationStrategy, offset: float) -> BranchResult:
            await asyncio.sleep(offset)
            await self._repository.append_event(
                run_id,
                EVENTS.BRANCH_STARTED,
                f"{strategy.title}: patch attempt 1",
                branch_id=strategy.id,
            )
            await self._step()
            await self._repository.append_event(
                run_id,
                EVENTS.BRANCH_PROGRESS,
                "Patch applies; running pytest, pip check, and Ruff",
                branch_id=strategy.id,
            )
            await self._step()
            result = MOCK_RESULTS[strategy.id].model_copy(deep=True)
            await self._repository.append_event(
                run_id,
                EVENTS.BRANCH_COMPLETED,
                f"{result.tests_passed}/{result.tests_collected} tests passed",
                branch_id=strategy.id,
                payload={"result": result.model_dump(mode="json")},
            )
            return result

        coroutines: list[Coroutine[Any, Any, BranchResult]] = [
            run_branch(strategy, index * self._settings.mock_step_delay_seconds / 2)
            for index, strategy in enumerate(summary.strategies)
        ]
        results = list(await asyncio.gather(*coroutines))
        summary = await self._repository.require_run(run_id)
        summary.branches = results
        await self._repository.save_run(summary)
        await self._repository.set_status(
            run_id, RunStatus.EVALUATING, "Reapplying candidate patches to the baseline"
        )
        await self._step()

        winner, fully_verified = rank_results(results)
        if winner is None or not fully_verified:
            raise RuntimeError("No branch passed the deterministic verification gate")
        summary = await self._repository.require_run(run_id)
        summary.winner_id = winner.strategy_id
        summary.patch = winner.patch
        summary.report = (
            f"{winner.strategy_id.title()} won: {winner.tests_passed}/{winner.tests_collected} "
            f"tests, {winner.lint_findings} lint findings, {winner.changed_lines} changed lines. "
            "The patch was reapplied to the baseline before selection."
        )
        await self._repository.save_run(summary)
        await self._repository.append_event(
            run_id,
            EVENTS.WINNER_SELECTED,
            "Minimal won the deterministic evidence gate",
            branch_id=winner.strategy_id,
            payload={"winner_id": winner.strategy_id},
        )
        await self._repository.set_status(
            run_id, RunStatus.COMPLETED, "Verified migration package ready"
        )
        await self._repository.append_event(
            run_id,
            EVENTS.RUN_COMPLETED,
            "Winner patch and evidence report are ready",
            branch_id=winner.strategy_id,
        )

    async def _execute_live(self, run_id: str) -> None:
        if not self._settings.nebius_api_key or not self._settings.tavily_api_key:
            raise RuntimeError("Live mode requires configured Nebius and Tavily credentials")
        summary = await self._repository.require_run(run_id)
        model = NebiusModelProvider(
            self._settings.nebius_api_key,
            self._settings.nebius_base_url,
            self._settings.nemotron_model,
        )
        research = MigrationResearch(TavilyResearchProvider(self._settings.tavily_api_key))
        async with ContreeSandboxProvider(
            token=self._settings.nebius_api_key,
            base_url=self._settings.contree_api_url,
        ) as sandbox:
            await self._repository.set_status(
                run_id,
                RunStatus.PREPARING,
                "Cloning and testing the repository inside Token Factory Sandbox",
            )
            baseline = await BaselineRunner(sandbox).prepare(
                self._settings.contree_image,
                summary.repo_url,
            )
            await self._repository.append_event(
                run_id,
                EVENTS.BRANCH_PROGRESS,
                f"Baseline pinned at {baseline.commit_sha[:12]}; "
                f"{baseline.tests_passed}/{baseline.tests_collected} tests passed",
                payload={"commit_sha": baseline.commit_sha},
            )
            await self._repository.set_status(
                run_id,
                RunStatus.PLANNING,
                "Retrieving official guidance and requesting grounded Nemotron strategies",
            )
            citations = await research.collect()
            await self._repository.append_event(
                run_id,
                EVENTS.RESEARCH_READY,
                f"{len(citations)} allowlisted official sources retained",
                payload={"citations": [item.model_dump(mode="json") for item in citations]},
            )
            strategies = await MigrationPlanner(model).plan(baseline.evidence, citations)
            summary = await self._repository.require_run(run_id)
            summary.citations = citations
            summary.strategies = strategies
            await self._repository.save_run(summary)
            await self._repository.append_event(
                run_id,
                EVENTS.STRATEGIES_READY,
                "Nemotron produced 3 grounded, schema-valid strategies",
                payload={
                    "strategies": [item.model_dump(mode="json") for item in strategies]
                },
            )
            await self._repository.set_status(
                run_id,
                RunStatus.BRANCHING,
                "Three migration branches started from the pinned baseline",
            )
            runner = BranchRunner(model, sandbox)

            async def execute_branch(strategy: MigrationStrategy) -> BranchResult:
                await self._repository.append_event(
                    run_id,
                    EVENTS.BRANCH_STARTED,
                    f"{strategy.title}: bounded patch loop started",
                    branch_id=strategy.id,
                )
                try:
                    result = await runner.run(
                        baseline.state,
                        strategy,
                        baseline.evidence,
                        workdir=repository_workdir(summary.repo_url),
                    )
                except Exception as exc:  # noqa: BLE001 - preserve sibling branch evidence
                    message = redact(
                        str(exc),
                        [self._settings.nebius_api_key, self._settings.tavily_api_key],
                    )[:500]
                    await self._repository.append_event(
                        run_id,
                        EVENTS.BRANCH_COMPLETED,
                        f"Branch failed safely: {message}",
                        branch_id=strategy.id,
                    )
                    return BranchResult(
                        strategy_id=strategy.id,
                        status=BranchStatus.FAILED,
                        tests_collected=0,
                        tests_passed=0,
                        tests_failed=0,
                        pip_check_passed=False,
                        lint_findings=0,
                        changed_files=0,
                        changed_lines=0,
                        elapsed_seconds=0,
                        patch_applicable=False,
                    )
                await self._repository.append_event(
                    run_id,
                    EVENTS.BRANCH_COMPLETED,
                    f"{result.tests_passed}/{result.tests_collected} tests passed",
                    branch_id=strategy.id,
                    payload={"result": result.model_dump(mode="json")},
                )
                return result

            results = list(
                await asyncio.gather(*(execute_branch(strategy) for strategy in strategies))
            )

            winner, fully_verified = rank_results(results)
            if winner is None or not fully_verified or not winner.patch:
                raise RuntimeError("No live branch passed the deterministic verification gate")
            winner_strategy = next(
                strategy for strategy in strategies if strategy.id == winner.strategy_id
            )
            final_verification = await runner.validate_existing_patch(
                baseline.state,
                winner_strategy,
                winner.patch,
                workdir=repository_workdir(summary.repo_url),
            )
            if final_verification.status is not BranchStatus.PASSED:
                raise RuntimeError("Winner patch failed clean baseline revalidation")

        summary = await self._repository.require_run(run_id)
        summary.branches = results
        await self._repository.save_run(summary)
        await self._repository.set_status(
            run_id,
            RunStatus.EVALUATING,
            "Ranking branches from deterministic test and patch metrics",
        )
        summary = await self._repository.require_run(run_id)
        summary.winner_id = winner.strategy_id
        summary.patch = winner.patch
        summary.report = (
            f"{winner.strategy_id.title()} won at commit {baseline.commit_sha[:12]}: "
            f"{winner.tests_passed}/{winner.tests_collected} tests, "
            f"{winner.lint_findings} lint findings, {winner.changed_lines} changed lines."
        )
        await self._repository.save_run(summary)
        await self._repository.append_event(
            run_id,
            EVENTS.WINNER_SELECTED,
            f"{winner.strategy_id.title()} won the deterministic evidence gate",
            branch_id=winner.strategy_id,
            payload={"winner_id": winner.strategy_id},
        )
        await self._repository.set_status(
            run_id,
            RunStatus.COMPLETED,
            "Verified live migration package ready",
        )
        await self._repository.append_event(
            run_id,
            EVENTS.RUN_COMPLETED,
            "Winner patch and live evidence report are ready",
            branch_id=winner.strategy_id,
        )
