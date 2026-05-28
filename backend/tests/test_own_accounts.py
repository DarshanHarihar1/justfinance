from __future__ import annotations

from pathlib import Path

from app.services.categorizer.own_accounts import detect_own_account_last4s


def test_detect_own_accounts_from_fixture_raw_text() -> None:
    pdf = Path(__file__).parent / "fixtures" / "phonepe_sample.pdf"
    from app.services.pdf_parser import parse_phonepe_pdf

    parsed = parse_phonepe_pdf(pdf.read_bytes())
    last4s = detect_own_account_last4s(parsed.raw_text)
    assert "4200" in last4s
    assert "8216" in last4s
