"""
Serviço de geração de PDF com layout profissional usando ReportLab.

Layout inspirado em currículo executivo com:
  - Nome grande no topo + dados de contato
  - Seções com ícone circular colorido + título em caixa alta marrom
  - Linha separadora sob cada título de seção
  - Bullets vermelhos para itens de lista
  - Seção de habilidades em duas colunas
"""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger("resume-ai.pdf_service")

# ---------------------------------------------------------------------------
# Cores do tema
# ---------------------------------------------------------------------------
COLOR_PRIMARY = colors.HexColor("#1B2A4A")  # Azul marinho escuro
COLOR_ACCENT = colors.HexColor("#1B2A4A")   # Azul marinho para bullets
COLOR_TEXT = colors.HexColor("#2C2C2C")      # Texto principal
COLOR_LIGHT_TEXT = colors.HexColor("#555555") # Texto secundário
COLOR_LINE = colors.HexColor("#1B2A4A")      # Linha separadora

# Largura útil do documento (A4 - margens)
PAGE_WIDTH = A4[0] - 2 * 2 * cm  # ~17 cm

# ---------------------------------------------------------------------------
# Estilos customizados
# ---------------------------------------------------------------------------
_styles = getSampleStyleSheet()

STYLE_NAME = ParagraphStyle(
    "ResumeName",
    parent=_styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=24,
    leading=28,
    alignment=TA_LEFT,
    spaceAfter=2,
    textColor=COLOR_TEXT,
)

STYLE_CONTACT = ParagraphStyle(
    "ResumeContact",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=TA_LEFT,
    spaceAfter=8,
    textColor=COLOR_LIGHT_TEXT,
)

STYLE_SECTION_TITLE = ParagraphStyle(
    "SectionTitle",
    parent=_styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    spaceBefore=10,
    spaceAfter=2,
    textColor=COLOR_PRIMARY,
    leftIndent=0,
)

