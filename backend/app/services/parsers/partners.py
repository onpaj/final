import csv
import io
from datetime import date
from decimal import Decimal

from app.services.parsers.base import TransactionRow

_EXPECTED_HEADER = [
    "Datum provedení", "Datum zúčtování", "Směr", "Typ", "Zpráva pro příjemce",
    "Číslo účtu protistrany", "Kód banky protistrany", "IBAN protistrany",
    "Název protistrany", "Původní název protistrany", "Poznámka pro mě",
    "Konstantní symbol", "Specifický symbol", "Variabilní symbol", "Reference",
    "Částka", "Měna", "Původní částka", "Původní měna", "Směnný kurz",
    "Držitel karty", "Číslo karty", "Identifikace transakce",
]


class PartnersParser:
    _EXPECTED_HEADER = _EXPECTED_HEADER

    def parse(self, file_bytes: bytes) -> list[TransactionRow]:
        text = file_bytes.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
        header = [h.strip() for h in next(reader)]
        if header != self._EXPECTED_HEADER:
            raise ValueError(f"Unexpected CSV header. Got: {header}")
        rows = []
        for raw in reader:
            if not any(f.strip() for f in raw):
                continue
            if len(raw) < 23:
                raise ValueError(f"Row has {len(raw)} columns, expected 23: {raw}")
            rows.append(TransactionRow(
                booking_date=self._parse_date(raw[0]),
                value_date=self._parse_date(raw[1]),
                amount=self._parse_amount(raw[15]),
                currency=raw[16].strip(),
                counterparty_name=raw[8].strip() or None,
                counterparty_account=self._parse_counterparty_account(raw[7], raw[5], raw[6]),
                description=self._parse_description(raw[10], raw[4], raw[3]),
                raw_reference=raw[22].strip() or None,
            ))
        return rows

    @staticmethod
    def _parse_date(s: str) -> date:
        d, m, y = s.strip().split(".")
        return date(int(y), int(m), int(d))

    @staticmethod
    def _parse_amount(s: str) -> Decimal:
        cleaned = s.strip().replace("\xa0", "").replace(" ", "")
        if not cleaned:
            raise ValueError("Amount field is empty")
        return Decimal(cleaned.replace(",", "."))

    @staticmethod
    def _parse_counterparty_account(iban: str, account: str, bank: str) -> str | None:
        if iban.strip():
            return iban.strip()
        acc, bk = account.strip(), bank.strip()
        if acc and bk:
            return f"{acc}/{bk}"
        return acc or None

    @staticmethod
    def _parse_description(note: str, message: str, typ: str) -> str | None:
        return note.strip() or message.strip() or typ.strip() or None
