import pytest
from app.services.iban_utils import (
    normalize_iban,
    iban_to_local_cz,
    normalize_local_cz,
    account_identifiers,
)

# --- normalize_iban ---

def test_normalize_iban_strips_spaces():
    assert normalize_iban("CZ65 0800 0000 1920 0014 5399") == "CZ6508000000192000145399"

def test_normalize_iban_uppercases():
    assert normalize_iban("cz6508000000192000145399") == "CZ6508000000192000145399"

def test_normalize_iban_already_normalized():
    assert normalize_iban("CZ6508000000192000145399") == "CZ6508000000192000145399"

# --- iban_to_local_cz ---
# Czech IBAN structure (24 chars): CZ + 2 check + 4 bank + 6 prefix + 10 account
# CZ6508000000192000145399 → bank=0800, prefix=000019→19, account=2000145399
# CZ6503000000000001234567 → bank=0300, prefix=000000→0,  account=0001234567→1234567

def test_iban_to_local_cz_with_prefix():
    assert iban_to_local_cz("CZ6508000000192000145399") == "19-2000145399/0800"

def test_iban_to_local_cz_without_prefix():
    assert iban_to_local_cz("CZ6503000000000001234567") == "1234567/0300"

def test_iban_to_local_cz_accepts_spaces():
    assert iban_to_local_cz("CZ65 0800 0000 1920 0014 5399") == "19-2000145399/0800"

def test_iban_to_local_cz_non_czech_returns_none():
    assert iban_to_local_cz("DE89370400440532013000") is None

def test_iban_to_local_cz_malformed_returns_none():
    assert iban_to_local_cz("NOTANIBAN") is None

def test_iban_to_local_cz_wrong_length_returns_none():
    assert iban_to_local_cz("CZ650800") is None

# --- normalize_local_cz ---

def test_normalize_local_cz_basic():
    assert normalize_local_cz("1234567/0300") == "1234567/0300"

def test_normalize_local_cz_strips_leading_zeros_from_account():
    assert normalize_local_cz("0001234567/0300") == "1234567/0300"

def test_normalize_local_cz_with_prefix():
    assert normalize_local_cz("19-2000145399/0800") == "19-2000145399/0800"

def test_normalize_local_cz_strips_leading_zeros_from_prefix():
    assert normalize_local_cz("019-2000145399/0800") == "19-2000145399/0800"

def test_normalize_local_cz_zero_prefix_omitted():
    assert normalize_local_cz("0-1234567/0300") == "1234567/0300"

def test_normalize_local_cz_no_slash_returns_none():
    assert normalize_local_cz("notanaccount") is None

def test_normalize_local_cz_non_numeric_returns_none():
    assert normalize_local_cz("abc/0300") is None

# --- account_identifiers ---

def test_account_identifiers_czech_iban_without_prefix():
    ids = account_identifiers("CZ6503000000000001234567")
    assert ids == {"CZ6503000000000001234567", "1234567/0300"}

def test_account_identifiers_czech_iban_with_prefix():
    ids = account_identifiers("CZ6508000000192000145399")
    assert ids == {"CZ6508000000192000145399", "19-2000145399/0800"}

def test_account_identifiers_normalizes_input_iban():
    ids = account_identifiers("CZ65 0800 0000 1920 0014 5399")
    assert "CZ6508000000192000145399" in ids

def test_account_identifiers_non_czech_iban_returns_only_iban():
    ids = account_identifiers("DE89370400440532013000")
    assert ids == {"DE89370400440532013000"}
