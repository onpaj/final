import io
import re
from datetime import date
from decimal import Decimal

import pdfplumber

from app.services.parsers.base import TransactionRow

_DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}")
_ACCOUNT_RE = re.compile(r"^\d+\s*/\s*\d+$")

_COL_DATES = 0
_COL_TYPE_CODE = 1
_COL_NAME_ACCOUNT = 2
_COL_DETAILS = 3
_COL_AMOUNT = 4


class AirBankPdfParser:

    def parse(self, file_bytes: bytes) -> list[TransactionRow]:
        raw_rows = self._extract_rows(file_bytes)
        return [self._parse_row(row) for row in raw_rows if self._is_data_row(row)]

    def _extract_rows(self, file_bytes: bytes) -> list[list[str | None]]:
        result = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    result.extend(table)
        return result

    def _is_data_row(self, row: list[str | None]) -> bool:
        if not row or len(row) <= _COL_AMOUNT:
            return False
        first = (row[_COL_DATES] or "").strip()
        return bool(_DATE_RE.match(first))

    def _parse_row(self, row: list[str | None]) -> TransactionRow:
        booking_date, value_date = self._split_dates(row[_COL_DATES])
        tx_type, tx_code = self._split_type_code(row[_COL_TYPE_CODE])
        name, account = self._split_name_account(row[_COL_NAME_ACCOUNT])
        details = self._clean(row[_COL_DETAILS])

        return TransactionRow(
            booking_date=booking_date,
            value_date=value_date,
            amount=self._parse_amount(row[_COL_AMOUNT]),
            currency="CZK",  # AirBank CZK statements only; foreign-currency PDFs differ
            counterparty_name=name,
            counterparty_account=account,
            description=details or tx_type,
            raw_reference=tx_code,
        )

    @staticmethod
    def _split_dates(cell: str | None) -> tuple[date, date | None]:
        lines = [line.strip() for line in (cell or "").split("\n") if line.strip()]
        if not lines:
            raise ValueError("Date cell is empty")
        booking = AirBankPdfParser._parse_date(lines[0])
        value = AirBankPdfParser._parse_date(lines[1]) if len(lines) > 1 else None
        return booking, value

    @staticmethod
    def _split_type_code(cell: str | None) -> tuple[str | None, str | None]:
        lines = [line.strip() for line in (cell or "").split("\n") if line.strip()]
        tx_type = lines[0] if lines else None
        tx_code = lines[1] if len(lines) > 1 else None
        return tx_type, tx_code

    @staticmethod
    def _split_name_account(cell: str | None) -> tuple[str | None, str | None]:
        lines = [line.strip() for line in (cell or "").split("\n") if line.strip()]
        account = None
        name_lines = []
        for line in lines:
            if _ACCOUNT_RE.match(line):
                account = line
            else:
                name_lines.append(line)
        name = "\n".join(name_lines) or None
        return name, account

    @staticmethod
    def _parse_date(s: str) -> date:
        d, m, y = s.strip().split(".")
        return date(int(y), int(m), int(d))

    @staticmethod
    def _parse_amount(s: str | None) -> Decimal:
        if not s:
            raise ValueError("Amount field is empty")
        cleaned = s.strip().replace("\xa0", "").replace(" ", "")
        return Decimal(cleaned.replace(",", "."))

    @staticmethod
    def _clean(s: str | None) -> str | None:
        if not s:
            return None
        stripped = s.strip()
        return stripped or None
