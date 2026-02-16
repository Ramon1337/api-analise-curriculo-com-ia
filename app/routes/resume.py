"""
Rotas relacionadas a currículos — análise e ajuste via n8n.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from requests.exceptions import ConnectionError, ReadTimeout

from app.core.config import get_settings
from app.schemas.resume_schema import AnalysisResponse, ErrorResponse
from app.services import n8n_client, pdf_service, resume_parser

logger = logging.getLogger("resume-ai.routes.resume")

router = APIRouter(prefix="/resume", tags=["Resume"])


# ---------------------------------------------------------------------------
# POST /resume/analyze
# ---------------------------------------------------------------------------
@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analisa ou ajusta um currículo",
    description=(
        "Recebe um arquivo PDF ou texto (.txt), envia para o n8n (orquestrador de IA) "
        "e devolve:\n\n"
        "- **adjust=False** → JSON com `analysis`, `suggestions` e `score` (0-10)\n"
        "- **adjust=True** → PDF com o currículo reescrito\n\n"
        "O campo `score` contém a nota geral atribuída pela IA ao currículo."
    ),
    responses={
        200: {
            "description": "Análise em JSON (adjust=False) ou PDF ajustado (adjust=True)",
            "content": {
                "application/json": {
                    "schema": AnalysisResponse.model_json_schema(),
                    "example": {
                        "analysis": "1) Pontos fortes\n- Experiência com IA...\n2) Pontos fracos...\n3) Sugestões...",
                        "suggestions": "Corrigir formatação, incluir métricas...",
                        "score": 7,
                    },
                },
                "application/pdf": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
        },
        400: {"model": ErrorResponse, "description": "Arquivo inválido ou formato não suportado"},
        413: {"model": ErrorResponse, "description": "Arquivo excede o limite de tamanho"},
        500: {"model": ErrorResponse, "description": "Erro de conexão ou timeout com o serviço de IA (n8n)"},
    },
)
async def analyze_resume(
    file: UploadFile = File(..., description="Currículo em PDF ou texto (.txt)"),
    adjust: bool = Form(False, description="Se True, retorna PDF reescrito"),
):
    """Endpoint principal de análise / ajuste de currículo."""

    settings = get_settings()

    # ------------------------------------------------------------------
    # 1. Leitura e validação de tamanho
    # ------------------------------------------------------------------
    content: bytes = await file.read()

    if len(content) > settings.max_file_size_bytes:
        logger.warning(
            "Arquivo rejeitado por tamanho: %d bytes (limite: %d bytes)",
            len(content),
            settings.max_file_size_bytes,
        )
        raise HTTPException(
            status_code=413,
            detail=(
                f"O arquivo excede o limite de {settings.MAX_FILE_SIZE_MB} MB. "
                f"Tamanho recebido: {len(content) / (1024 * 1024):.2f} MB."
            ),
        )

    # ------------------------------------------------------------------
    # 2. Extração de texto
    # ------------------------------------------------------------------
    try:
        resume_text: str = resume_parser.extract_text_from_upload(
            content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "unknown",
        )
    except ValueError as exc:
        logger.warning("Falha na extração de texto: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    # ------------------------------------------------------------------
    # 3. Envio para n8n
    # ------------------------------------------------------------------
    try:
        n8n_response = n8n_client.send_resume(text=resume_text, adjust=adjust)
    except ConnectionError as exc:
        logger.error("Erro de conexão com n8n: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Não foi possível conectar ao serviço de IA (n8n). Tente novamente mais tarde.",
        )
    except ReadTimeout as exc:
        logger.error("Timeout do n8n: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="O serviço de IA demorou demais para responder. Tente novamente.",
        )
    except RuntimeError as exc:
        logger.error("Erro do n8n: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Erro no serviço de IA: {exc}",
        )

    # ------------------------------------------------------------------
    # 4. Resposta
    # ------------------------------------------------------------------
    if adjust and n8n_response.rewritten_resume:
        # Tenta extrair nome do candidato da primeira linha do texto original
        first_line = resume_text.strip().split("\n")[0].strip()
        candidate_name = first_line if len(first_line) < 60 else "Candidato"

        pdf_path: Path = pdf_service.generate_resume_pdf(
            candidate_name=candidate_name,
            resume_text=n8n_response.rewritten_resume,
        )

        logger.info("Retornando PDF ajustado: %s", pdf_path)

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename="curriculo_ajustado.pdf",
            background=_cleanup_task(pdf_path),
        )

    # Modo análise → JSON
    logger.info("Retornando análise em JSON")
    return AnalysisResponse(
        analysis=n8n_response.analysis,
        suggestions=n8n_response.suggestions,
        score=n8n_response.score,
    )


# ---------------------------------------------------------------------------
# Helper: limpeza do arquivo temporário após envio
# ---------------------------------------------------------------------------
from starlette.background import BackgroundTask


def _cleanup_task(path: Path) -> BackgroundTask:
    """Cria uma BackgroundTask que remove o arquivo temporário após o envio."""

    def _remove() -> None:
        try:
            os.unlink(path)
            logger.debug("Arquivo temporário removido: %s", path)
        except OSError:
            logger.warning("Não foi possível remover %s", path)

    return BackgroundTask(_remove)
