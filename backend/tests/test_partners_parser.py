import pytest
from datetime import date
from decimal import Decimal

from app.services.parsers.partners import PartnersParser

HEADER = (
    '"Datum provedení";"Datum zúčtování";"Směr";"Typ";"Zpráva pro příjemce";'
    '"Číslo účtu protistrany";"Kód banky protistrany";"IBAN protistrany";'
    '"Název protistrany";"Původní název protistrany";"Poznámka pro mě";'
    '"Konstantní symbol";"Specifický symbol";"Variabilní symbol";"Reference";'
    '"Částka";"Měna";"Původní částka";"Původní měna";"Směnný kurz";'
    '"Držitel karty";"Číslo karty";"Identifikace transakce"'
)


def make_csv(*rows: str) -> bytes:
    return ("\n".join([HEADER] + list(rows))).encode("utf-8")


def test_outgoing_transfer_with_note():
    # Real row from the export: outgoing bank transfer with personal note in col 10, IBAN in col 7
    csv_bytes = make_csv(
        '"31.3.2026";"31.3.2026";"Odchozí";"Odchozí platba";"";"7348183014";"6363";'
        '"CZ1963630000007348183014";"Pajgrt Ondřej";"";"Adam jidlo";"";"";"";"";"'
        '-290,00";"CZK";"-290,00";"CZK";"1";"";"";"935b1dad-4e6f-465f-9884-d24e8eba7c07"'
    )
    result = PartnersParser().parse(csv_bytes)

    assert len(result) == 1
    row = result[0]
    assert row.booking_date == date(2026, 3, 31)
    assert row.amount == Decimal("-290.00")
    assert row.counterparty_name == "Pajgrt Ondřej"
    assert row.counterparty_account == "CZ1963630000007348183014"  # IBAN preferred
    assert row.description == "Adam jidlo"  # personal note used (col 10)
    assert row.raw_reference == "935b1dad-4e6f-465f-9884-d24e8eba7c07"


def test_incoming_payment():
    # Real row from the export: incoming payment, positive amount
    csv_bytes = make_csv(
        '"31.3.2026";"31.3.2026";"Příchozí";"Příchozí platba";"";"7757000901";"6363";'
        '"CZ6063630000007757000901";"Pajgrt Bartošová And";"Pajgrt Bartošová And";"";"";"";"";"";'
        '"286,00";"CZK";"286,00";"CZK";"1";"";"";"ea46c949-9c83-49eb-9311-609660200c03"'
    )
    result = PartnersParser().parse(csv_bytes)

    assert len(result) == 1
    row = result[0]
    assert row.booking_date == date(2026, 3, 31)
    assert row.value_date == date(2026, 3, 31)
    assert row.amount == Decimal("286.00")
    assert row.currency == "CZK"
    assert row.counterparty_name == "Pajgrt Bartošová And"
    assert row.counterparty_account == "CZ6063630000007757000901"
    # col 10 empty, col 4 empty, falls back to col 3 (type)
    assert row.description == "Příchozí platba"


def test_card_payment_no_iban():
    # Real row from the export: card payment — cols 5, 6, 7 all empty; falls back to col 3 for description
    csv_bytes = make_csv(
        '"27.3.2026";"30.3.2026";"Odchozí";"Platba kartou";"";"";"";"";"HORNBACH";"";"";"";"";"";"";"'
        '-1601,00";"CZK";"-1601,00";"CZK";"1";"";"**** 3194";"fd887c83-99dc-4e58-89ba-b8db4ccb7cd6"'
    )
    result = PartnersParser().parse(csv_bytes)

    assert len(result) == 1
    row = result[0]
    assert row.booking_date == date(2026, 3, 27)
    assert row.amount == Decimal("-1601.00")
    assert row.counterparty_name == "HORNBACH"
    assert row.counterparty_account is None  # no IBAN, no account+bank
    assert row.description == "Platba kartou"  # col 3 fallback
    assert row.booking_date != row.value_date  # card payment has different booking vs value date


