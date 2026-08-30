import pytest
from pydantic import ValidationError

from app.domain.models import CreateRunRequest, RunStatus, assert_transition


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/owner/repo",
        "https://gitlab.com/owner/repo",
        "https://user:pass@github.com/owner/repo",
        "https://github.com:444/owner/repo",
        "https://github.com/owner/repo/tree/main",
        "https://github.com/owner/repo#readme",
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

