"""FastAPI application factory.

Kept separate from route definitions so tests can build the app and use
Starlette's TestClient without binding a network port, and so a production
server (uvicorn/gunicorn) imports a single ``app`` object.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="QueryPilot API",
        description="Conversational SQL analyst agent over PostgreSQL.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.client_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
