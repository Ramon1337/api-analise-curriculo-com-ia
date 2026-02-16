"""
Ponto de entrada da aplicação FastAPI – Resume AI Backend.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings, logger
from app.routes.resume import router as resume_router

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Cria e configura a instância FastAPI."""

    settings = get_settings()

    app = FastAPI(
        title="Resume AI Backend",
        description=(
            "API para análise e ajuste de currículos com IA, "
            "integrada ao n8n como orquestrador."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ----- CORS -----------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----- Rotas ----------------------------------------------------------
    app.include_router(resume_router)

    # ----- Health check ---------------------------------------------------
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    logger.info("Resume AI Backend inicializado com sucesso")

    return app


# Instância usada pelo uvicorn
app: FastAPI = create_app()