def test_single_digit_day_and_month():
    csv_data = make_csv(
        '"9.3.2026";"11.3.2026";"Odchozí";"Platba kartou";"";"";"";"";"Rohlik.cz";"";"";"";"";"";"";"-2628,39";"CZK";"-2628,39";"CZK";"1";"";"";"183cdfd6-fe9d-4176-aa14-209656b4d4dc"'
    )
    result = PartnersParser().parse(csv_data)
    assert result[0].booking_date == date(2026, 3, 9)
    assert result[0].value_date == date(2026, 3, 11)


def test_counterparty_account_from_account_bank():
    # No IBAN, but account number and bank code present
    csv_data = make_csv(
        '"11.3.2026";"12.3.2026";"Odchozí";"Odchozí platba";"OBJEDNAVKA 588124662";"2171532";"0800";"";"Alza";"";"Retezovy olej";"";"";"";"";"-132,00";"CZK";"-132,00";"CZK";"1";"";"";"b45f3ee6-3b23-49af-b7f2-857095e0f6ae"'
    )
    result = PartnersParser().parse(csv_data)
    assert result[0].counterparty_account == "2171532/0800"
    assert result[0].description == "Retezovy olej"  # personal note wins


def test_description_falls_back_to_message():
    # col 10 (note) is empty, col 4 (message) is non-empty, col 3 (type) is "Odchozí platba"
    csv_data = make_csv(
        '"12.3.2026";"12.3.2026";"Odchozí";"Odchozí platba";"palmknihy.cz AMSU-NDOW-19A8";"2600285563";"2010";"CZ9320100000002600285563";"";"";"";"";"";"";"1366413833";"-572,00";"CZK";"-572,00";"CZK";"1";"";"";"17f9f997-32e4-4b29-9e66-8c2dae2547d6"'
    )
    result = PartnersParser().parse(csv_data)
    assert result[0].description == "palmknihy.cz AMSU-NDOW-19A8"


def test_invalid_header_raises():
    bad_csv = b'"Wrong";"Header"\n"val1";"val2"'
    with pytest.raises(ValueError, match="Unexpected CSV header"):
        PartnersParser().parse(bad_csv)


def test_short_row_raises():
    # Row with only a few columns
    short_row_csv = (HEADER + '\n"31.3.2026";"31.3.2026"').encode("utf-8")
    with pytest.raises(ValueError, match="columns, expected 23"):
        PartnersParser().parse(short_row_csv)


def test_empty_rows_skipped():
    # A blank line between two real data rows should be ignored
    csv_bytes = make_csv(
        '"31.3.2026";"31.3.2026";"Odchozí";"Odchozí platba";"";"7348183014";"6363";'
        '"CZ1963630000007348183014";"Pajgrt Ondřej";"";"Adam jidlo";"";"";"";"";"'
        '-290,00";"CZK";"-290,00";"CZK";"1";"";"";"935b1dad-4e6f-465f-9884-d24e8eba7c07"',
        "",  # blank line
        '"30.3.2026";"30.3.2026";"Příchozí";"Příchozí platba";"";"7778295913";"6363";'
        '"CZ0563630000007778295913";"Pajgrt Ondřej";"Pajgrt Ondřej";"";"";"";"";"";'
        '"5000,00";"CZK";"5000,00";"CZK";"1";"";"";"e3b5c0af-09bf-4088-bd32-af7809afe380"',
    )
    result = PartnersParser().parse(csv_bytes)

    assert len(result) == 2
    assert result[0].booking_date == date(2026, 3, 31)
    assert result[1].booking_date == date(2026, 3, 30)


def test_amount_decimal_parsing():
    # Real row from the export: large negative amount "-7411,76"
    csv_bytes = make_csv(
        '"27.3.2026";"30.3.2026";"Odchozí";"Platba kartou";"";"";"";"";"Makro";"";"";"";"";"";"";"'
        '-7411,76";"CZK";"-7411,76";"CZK";"1";"";"**** 3194";"2c94d73f-62e7-48a7-81f8-41b7a86edda6"'
    )
    result = PartnersParser().parse(csv_bytes)

    assert len(result) == 1
    assert result[0].amount == Decimal("-7411.76")
