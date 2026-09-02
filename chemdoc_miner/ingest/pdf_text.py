from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pdfplumber


def extract_pdf_text(path: Path, *, ocr_if_empty: bool = True) -> tuple[str, int, str]:
    """Return (text, page_count, method). method is 'text' or 'ocr'."""
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        parts = [(page.extract_text() or "") for page in pdf.pages]
        text = "\n".join(parts).strip()
    if len(text) >= 40:
        return text, page_count, "text"
    if ocr_if_empty:
        ocr = _ocr_pdf(path)
        if len(ocr.strip()) >= 40:
            return ocr.strip(), page_count, "ocr"
    return text, page_count, "text"


def _ocr_pdf(path: Path) -> str:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return ""
    try:
        pdf = pdfium.PdfDocument(str(path))
    except Exception:
        return ""
    chunks: list[str] = []
    try:
        for index in range(len(pdf)):
            image = pdf[index].render(scale=2).to_pil()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                image.save(handle.name)
                tmp_name = handle.name
            result = subprocess.run(
                ["tesseract", tmp_name, "stdout", "-l", "eng"],
                capture_output=True,
                text=True,
                check=False,
            )
            Path(tmp_name).unlink(missing_ok=True)
            if result.returncode == 0:
                chunks.append(result.stdout)
    finally:
        pdf.close()
    return "\n".join(chunks)
