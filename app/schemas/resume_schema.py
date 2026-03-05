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
# Resposta recebida do n8n (estrutura real da IA)
# ---------------------------------------------------------------------------
class N8NResponse(BaseModel):
    """Resposta esperada do webhook do n8n."""

    score: float | None = Field(None, description="Nota atribuída ao currículo (0-10)")
    justificativa_score: str = Field("", description="Justificativa da nota")
    nivel_classificado: str = Field("", description="Nível classificado (ex: Pleno, Júnior, Sênior)")
    pontos_fortes: list[str] = Field(default_factory=list, description="Lista de pontos fortes")
    pontos_fracos: list[str] = Field(default_factory=list, description="Lista de pontos fracos")
    sugestoes_praticas: list[str] = Field(default_factory=list, description="Sugestões práticas de melhoria")
    avaliacao_geral: str = Field("", description="Avaliação geral do currículo")
    rewritten_resume: str = Field("", description="Currículo reescrito (preenchido quando adjust=True)")


# ---------------------------------------------------------------------------
# Resposta da API (modo análise)
# ---------------------------------------------------------------------------
class AnalysisResponse(BaseModel):
    """Resposta devolvida ao cliente quando adjust=False."""

    score: float | None = Field(
        None,
        description="Nota geral do currículo de 0 a 10",
        ge=0,
        le=10,
        json_schema_extra={"example": 7.5},
    )
    justificativa_score: str = Field(
        "",
        description="Justificativa da nota atribuída",
        json_schema_extra={"example": "O currículo apresenta boa estrutura e experiência relevante, mas falta métricas de impacto."},
    )
    nivel_classificado: str = Field(
        "",
        description="Nível profissional classificado pela IA",
        json_schema_extra={"example": "Pleno"},
    )
    pontos_fortes: list[str] = Field(
        default_factory=list,
        description="Lista de pontos fortes identificados",
        json_schema_extra={"example": ["Experiência com IA e automação", "Boa formação acadêmica"]},
    )
    pontos_fracos: list[str] = Field(
        default_factory=list,
        description="Lista de pontos fracos identificados",
        json_schema_extra={"example": ["Falta de métricas de impacto", "Sem link para portfólio"]},
    )
    sugestoes_praticas: list[str] = Field(
        default_factory=list,
        description="Sugestões práticas de melhoria",
        json_schema_extra={"example": ["Incluir métricas nos projetos", "Adicionar link do GitHub"]},
    )
    avaliacao_geral: str = Field(
        "",
        description="Texto de avaliação geral do currículo",
        json_schema_extra={"example": "Currículo bem estruturado com boa experiência, mas precisa de ajustes para se destacar."},
    )

    model_config = {"json_schema_extra": {
        "example": {
            "score": 8,
            "justificativa_score": "O currículo apresenta boa estrutura e experiência relevante.",
            "nivel_classificado": "Pleno",
            "pontos_fortes": ["Experiência com IA", "Boa formação"],
            "pontos_fracos": ["Falta métricas", "Sem portfólio"],
            "sugestoes_praticas": ["Incluir métricas", "Adicionar GitHub"],
            "avaliacao_geral": "Currículo bem estruturado com potencial de melhoria.",
        }
    }}


# ---------------------------------------------------------------------------
# Resposta genérica de erro
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Corpo padrão de respostas de erro."""

    detail: str
