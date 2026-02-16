"""
Schemas Pydantic usados na API de currículos.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Payload enviado ao n8n
# ---------------------------------------------------------------------------
class N8NPayload(BaseModel):
    """Corpo da requisição enviada ao webhook do n8n."""

    resume_text: str = Field(..., description="Texto extraído do currículo")
    adjust: bool = Field(
        False, description="Se True, solicita reescrita; se False, apenas análise"
    )


# ---------------------------------------------------------------------------
# Resposta recebida do n8n
# ---------------------------------------------------------------------------
class N8NResponse(BaseModel):
    """Resposta esperada do webhook do n8n."""

    analysis: str = Field("", description="Texto da análise do currículo")
    suggestions: str = Field(
        "", description="Sugestões de melhoria (texto livre)"
    )
    score: int | None = Field(
        None, description="Nota atribuída ao currículo (0-10)"
    )
    rewritten_resume: str = Field(
        "", description="Currículo reescrito (preenchido quando adjust=True)"
    )


# ---------------------------------------------------------------------------
# Resposta da API (modo análise)
# ---------------------------------------------------------------------------
class AnalysisResponse(BaseModel):
    """Resposta devolvida ao cliente quando adjust=False."""

    analysis: str = Field(
        ...,
        description="Texto completo da análise do currículo (pontos fortes, fracos e sugestões)",
        json_schema_extra={"example": "1) Pontos fortes\n- Experiência com IA e automação...\n\n2) Pontos fracos\n- Falta de métricas...\n\n3) Sugestões..."},
    )
    suggestions: str = Field(
        "",
        description="Sugestões de melhoria em texto livre",
        json_schema_extra={"example": "Corrigir formatação, incluir métricas, adicionar GitHub..."},
    )
    score: int | None = Field(
        None,
        description="Nota geral do currículo de 0 a 10",
        ge=0,
        le=10,
        json_schema_extra={"example": 7},
    )

    model_config = {"json_schema_extra": {
        "example": {
            "analysis": "1) Pontos fortes\n- Experiência com IA...\n2) Pontos fracos\n- Formatação...\n3) Sugestões...\n4) Avaliação geral...",
            "suggestions": "Corrigir formatação, incluir métricas de impacto, adicionar GitHub...",
            "score": 7,
        }
    }}


# ---------------------------------------------------------------------------
# Resposta genérica de erro
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Corpo padrão de respostas de erro."""

    detail: str
