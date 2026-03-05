"""
Serviço de extração de texto de arquivos de currículo (PDF e texto puro).
"""

from __future__ import annotations

import io
import logging

from PyPDF2 import PdfReader

logger = logging.getLogger("resume-ai.resume_parser")


def extract_text_from_pdf(content: bytes) -> str:
    """
    Extrai texto de um arquivo PDF em memória.

    Parameters
    ----------
    content:
        Bytes do arquivo PDF.

    Returns
    -------
    str
        Texto concatenado de todas as páginas.

    Raises
    ------
    ValueError
        Se o PDF não contiver texto extraível.
    """
    reader = PdfReader(io.BytesIO(content))
    pages_text: list[str] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())
            logger.debug("Página %d: %d caracteres extraídos", page_num, len(text))

    full_text = "\n\n".join(pages_text)

    if not full_text.strip():
        raise ValueError(
            "Não foi possível extrair texto do PDF. "
            "O arquivo pode conter apenas imagens."
        )

    logger.info(
        "Texto extraído do PDF: %d páginas, %d caracteres",
        len(reader.pages),
        len(full_text),
    )
    return full_text


def extract_text_from_docx(content: bytes) -> str:
    """
    Extrai texto de um arquivo DOCX em memória.

    Parameters
    ----------
    content:
        Bytes do arquivo DOCX.

    Returns
    -------
    str
        Texto concatenado de todos os parágrafos.

    Raises
    ------
    ValueError
        Se o DOCX não contiver texto extraível.
    """
    doc = Document(io.BytesIO(content))
    paragraphs_text: list[str] = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    full_text = "\n\n".join(paragraphs_text)

    if not full_text.strip():
        raise ValueError(
            "Não foi possível extrair texto do DOCX. "
            "O arquivo pode estar vazio ou conter apenas imagens."
        )

    logger.info(
        "Texto extraído do DOCX: %d parágrafos, %d caracteres",
        len(paragraphs_text),
        len(full_text),
    )
    return full_text


def extract_text_from_upload(content: bytes, content_type: str, filename: str) -> str:
    """
    Extrai texto de um arquivo enviado pelo usuário.

    Suporta:
    - ``application/pdf``
    - ``application/vnd.openxmlformats-officedocument.wordprocessingml.document`` (DOCX)
    - ``text/plain``

    Parameters
    ----------
    content:
        Bytes do arquivo.
    content_type:
        MIME type do upload.
    filename:
        Nome original do arquivo.

    Returns
    -------
    str
        Texto extraído.

    Raises
    ------
    ValueError
        Se o tipo de arquivo não for suportado ou o texto estiver vazio.
    """
    logger.info("Processando upload: %s (%s)", filename, content_type)

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(content)

    docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if content_type == docx_mime or filename.lower().endswith(".docx"):
        return extract_text_from_docx(content)

    if content_type.startswith("text/") or filename.lower().endswith(".txt"):
        text = content.decode("utf-8", errors="replace").strip()
        if not text:
            raise ValueError("O arquivo de texto está vazio.")
        logger.info("Texto puro lido: %d caracteres", len(text))
        return text

    raise ValueError(
        f"Tipo de arquivo não suportado: {content_type}. "
        "Envie um PDF, DOCX ou arquivo de texto (.txt)."
    )
