import pytest
from datetime import date
from decimal import Decimal

from app.services.parsers.airbank_pdf import AirBankPdfParser

# Raw rows exactly as returned by pdfplumber (6 columns).
# Format: [dates_cell, type_code_cell, name_account_cell, details_cell, amount_cell, fees_cell]

STANDING_ORDER = [
    "02.03.2026\n02.03.2026",
    "Trvalý příkaz\n151641036232",
    "120777711 / 0300",                        # just account, no name in Col 2
    "SOS vesničky\nVS140060\nSOS vesničky",    # details (name appears here)
    "-500,00",
    "0,00",
]

INCOMING_WITH_NAME = [
    "02.03.2026\n02.03.2026",
    "Příchozí úhrada\n151663208902",
    "dům sinkulova 12\n5112785001 / 5500",     # name + account
    "VS7653250275\nOsobní výběr Sinkulova 12",
    "3 000,00",
    "0,00",
]

OUTGOING_EMPTY_DETAILS = [
    "06.03.2026\n06.03.2026",
    "Odchozí úhrada\n152172884502",
    "7757000901 / 6363",                       # just account
    "",                                         # empty details
    "-25 000,00",
    "0,00",
]

SIPO = [
    "11.03.2026\n11.03.2026",
    "Inkaso SIPO\n152579099922",
    "Air Bank",                                 # just name, no account
    "SIPO\n1044362983",
    "-212,00",
    "0,00",
]

LARGE_AMOUNT = [
    "03.03.2026\n03.03.2026",
    "Příchozí úhrada\n151800655262",
    "Anela Cosmetics s.r.\n2103271662 / 2010",
    "VS7413769\n001 - Andrea Pajgrt Bartosova - Dob",
    "21 478,00",
    "0,00",
]


def test_standing_order_debit():
    """Account-only in Col 2; name appears in details."""
    row = AirBankPdfParser()._parse_row(STANDING_ORDER)
    assert row.booking_date == date(2026, 3, 2)
    assert row.value_date == date(2026, 3, 2)
    assert row.amount == Decimal("-500.00")
    assert row.currency == "CZK"
    assert row.counterparty_name is None           # name not in Col 2
    assert row.counterparty_account == "120777711 / 0300"
    assert row.description == "SOS vesničky\nVS140060\nSOS vesničky"
    assert row.raw_reference == "151641036232"


def test_incoming_name_and_account_in_col2():
    """Name + account both in Col 2."""
    row = AirBankPdfParser()._parse_row(INCOMING_WITH_NAME)
    assert row.booking_date == date(2026, 3, 2)
    assert row.value_date == date(2026, 3, 2)
    assert row.amount == Decimal("3000.00")
    assert row.currency == "CZK"
    assert row.counterparty_name == "dům sinkulova 12"
    assert row.counterparty_account == "5112785001 / 5500"
    assert row.description == "VS7653250275\nOsobní výběr Sinkulova 12"
    assert row.raw_reference == "151663208902"


def test_outgoing_empty_details_falls_back_to_type():
    """Empty details cell → description falls back to transaction type."""
    row = AirBankPdfParser()._parse_row(OUTGOING_EMPTY_DETAILS)
    assert row.booking_date == date(2026, 3, 6)
    assert row.amount == Decimal("-25000.00")
    assert row.counterparty_name is None
    assert row.counterparty_account == "7757000901 / 6363"
    assert row.description == "Odchozí úhrada"    # fallback to type
    assert row.raw_reference == "152172884502"


def test_sipo_name_only_no_account():
    """Name only in Col 2 (no account number)."""
    row = AirBankPdfParser()._parse_row(SIPO)
    assert row.booking_date == date(2026, 3, 11)
    assert row.amount == Decimal("-212.00")
    assert row.counterparty_name == "Air Bank"
    assert row.counterparty_account is None
    assert row.description == "SIPO\n1044362983"
    assert row.raw_reference == "152579099922"


def test_large_amount_with_space_thousands_separator():
    row = AirBankPdfParser()._parse_row(LARGE_AMOUNT)
    assert row.amount == Decimal("21478.00")
    assert row.counterparty_name == "Anela Cosmetics s.r."
    assert row.counterparty_account == "2103271662 / 2010"


def test_is_data_row_skips_first_header():
    parser = AirBankPdfParser()
    assert parser._is_data_row(["Zaúčtování", "Typ", "Název", None, None, None]) is False


def test_is_data_row_skips_second_header():
    parser = AirBankPdfParser()
    assert parser._is_data_row(["Provedení", "Kód transakce", "Číslo účtu / debetní karty", "Detaily", "Částka CZK", "Poplatky"]) is False


def test_is_data_row_skips_empty():
    parser = AirBankPdfParser()
    assert parser._is_data_row([]) is False
    assert parser._is_data_row([None] * 6) is False


def test_is_data_row_accepts_transaction():
    parser = AirBankPdfParser()
    assert parser._is_data_row(STANDING_ORDER) is True


def test_integration_real_pdf():
    """Parse the real AirBank PDF and verify basic counts/values.

    Skipped in CI — the PDF contains real bank data and is not committed.
    Place data/Attachment-1.pdf at the repo root to run locally.
    """
    import pathlib
    pdf_path = pathlib.Path(__file__).parent.parent.parent / "data" / "Attachment-1.pdf"
    if not pdf_path.exists():
        pytest.skip("data/Attachment-1.pdf not found (real bank data, not committed)")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    rows = AirBankPdfParser().parse(pdf_bytes)
    assert len(rows) == 15
    for row in rows:
        assert row.booking_date is not None
        assert row.amount != 0
        assert row.currency == "CZK"
    first = rows[0]
    assert first.amount == Decimal("-500.00")
    assert first.counterparty_account == "120777711 / 0300"
