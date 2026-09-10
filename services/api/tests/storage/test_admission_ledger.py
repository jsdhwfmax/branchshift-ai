import asyncio
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.config import Settings
from app.domain.models import RunSummary
from app.storage.admission import AdmissionDenied, http_admission
from app.storage.repositories import RunRepository


def test_independent_connections_atomically_compete_for_last_slot(tmp_path):
    url = f"sqlite:///{tmp_path / 'race.db'}"
    config = Settings(database_url=url, http_daily_run_limit=1)
    repositories = [RunRepository(url), RunRepository(url)]
    barrier = threading.Barrier(2)

    def compete(index):
        async def create():
            with http_admission(config, f"198.51.100.{index}"):
                return await repositories[index].create_run(RunSummary(
                    id=f"race-{index}", repo_url="https://github.com/owner/repo",
                ))

        barrier.wait(timeout=5)
        try:
            asyncio.run(create())
            return "accepted"
        except AdmissionDenied:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(compete, range(2)))
    for repository in repositories:
        repository.close()
    assert sorted(results) == ["accepted", "denied"]
    with sqlite3.connect(tmp_path / "race.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM http_admissions").fetchone()[0] == 1


async def test_run_insert_failure_rolls_back_admission_together(tmp_path):
    url = f"sqlite:///{tmp_path / 'rollback.db'}"
    repository = RunRepository(url)
    config = Settings(database_url=url, http_daily_run_limit=1)
    await repository.create_run(RunSummary(id="existing", repo_url="https://github.com/owner/repo"))
    with http_admission(config, "198.51.100.1"), pytest.raises(sqlite3.IntegrityError):
        await repository.create_run(RunSummary(id="existing", repo_url="https://github.com/owner/repo"))
    with sqlite3.connect(tmp_path / "rollback.db") as connection:
        assert connection.execute("SELECT COUNT(*) FROM http_admissions").fetchone()[0] == 0
    with http_admission(config, "198.51.100.1"):
        await repository.create_run(RunSummary(id="new", repo_url="https://github.com/owner/repo"))
    repository.close()