STYLE_BODY = ParagraphStyle(
    "ResumeBody",
    parent=_styles["BodyText"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=13,
    alignment=TA_JUSTIFY,
    spaceAfter=4,
    textColor=COLOR_TEXT,
)

STYLE_JOB_TITLE = ParagraphStyle(
    "JobTitle",
    parent=_styles["Normal"],
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    spaceAfter=2,
    spaceBefore=6,
    textColor=COLOR_TEXT,
)

STYLE_JOB_META = ParagraphStyle(
    "JobMeta",
    parent=_styles["Normal"],
    fontName="Helvetica-Oblique",
    fontSize=9,
    leading=12,
    spaceAfter=2,
    textColor=COLOR_LIGHT_TEXT,
)

STYLE_BULLET = ParagraphStyle(
    "BulletItem",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=13,
    alignment=TA_JUSTIFY,
    spaceAfter=2,
    textColor=COLOR_TEXT,
    leftIndent=14,
    firstLineIndent=0,
    bulletIndent=0,
)

STYLE_SKILL_ITEM = ParagraphStyle(
    "SkillItem",
    parent=_styles["Normal"],
    fontName="Helvetica",
    fontSize=9.5,
    leading=13,
    textColor=COLOR_TEXT,
)


# ---------------------------------------------------------------------------
# Flowable customizado: círculo colorido + título de seção + linha
# ---------------------------------------------------------------------------
class SectionHeader(Flowable):
    """Desenha: ● TÍTULO DA SEÇÃO  seguido de uma linha horizontal."""

    def __init__(self, title: str, width: float = PAGE_WIDTH):
        super().__init__()
        self.title = title.upper()
        self.width = width
        self.height = 20

    def draw(self):
        canvas = self.canv
        # Texto do título
        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(COLOR_PRIMARY)
        canvas.drawString(0, self.height - 11, self.title)
        # Linha separadora
        canvas.setStrokeColor(COLOR_LINE)
        canvas.setLineWidth(0.8)
        canvas.line(0, 0, self.width, 0)


class BulletPoint(Flowable):
    """Desenha um pequeno bullet vermelho seguido de texto (como Paragraph)."""

    def __init__(self, text: str, style: ParagraphStyle, width: float = PAGE_WIDTH):
        super().__init__()
        self._text = text
        self._style = style
        self._width = width
        # Cria parágrafo com indentação para o texto
        self._para = Paragraph(text, style)
        w, h = self._para.wrap(width - 14, 1000)
        self.height = h
        self._para_height = h
        self._para_width = w

    def wrap(self, availWidth, availHeight):
        self._para = Paragraph(self._text, self._style)
        w, h = self._para.wrap(availWidth - 14, availHeight)
        self.height = h
        self._para_height = h
        return availWidth, h

    def draw(self):
        canvas = self.canv
        # Bullet vermelho
        canvas.setFillColor(COLOR_ACCENT)
        canvas.circle(4, self._para_height - 5, 2.2, fill=1, stroke=0)
        # Texto
        self._para.drawOn(canvas, 14, 0)


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------

_SECTION_PATTERNS = [
    r"(?i)^resum[o|é]\s*profissional",
    r"(?i)^experi[eê]ncia\s*profissional",
    r"(?i)^forma[çc][aã]o\s*acad[eê]mica",
    r"(?i)^habilidades",
    r"(?i)^compet[eê]ncias",
    r"(?i)^softwares?\s*(e\s*ferramentas)?",
    r"(?i)^ferramentas",
    r"(?i)^idiomas",
    r"(?i)^certifica[çc][oõ]es",
    r"(?i)^cursos",
    r"(?i)^projetos",
    r"(?i)^objetivo",
    r"(?i)^informa[çc][oõ]es?\s*(adicionais|pessoais|complementares)",
    r"(?i)^links?\s*(e\s*refer[eê]ncias)?",
    r"(?i)^refer[eê]ncias",
    r"(?i)^atividades",
    r"(?i)^trabalhos?\s*volunt",
]


def _sanitize_text(text: str) -> str:
    """Substitui caracteres Unicode problemáticos por equivalentes ASCII.

    Helvetica (fonte padrão do ReportLab) não suporta vários caracteres
    Unicode como em-dash, en-dash, aspas curvas etc., que aparecem como
    caixinhas pretas no PDF.
    """
    replacements = {
        "\u2013": "-",   # en-dash  –
        "\u2014": "-",   # em-dash  —
        "\u2015": "-",   # horizontal bar
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201C": '"',   # left double quote
        "\u201D": '"',   # right double quote
        "\u2022": "-",   # bullet •
        "\u2026": "...", # ellipsis …
        "\u00A0": " ",   # non-breaking space
        "\u200B": "",    # zero-width space
        "\u00AD": "-",   # soft hyphen
        "\uFEFF": "",    # BOM
        "\u2010": "-",   # hyphen
        "\u2011": "-",   # non-breaking hyphen
        "\u2012": "-",   # figure dash
        "\u2500": "-",   # box drawing horizontal
        "\u25AA": "-",   # black small square ▪
        "\u25BA": "-",   # black right-pointing pointer ►
        "\u25CF": "-",   # black circle ●
        "\u2011": "-",   # non-breaking hyphen
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _extract_section_title(line: str) -> tuple[str, str]:
    """Extrai o título da seção e possível conteúdo inline.

    Ex: 'Ferramentas e Práticas: Git, Postman, VS Code'
    -> ('Ferramentas e Práticas', 'Git, Postman, VS Code')

    Ex: 'Experiência Profissional'
    -> ('Experiência Profissional', '')
    """
    stripped = line.strip()
    # Se contém ':', verificar se o conteúdo pós-':' é longo (items inline)
    if ":" in stripped:
        parts = stripped.split(":", 1)
        title_part = parts[0].strip()
        content_part = parts[1].strip() if len(parts) > 1 else ""
        # Se a parte após ':' é conteúdo significativo (>10 chars),
        # separar como título + conteúdo
        if len(content_part) > 10:
            return title_part, content_part
    return stripped.rstrip(":"), ""


def _is_section_header(line: str) -> bool:
    """Verifica se a linha parece ser um título de seção do currículo."""
    stripped = line.strip()
    # Extrair apenas a parte do título (antes de ':')
    title_part = stripped.split(":", 1)[0].strip() if ":" in stripped else stripped
    title_part = title_part.rstrip(":")
    if not title_part:
        return False
    # Linha curta toda em caixa alta
    if title_part.isupper() and len(title_part) < 60:
        return True
    for pat in _SECTION_PATTERNS:
        if re.match(pat, title_part):
            return True
    return False


def _is_bullet(line: str) -> bool:
    """Verifica se a linha é um item de lista (começa com •, -, *, etc.)."""
    stripped = line.strip()
    return bool(stripped) and stripped[0] in ("•", "-", "–", "—", "*", "►", "▪", "●")


def _clean_bullet_text(line: str) -> str:
    """Remove o marcador de bullet do início da linha."""
    stripped = line.strip()
    if stripped and stripped[0] in ("•", "-", "–", "—", "*", "►", "▪", "●"):
        return stripped[1:].strip()
    return stripped


def _is_contact_line(line: str) -> bool:
    """Detecta se a linha contém informações de contato."""
    lower = line.lower()
    return any(
        kw in lower
        for kw in ["@", "linkedin", "github", "telefone", "tel:", "fone:", "celular"]
    ) or bool(re.search(r"\(\d{2}\)\s*\d{4,5}", line))


def _parse_resume_sections(text: str) -> list[dict]:
    """
    Faz o parse do texto do currículo em blocos estruturados.

    Retorna lista de dicts:
      {"type": "name", "content": "..."}
      {"type": "contact", "content": "..."}
      {"type": "section", "title": "...", "items": [...]}
    Cada item pode ser:
      {"type": "paragraph", "text": "..."}
      {"type": "bullet", "text": "..."}
      {"type": "job_title", "text": "..."}
    """
    lines = text.split("\n")
    sections: list[dict] = []
    current_section: dict | None = None

    # Tentar extrair nome (primeira linha não vazia, geralmente o nome)
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if idx < len(lines):
        name_line = lines[idx].strip()
        sections.append({"type": "name", "content": name_line})
        idx += 1

    # Coletar linhas de contato logo após o nome
    contact_lines = []
    while idx < len(lines):
        line = lines[idx].strip()
        if not line:
            idx += 1
            continue
        if _is_contact_line(line) or (
            not _is_section_header(line) and len(contact_lines) < 3 and not _is_bullet(line)
            and len(line) < 120 and not current_section
        ):
            contact_lines.append(line)
            idx += 1
        else:
            break

    if contact_lines:
        sections.append({"type": "contact", "content": " | ".join(contact_lines)})

    # Processar o restante
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1

        if not line:
            continue

        if _is_section_header(line):
            title, inline_content = _extract_section_title(line)
            current_section = {
                "type": "section",
                "title": title,
                "items": [],
            }
            sections.append(current_section)
            # Se houver conteúdo inline (ex: "Ferramentas: Git, Postman")
            if inline_content:
                current_section["items"].append(
                    {"type": "paragraph", "text": inline_content}
                )
        elif _is_bullet(line):
            text = _clean_bullet_text(line)
            if current_section:
                current_section["items"].append({"type": "bullet", "text": text})
            else:
                # Criar seção implícita
                current_section = {"type": "section", "title": "", "items": []}
                sections.append(current_section)
                current_section["items"].append({"type": "bullet", "text": text})
        else:
            if current_section:
                # Detectar título de cargo/função (ex: "Analista de Sistemas | Empresa")
                if "|" in line and len(line) < 120:
                    current_section["items"].append({"type": "job_title", "text": line})
                else:
                    current_section["items"].append({"type": "paragraph", "text": line})
            else:
                # Texto antes de qualquer seção — tratar como parágrafo solto
                current_section = {"type": "section", "title": "", "items": []}
                sections.append(current_section)
                current_section["items"].append({"type": "paragraph", "text": line})

    return sections


def _build_skills_table(items: list[dict]) -> Table:
    """Constrói tabela de duas colunas para habilidades/competências."""
    bullet_char = '<font color="#1B2A4A">&#8226;</font>&nbsp;'
    texts = [it["text"] for it in items if it.get("text")]

    # Dividir em duas colunas
    mid = (len(texts) + 1) // 2
    col1 = texts[:mid]
    col2 = texts[mid:]

    # Garantir mesmo número de linhas
    while len(col1) < len(col2):
        col1.append("")
    while len(col2) < len(col1):
        col2.append("")

    col_width = PAGE_WIDTH / 2 - 2 * mm
    data = []
    for left, right in zip(col1, col2):
        left_p = Paragraph(
            f"{bullet_char}{left}" if left else "",
            STYLE_SKILL_ITEM,
        )
        right_p = Paragraph(
            f"{bullet_char}{right}" if right else "",
            STYLE_SKILL_ITEM,
        )
        data.append([left_p, right_p])

    table = Table(data, colWidths=[col_width, col_width])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------

def generate_resume_pdf(
    candidate_name: str,
    resume_text: str,
    *,
    output_path: str | Path | None = None,
) -> Path:
    """
    Gera um PDF profissional a partir do texto do currículo.

    O layout segue um modelo executivo com:
      - Nome em destaque + dados de contato
      - Seções com ícone circular + título em caixa alta marrom
      - Bullets vermelhos para itens de lista
      - Habilidades em duas colunas

    Parameters
    ----------
    candidate_name:
        Nome do candidato exibido no topo do PDF.
    resume_text:
        Corpo do currículo (pode conter quebras de linha ``\\n``).
    output_path:
        Caminho opcional para salvar o arquivo. Se omitido, cria um arquivo
        temporário.

    Returns
    -------
    Path
        Caminho absoluto do PDF gerado.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix="resume_"
        )
        output_path = Path(tmp.name)
        tmp.close()
    else:
        output_path = Path(output_path)

    logger.info("Gerando PDF em %s", output_path)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title=f"Currículo – {candidate_name}",
        author="Resume AI",
    )

    story: list = []
    # Sanitizar texto para remover caracteres Unicode problemáticos
    sanitized_text = _sanitize_text(resume_text)
    sections = _parse_resume_sections(sanitized_text)

    for section in sections:
        stype = section["type"]

        if stype == "name":
            story.append(Paragraph(section["content"].upper(), STYLE_NAME))

        elif stype == "contact":
            story.append(Paragraph(section["content"], STYLE_CONTACT))
            story.append(Spacer(1, 4))

        elif stype == "section":
            title = section.get("title", "")
            items = section.get("items", [])

            # Cabeçalho da seção
            if title:
                story.append(Spacer(1, 4))
                story.append(SectionHeader(title))
                story.append(Spacer(1, 6))

            # Detectar se é seção de habilidades/competências → layout 2 colunas
            title_lower = title.lower()
            is_skills = any(
                kw in title_lower
                for kw in ["habilidade", "competência", "competencia", "software", "ferramenta"]
            )
            all_bullets = all(it["type"] == "bullet" for it in items) if items else False

            if is_skills and all_bullets and len(items) >= 4:
                story.append(_build_skills_table(items))
            else:
                for item in items:
                    if item["type"] == "bullet":
                        story.append(BulletPoint(item["text"], STYLE_BULLET))
                    elif item["type"] == "job_title":
                        story.append(Paragraph(item["text"], STYLE_JOB_TITLE))
                    else:
                        story.append(Paragraph(item["text"], STYLE_BODY))

    doc.build(story)
    logger.info("PDF gerado com sucesso: %s", output_path)
    return output_path
