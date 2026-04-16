import re

_IBAN_PREFIX_RE = re.compile(r'^[A-Za-z]{2}\d{2}')


def normalize_iban(s: str) -> str:
    """Strip spaces and uppercase. Works for any IBAN."""
    return s.replace(" ", "").upper()


def iban_to_local_cz(iban: str) -> str | None:
    """
    Derive Czech local account format from a Czech IBAN.

    Czech IBAN (24 chars): CZ + 2 check + 4 bank + 6 prefix + 10 account
    Returns 'account/bank' (no prefix) or 'prefix-account/bank'.
    Returns None for non-Czech or malformed IBANs.
    """
    normalized = normalize_iban(iban)
    if not normalized.startswith("CZ") or len(normalized) != 24:
        return None
    try:
        bank_code = normalized[4:8]
        prefix_int = int(normalized[8:14])
        account_int = int(normalized[14:24])
    except ValueError:
        return None
    account_str = str(account_int)
    if prefix_int == 0:
        return f"{account_str}/{bank_code}"
    return f"{prefix_int}-{account_str}/{bank_code}"


def normalize_local_cz(s: str) -> str | None:
    """
    Normalize a Czech local account string to canonical form.

    Accepts 'account/bank' or 'prefix-account/bank'.
    Strips leading zeros from prefix and account.
    Returns None if unparseable.
    """
    s = s.strip()
    if "/" not in s:
        return None
    slash_idx = s.rfind("/")
    bank_code = s[slash_idx + 1:].strip()
    account_part = s[:slash_idx].strip()
    if "-" in account_part:
        dash_idx = account_part.index("-")
        prefix_str = account_part[:dash_idx].strip()
        account_str = account_part[dash_idx + 1:].strip()
        try:
            prefix_int = int(prefix_str)
            account_int = int(account_str)
        except ValueError:
            return None
        if prefix_int == 0:
            return f"{account_int}/{bank_code}"
        return f"{prefix_int}-{account_int}/{bank_code}"
    else:
        try:
            account_int = int(account_part)
        except ValueError:
            return None
        return f"{account_int}/{bank_code}"


def account_identifiers(iban: str) -> set[str]:
    """
    Return all canonical identifier forms for an account given its IBAN.
    For Czech IBANs: {normalized_iban, local_cz_format}.
    For other IBANs: {normalized_iban}.
    """
    normalized = normalize_iban(iban)
    identifiers: set[str] = {normalized}
    local = iban_to_local_cz(normalized)
    if local:
        identifiers.add(local)
    return identifiers
