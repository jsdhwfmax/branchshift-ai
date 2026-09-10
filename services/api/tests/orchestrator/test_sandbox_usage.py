import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.config import Settings
from app.domain.models import CreateRunRequest, RunStatus, RunSummary
from app.orchestrator.run_manager import RunManager
from app.providers.contree import ContreeSandboxProvider
from app.storage.repositories import RunRepository


def live_settings(database_url):
    return Settings(
        mode="live", database_url=database_url,
        nebius_api_key="test-key", nebius_project_id="test-project",
        tavily_api_key="test-research", max_concurrent_runs=2,
    )


async def test_concurrent_live_failures_persist_separate_real_adapter_counts(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'usage.db'}"
    repository = RunRepository(database_url)
    manager = RunManager(repository, live_settings(database_url))
    providers = []
    both_entered = asyncio.Event()

    async def enter(provider):
        providers.append(provider)
        if len(providers) == 1:
            use = AsyncMock(side_effect=RuntimeError("Image SDK request failed"))
        else:
            prepared = SimpleNamespace(uuid="failed", exit_code=2, stdout="setup failed", stderr="")
            image = SimpleNamespace(run=AsyncMock(return_value=prepared))
            use = AsyncMock(return_value=image)
            both_entered.set()
        provider._sdk = SimpleNamespace(
            images=SimpleNamespace(use=use), __aexit__=AsyncMock(return_value=None),
        )
        await both_entered.wait()
        return provider

    monkeypatch.setattr(ContreeSandboxProvider, "__aenter__", enter)
    request = CreateRunRequest(repo_url="https://github.com/owner/repo")
    runs = [await manager.create(request) for _ in range(2)]
    await asyncio.wait_for(asyncio.gather(*(manager.wait(run.id) for run in runs)), timeout=2)
    summaries = [await repository.require_run(run.id) for run in runs]
    assert all(summary.status is RunStatus.FAILED for summary in summaries)
    usage = [summary.provider_usage for summary in summaries]
    assert sorted(item["sandbox_sdk_calls_attempted"] for item in usage) == [1, 2]
    assert sorted(item["sandbox_sdk_calls_failed"] for item in usage) == [0, 1]
    assert sorted(item["sandbox_run_exit_nonzero"] for item in usage) == [0, 1]
    assert all(item["sandbox_usage_version"] == 1 for item in usage)
    assert all(item["requests"] == 0 for item in usage)
    assert providers[0].usage is not providers[1].usage
    assert manager._usage == {}
    # The persisted summary is a snapshot, not an alias of the now-finished provider.
    providers[0].usage["sandbox_sdk_calls_attempted"] = 999
    for run in runs:
        assert (await repository.require_run(run.id)).provider_usage[
            "sandbox_sdk_calls_attempted"
        ] != 999
    await manager.shutdown()
    repository.close()


async def test_live_cancellation_persists_incomplete_remote_call_observation(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'cancel-usage.db'}"
    repository = RunRepository(database_url)
    manager = RunManager(repository, live_settings(database_url))
    started = asyncio.Event()

    async def blocked_use(image):
        started.set()
        await asyncio.Event().wait()

    async def enter(provider):
        provider._sdk = SimpleNamespace(
            images=SimpleNamespace(use=blocked_use), __aexit__=AsyncMock(return_value=None),
        )
        return provider

    monkeypatch.setattr(ContreeSandboxProvider, "__aenter__", enter)
    run = await manager.create(CreateRunRequest(repo_url="https://github.com/owner/repo"))
    await asyncio.wait_for(started.wait(), timeout=1)
    await manager.shutdown()
    repository.close()
    reopened = RunRepository(database_url)
    summary = await reopened.require_run(run.id)
    assert summary.status is RunStatus.CANCELLED
    assert summary.provider_usage["sandbox_image_use_attempted"] == 1
    assert summary.provider_usage["sandbox_image_use_cancelled"] == 1
    assert summary.provider_usage["sandbox_sdk_calls_completed"] == 0
    assert summary.provider_usage["sandbox_sdk_calls_failed"] == 0
    assert summary.provider_usage["sandbox_run_attempted"] == 0
    assert summary.provider_usage["sandbox_usage_version"] == 1
    assert manager._usage == {}
    reopened.close()


async def test_recovery_does_not_backfill_old_or_unstarted_run_usage(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'historical-usage.db'}"
    repository = RunRepository(database_url)
    previous_usage = {"requests": 2, "input_tokens": 40, "output_tokens": 10}
    for run_id, usage in (("historical", previous_usage), ("unstarted", {})):
        await repository.create_run(RunSummary(
            id=run_id, repo_url="https://github.com/owner/repo",
            status=RunStatus.BRANCHING, provider_usage=usage,
        ))
    manager = RunManager(repository, live_settings(database_url))
    await manager.recover_interrupted()
    assert (await repository.require_run("historical")).provider_usage == previous_usage
    assert (await repository.require_run("unstarted")).provider_usage == {}
    repository.close()
