from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.body_limit import RunBodyLimitMiddleware
from app.api.health import router as health_router
from app.api.runs import router as runs_router
from app.config import Settings, settings
from app.orchestrator.run_manager import RunManager
from app.static import AppStaticFiles
from app.storage.repositories import RunRepository


def create_app(config: Settings = settings, *, web_dist: Path | None = None) -> FastAPI:
    repository = RunRepository(config.database_url)
    manager = RunManager(repository, config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await manager.recover_interrupted()
        yield
        await manager.shutdown()
        repository.close()

    application = FastAPI(
        title="BranchShift API",
        version="0.1.0",
        description="Evidence-first dependency migration orchestration",
        lifespan=lifespan,
    )
    application.state.settings = config
    application.state.repository = repository
    application.state.manager = manager
    application.add_middleware(RunBodyLimitMiddleware, max_bytes=config.http_max_body_bytes)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    application.include_router(health_router)
    application.include_router(runs_router)

    @application.get("/api")
    async def api_root() -> dict[str, str]:
        return {"name": "BranchShift", "status": "ready"}

    static_directory = web_dist or Path(__file__).resolve().parents[3] / "apps/web/dist"
    if (static_directory / "index.html").is_file():
        application.mount("/", AppStaticFiles(directory=static_directory, html=True), name="web")

    return application


app = create_app()
