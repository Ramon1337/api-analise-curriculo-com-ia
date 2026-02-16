"""
Configurações centrais da aplicação.
Carrega variáveis de ambiente via python-dotenv e expõe via Pydantic Settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Logging estruturado
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("resume-ai")

# ---------------------------------------------------------------------------
# Diretório raiz do projeto (resume-ai-backend/)
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Configurações carregadas do arquivo .env na raiz do projeto."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- n8n ---------------------------------------------------------------
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/resume"
    TIMEOUT_SECONDS: int = 120

    # ---- Upload ------------------------------------------------------------
    MAX_FILE_SIZE_MB: int = 5  # limite em megabytes

    # ---- CORS --------------------------------------------------------------
    CORS_ORIGINS: list[str] = ["*"]

    # ---- Futuro JWT --------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ---- helpers -----------------------------------------------------------
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Singleton cacheado das configurações."""
    return Settings()
