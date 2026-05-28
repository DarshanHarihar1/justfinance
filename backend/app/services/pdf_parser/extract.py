from __future__ import annotations

import io
from collections import defaultdict

import pdfplumber

from .types import LogicalRow

# Calibrated from the canonical fixture (page 0 word positions).
_DATE_COL_MAX = 130.0
_DETAIL_COL_MAX = 400.0


def extract_raw_text(pdf_bytes: bytes) -> str:
    """Concatenate per-page ``extract_text()`` output for ``statements.raw_text``."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return raw_text_from_pdf(pdf)


def extract_logical_rows(pdf_bytes: bytes) -> list[LogicalRow]:
    """Split each page into Date / Details / Amount columns via word positions."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return logical_rows_from_pdf(pdf)


def raw_text_from_pdf(pdf: pdfplumber.PDF) -> str:
    pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages)


def logical_rows_from_pdf(pdf: pdfplumber.PDF) -> list[LogicalRow]:
    rows: list[LogicalRow] = []
    for page in pdf.pages:
        rows.extend(_logical_rows_from_page(page))
    return rows


def _logical_rows_from_page(page: pdfplumber.page.Page) -> list[LogicalRow]:
    by_top: dict[float, list[dict[str, object]]] = defaultdict(list)
    for word in page.extract_words():
        by_top[round(float(word["top"]), 0)].append(word)

    out: list[LogicalRow] = []
    for top in sorted(by_top):
        words = sorted(by_top[top], key=lambda w: float(w["x0"]))
        date_parts: list[str] = []
        detail_parts: list[str] = []
        amount_parts: list[str] = []
        for word in words:
            x0 = float(word["x0"])
            text = str(word["text"])
            if x0 < _DATE_COL_MAX:
                date_parts.append(text)
            elif x0 < _DETAIL_COL_MAX:
                detail_parts.append(text)
            else:
                amount_parts.append(text)
        date_s = " ".join(date_parts).strip()
        detail_s = " ".join(detail_parts).strip()
        amount_s = " ".join(amount_parts).strip()
        if date_s or detail_s or amount_s:
            out.append(LogicalRow(date=date_s, detail=detail_s, amount=amount_s))
    return out
