import pytest
from pydantic import ValidationError

from app.domain.models import CreateRunRequest, RunStatus, RunSummary, assert_transition


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://gitlab.com/owner/repo",
        "https://user:pass@github.com/owner/repo",
        "https://github.com:444/owner/repo",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo#readme",
        "https://github.com/owner/repo?ref=main",
    ],
)
def test_repository_url_fails_closed(url):
    with pytest.raises(ValidationError):
        CreateRunRequest(repo_url=url)


def test_repository_url_accepts_public_root():
    request = CreateRunRequest(repo_url="https://github.com/owner/repo")
    assert request.target == "pydantic-v2"


def test_run_transitions_are_ordered():
    assert_transition(RunStatus.QUEUED, RunStatus.PREPARING)
    with pytest.raises(ValueError, match="Invalid run transition"):
        assert_transition(RunStatus.QUEUED, RunStatus.COMPLETED)


@pytest.mark.parametrize(
    "path", [None, "fixtures/pydantic-v1-app", "packages/model_v1.2", "a" * 200]
)
def test_project_path_accepts_bounded_portable_relative_paths(path):
    request = CreateRunRequest(repo_url="https://github.com/owner/repo", project_path=path)
    summary = RunSummary(id="run", repo_url=request.repo_url, project_path=request.project_path)
    assert summary.project_path == path


@pytest.mark.parametrize(
    "path",
    ["", "/absolute", "../outside", "a/../b", ".", "a/./b", "a//b", "a/", "a\\b",
     "space here", "a;echo", "a%2fb", "路径", "a\nb", "a" * 201],
)
def test_project_path_rejects_unsafe_or_ambiguous_paths(path):
    with pytest.raises(ValidationError):
        CreateRunRequest(repo_url="https://github.com/owner/repo", project_path=path)
    with pytest.raises(ValidationError):
        RunSummary(id="run", repo_url="https://github.com/owner/repo", project_path=path)


def test_runtime_snapshot_metadata_roundtrips_and_rejects_invalid_hashes():
    summary = RunSummary(
        id="run", repo_url="https://github.com/owner/repo",
        orchestrator_revision="a" * 40, orchestrator_digest="b" * 64,
        orchestrator_dirty=True, runtime_config_digest="c" * 64,
    )
    assert RunSummary.model_validate_json(summary.model_dump_json()) == summary
    with pytest.raises(ValidationError):
        RunSummary.model_validate({**summary.model_dump(), "orchestrator_digest": "not-sha256"})
