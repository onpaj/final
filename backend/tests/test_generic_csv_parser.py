from decimal import Decimal
from app.services.parsers.generic_csv import GenericCsvParser

MAPPING = {
    "date": "Datum",
    "amount": "Castka",
    "currency": "Mena",
    "counterparty_name": "Protistrany",
    "counterparty_account": None,
    "description": "Popis",
    "reference": None,
    "date_format": "%d.%m.%Y",
    "decimal_separator": ",",
    "thousands_separator": " ",
    "encoding": "utf-8",
    "separator": ";",
}

CSV_CONTENT = b"""Datum;Castka;Mena;Protistrany;Popis
15.01.2026;-1 250,00;CZK;ALBERT;Nakup
20.01.2026;50 000,00;CZK;Zamestnavatel;Vyplata
"""


def test_parse_returns_rows():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert len(rows) == 2


def test_amounts_parsed():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert rows[0].amount == Decimal("-1250.00")
    assert rows[1].amount == Decimal("50000.00")


def test_counterparty_name():
    rows = GenericCsvParser.parse(CSV_CONTENT, MAPPING)
    assert rows[0].counterparty_name == "ALBERT"
