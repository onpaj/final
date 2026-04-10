import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.services.parsers.base import TransactionRow


class GenericCsvParser:
    @classmethod
    def parse(cls, file_bytes: bytes, mapping: dict) -> list[TransactionRow]:
        encoding = mapping.get("encoding", "utf-8")
        separator = mapping.get("separator", ",")
        date_fmt = mapping.get("date_format", "%Y-%m-%d")
        dec_sep = mapping.get("decimal_separator", ".")
        thou_sep = mapping.get("thousands_separator", "")

        text = file_bytes.decode(encoding)
        reader = csv.DictReader(io.StringIO(text), delimiter=separator)
        rows = []
        for raw in reader:
            date_str = raw.get(mapping["date"], "").strip()
            amount_str = raw.get(mapping["amount"], "").strip()
            if not date_str or not amount_str:
                continue
            if thou_sep:
                amount_str = amount_str.replace(thou_sep, "")
            if dec_sep != ".":
                amount_str = amount_str.replace(dec_sep, ".")
            try:
                amount = Decimal(amount_str)
                booking_date = datetime.strptime(date_str, date_fmt).date()
            except (InvalidOperation, ValueError):
                continue

            def col(key, _raw=raw):
                col_name = mapping.get(key)
                return _raw.get(col_name, "").strip() or None if col_name else None

            rows.append(TransactionRow(
                booking_date=booking_date,
                value_date=None,
                amount=amount,
                currency=col("currency") or "CZK",
                counterparty_name=col("counterparty_name"),
                counterparty_account=col("counterparty_account"),
                description=col("description"),
                raw_reference=col("reference"),
            ))
        return rows
