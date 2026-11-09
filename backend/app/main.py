"""FastAPI application factory.

Run locally from the backend/ folder:
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.db import check_database
from app.errors import BadRequestError, NotFoundError, bad_request_handler, not_found_handler
from app.routers import games, meta, mvp, players, teams
from app.services.game_model import GameModel

API_PREFIX = "/api/v1"

DESCRIPTION = """
Read-only API over 26 NBA seasons (2000-01 to 2025-26) of player and team data, plus model output:
leave-one-season-out MVP predictions, player archetypes, and game predictions for the season in
progress that account for each team's injury report (with what-if changes to who plays).

Counting stats ending in `_pg` are per-game averages; fields ending in `_pct` are fractions (0.512 = 51.2%).
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail at startup, not on the first request, if the data or model is missing or incompatible.
    settings: Settings = app.state.settings
    app.state.db_meta = check_database(settings.db_path)
    app.state.game_model = GameModel.from_json(app.state.db_meta["game_model"])
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="NBA Analytics API",
        version="1.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def cache_headers(request: Request, call_next):
        # The data only changes when the pipeline is rebuilt, so successful GETs are safe to cache.
        response = await call_next(request)
        if "cache-control" not in response.headers:
            cacheable = request.method == "GET" and response.status_code == 200
            response.headers["Cache-Control"] = f"public, max-age={settings.cache_max_age}" if cacheable else "no-store"
        return response

    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(BadRequestError, bad_request_handler)

    for module in (meta, players, mvp, teams, games):
        app.include_router(module.router, prefix=API_PREFIX)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
