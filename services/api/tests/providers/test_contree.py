import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.providers.base import ProviderUnavailable, SandboxState
from app.providers.contree import ContreeSandboxProvider


async def test_contree_provider_initializes_installed_sdk_without_network():
    async with ContreeSandboxProvider(
        token="test-token",
        project_id="test-project",
        base_url="https://api.tokenfactory.nebius.com/sandboxes",
    ) as provider:
        assert provider._sdk is not None


def test_contree_provider_requires_project_id():
    with pytest.raises(ProviderUnavailable, match="NEBIUS_PROJECT_ID"):
        ContreeSandboxProvider(
            token="test-token",
            project_id="",
            base_url="https://api.tokenfactory.nebius.com/sandboxes",
        )


def local_provider(usage=None):
    return ContreeSandboxProvider("test-token", "test-project", "https://example.test", usage=usage)


def sdk_state(name, exit_code=0, **methods):
    return SimpleNamespace(uuid=name, exit_code=exit_code, stdout="", stderr="", **methods)


def assert_settled(usage):
    for operation in ("sdk_calls", "image_use", "run", "read"):
        assert usage[f"sandbox_{operation}_attempted"] == sum(
            usage[f"sandbox_{operation}_{outcome}"]
            for outcome in ("completed", "failed", "cancelled")
        )
    for outcome in ("attempted", "completed", "failed", "cancelled"):
        assert usage[f"sandbox_sdk_calls_{outcome}"] == sum(
            usage[f"sandbox_{operation}_{outcome}"]
            for operation in ("image_use", "run", "read")
        )


async def test_actual_sdk_boundaries_count_once_with_nonzero_exit_separate():
    usage = {"requests": 2, "input_tokens": 40, "output_tokens": 10}
    provider = local_provider(usage)
    child = sdk_state("child", exit_code=1, read=AsyncMock(return_value=b"retained source"))
    prepared = sdk_state("prepared", run=AsyncMock(return_value=child))
    image = sdk_state("image", run=AsyncMock(return_value=prepared))
    provider._sdk = SimpleNamespace(images=SimpleNamespace(use=AsyncMock(return_value=image)))

    baseline = await provider.create_base("python:test", "setup")
    result = await provider.run(baseline, "write files; run checks", timeout_seconds=10)
    assert await provider.read(result.state, "/source.py") == b"retained source"

    assert provider.usage is usage
    assert usage["requests"] == 2 and usage["input_tokens"] == 40
    assert usage["sandbox_usage_version"] == 1
    assert usage["sandbox_sdk_calls_attempted"] == 4
    assert usage["sandbox_sdk_calls_completed"] == 4
    assert usage["sandbox_image_use_attempted"] == usage["sandbox_read_attempted"] == 1
    assert usage["sandbox_run_attempted"] == 2
    assert usage["sandbox_run_exit_zero"] == usage["sandbox_run_exit_nonzero"] == 1
    assert not any("fork" in key or "write" in key or "metrics" in key for key in usage)
    provider._sdk.images.use.assert_awaited_once_with("python:test")
    image.run.assert_awaited_once()
    prepared.run.assert_awaited_once()
    child.read.assert_awaited_once_with("/source.py")
    assert_settled(usage)


async def test_failed_setup_is_completed_sdk_call_with_nonzero_command_exit():
    provider = local_provider()
    image = sdk_state("image", run=AsyncMock(return_value=sdk_state("failed", exit_code=2)))
    provider._sdk = SimpleNamespace(images=SimpleNamespace(use=AsyncMock(return_value=image)))
    with pytest.raises(ProviderUnavailable, match="baseline setup failed"):
        await provider.create_base("python:test", "bad setup")
    assert provider.usage["sandbox_sdk_calls_completed"] == 2
    assert provider.usage["sandbox_sdk_calls_failed"] == 0
    assert provider.usage["sandbox_run_exit_nonzero"] == 1
    assert provider._states == {}
    assert_settled(provider.usage)


@pytest.mark.parametrize("operation", ["image_use", "run", "read"])
async def test_sdk_exceptions_remain_failed_attempts_and_are_reraised(operation):
    provider = local_provider()
    failure = RuntimeError("SDK request failed")
    call = AsyncMock(side_effect=failure)
    provider._sdk = SimpleNamespace(images=SimpleNamespace(use=call))
    provider._states["parent"] = SimpleNamespace(run=call, read=call)
    with pytest.raises(RuntimeError, match="SDK request failed") as caught:
        if operation == "image_use":
            await provider.create_base("python:test", "setup")
        elif operation == "run":
            await provider.run(SandboxState("parent"), "command", timeout_seconds=10)
        else:
            await provider.read(SandboxState("parent"), "/source.py")
    assert caught.value is failure
    assert provider.usage[f"sandbox_{operation}_attempted"] == 1
    assert provider.usage["sandbox_sdk_calls_failed"] == 1
    assert provider.usage["sandbox_sdk_calls_completed"] == 0
    assert provider.usage["sandbox_run_exit_zero"] == 0
    assert_settled(provider.usage)


async def test_unknown_checkpoint_and_unopened_provider_do_not_invent_sdk_calls():
    provider = local_provider()
    with pytest.raises(ProviderUnavailable, match="async context manager"):
        await provider.create_base("python:test", "setup")
    with pytest.raises(ProviderUnavailable, match="Unknown"):
        await provider.run(SandboxState("unknown"), "command", timeout_seconds=10)
    with pytest.raises(ProviderUnavailable, match="Unknown"):
        await provider.read(SandboxState("unknown"), "/source.py")
    assert provider.usage["sandbox_usage_version"] == 1
    assert provider.usage["sandbox_sdk_calls_attempted"] == 0
    assert_settled(provider.usage)


async def test_cancelled_call_is_observed_and_propagates_without_success():
    provider = local_provider()
    started = asyncio.Event()

    async def blocked(**kwargs):
        started.set()
        await asyncio.Event().wait()

    provider._states["parent"] = SimpleNamespace(run=blocked)
    task = asyncio.create_task(provider.run(SandboxState("parent"), "wait", timeout_seconds=10))
    await asyncio.wait_for(started.wait(), timeout=1)
    assert provider.usage["sandbox_run_attempted"] == 1
    assert provider.usage["sandbox_run_completed"] == 0
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert provider.usage["sandbox_run_cancelled"] == 1
    assert provider.usage["sandbox_run_failed"] == 0
    assert_settled(provider.usage)


async def test_parallel_branches_share_only_their_own_provider_counters():
    first, second = local_provider(), local_provider()

    async def child(**kwargs):
        await asyncio.sleep(0)
        return sdk_state("child")

    first._states["parent"] = SimpleNamespace(run=child)
    second._states["parent"] = SimpleNamespace(run=child)
    await asyncio.gather(
        *(first.run(SandboxState("parent"), "check", timeout_seconds=10) for _ in range(3)),
        second.run(SandboxState("parent"), "check", timeout_seconds=10),
    )
    assert first.usage is not second.usage
    assert first.usage["sandbox_run_completed"] == 3
    assert second.usage["sandbox_run_completed"] == 1
    assert_settled(first.usage)
    assert_settled(second.usage)
