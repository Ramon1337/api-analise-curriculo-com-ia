"""
Cliente HTTP para comunicação com o webhook do n8n.
"""

from __future__ import annotations

import logging

import requests
from requests.exceptions import ConnectionError, ReadTimeout

from app.core.config import get_settings
from app.schemas.resume_schema import N8NPayload, N8NResponse

logger = logging.getLogger("resume-ai.n8n_client")


def send_resume(text: str, adjust: bool) -> N8NResponse:
    """
    Envia o texto do currículo para o webhook do n8n e devolve a resposta
    estruturada.

    Raises
    ------
    ConnectionError
        Quando não é possível conectar ao n8n.
    ReadTimeout
        Quando o n8n não responde dentro do tempo configurado.
    RuntimeError
        Quando o n8n retorna status diferente de 2xx.
    """
    settings = get_settings()

    payload = N8NPayload(resume_text=text, adjust=adjust)
    url = settings.N8N_WEBHOOK_URL

    logger.info(
        "Enviando currículo para n8n | adjust=%s | url=%s | timeout=%ss",
        adjust,
        url,
        settings.TIMEOUT_SECONDS,
    )

    try:
        response = requests.post(
            url,
            json=payload.model_dump(),
            timeout=settings.TIMEOUT_SECONDS,
        )
    except ConnectionError as exc:
        logger.error("Falha de conexão com n8n: %s", exc)
        raise ConnectionError(f"Não foi possível conectar ao n8n em {url}") from exc
    except ReadTimeout as exc:
        logger.error("Timeout ao aguardar resposta do n8n: %s", exc)
        raise ReadTimeout(
            f"n8n não respondeu em {settings.TIMEOUT_SECONDS}s"
        ) from exc

    if not response.ok:
        logger.error(
            "n8n retornou status %s: %s", response.status_code, response.text
        )
        raise RuntimeError(
            f"n8n retornou erro HTTP {response.status_code}: {response.text}"
        )

    raw = response.json()
    logger.info("Resposta recebida do n8n com sucesso")

    # ---------------------------------------------------------------
    # O n8n pode devolver formatos diferentes. Normaliza para dict:
    #   - Array:  [{"output": "..."}]  → pega o primeiro elemento
    #   - Objeto: {"output": "..."}    → usa direto
    #   - Objeto: {"analysis": "...", "suggestions": "...", "score": N}
    # ---------------------------------------------------------------
    if isinstance(raw, list):
        data = raw[0] if raw else {}
    else:
        data = raw

    logger.debug("Dados recebidos do n8n (normalizado): %s", str(data)[:500])

    # Se a resposta vier com campo "output" (texto único do n8n),
    # mapeia para os campos esperados pelo schema.
    if "output" in data and "analysis" not in data:
        output_text: str = data["output"]
        return N8NResponse(
            analysis=output_text,
            suggestions=output_text,
            score=data.get("score"),
            rewritten_resume=output_text if adjust else "",
        )

    # Formato: {"analysis": "...", "suggestions": "...", "score": N}
    return N8NResponse(
        analysis=data.get("analysis", ""),
        suggestions=data.get("suggestions", ""),
        score=data.get("score"),
        rewritten_resume=data.get("rewritten_resume", "") or (
            data.get("analysis", "") if adjust else ""
        ),
    )
