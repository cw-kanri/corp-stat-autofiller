from __future__ import annotations

from pathlib import Path


def extract_pdf_text(path: str | Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("PDF読込には pdfplumber が必要です。") from exc

    texts: list[str] = []
    with pdfplumber.open(Path(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            texts.append(text)
    return "\n".join(texts)

