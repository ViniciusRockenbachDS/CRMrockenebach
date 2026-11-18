import pytest

from app.utils.dates import add_months
from app.utils.validators import is_valid_cnpj, is_valid_cpf, normalize_document, normalize_phone_br


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("(47) 99999-8888", "+5547999998888"),
        ("47 3333-4444", "+554733334444"),
        ("+55 47 99999-8888", "+5547999998888"),
    ],
)
def test_normalize_phone(raw: str, expected: str) -> None:
    assert normalize_phone_br(raw) == expected


@pytest.mark.parametrize("raw", ["123", "(47) 89999-8888", "(00) 99999-8888"])
def test_invalid_phone(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_phone_br(raw)


def test_cpf_cnpj() -> None:
    assert is_valid_cpf("52998224725")
    assert not is_valid_cpf("11111111111")
    assert is_valid_cnpj("11222333000181")
    assert not is_valid_cnpj("11222333000180")
    assert normalize_document("11.222.333/0001-81") == "11222333000181"


def test_add_months_end_of_month() -> None:
    from datetime import date

    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)
