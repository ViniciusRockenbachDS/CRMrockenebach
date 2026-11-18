"""Validações e normalizações de dados brasileiros (telefone, CPF, CNPJ)."""

import re

_NON_DIGITS = re.compile(r"\D")


def only_digits(value: str) -> str:
    return _NON_DIGITS.sub("", value)


def normalize_phone_br(value: str) -> str:
    """Normaliza telefone para E.164 (+55DDDNÚMERO).

    Aceita: "(47) 99999-8888", "47999998888", "+55 47 99999-8888", "4733334444".
    """
    digits = only_digits(value)
    if len(digits) in (10, 11):          # DDD + número, sem código do país
        digits = f"55{digits}"
    if len(digits) not in (12, 13) or not digits.startswith("55"):
        raise ValueError("Telefone inválido. Use DDD + número, ex.: (47) 99999-8888.")
    ddd = digits[2:4]
    if ddd[0] == "0":
        raise ValueError("DDD inválido.")
    if len(digits) == 13 and digits[4] != "9":
        raise ValueError("Celular com 9 dígitos deve começar com 9.")
    return f"+{digits}"


def is_valid_cpf(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for size in (9, 10):
        total = sum(int(cpf[i]) * (size + 1 - i) for i in range(size))
        check = (total * 10) % 11 % 10
        if check != int(cpf[size]):
            return False
    return True


def is_valid_cnpj(cnpj: str) -> bool:
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_2 = [6, *weights_1]
    for weights, pos in ((weights_1, 12), (weights_2, 13)):
        total = sum(int(cnpj[i]) * w for i, w in enumerate(weights))
        remainder = total % 11
        check = 0 if remainder < 2 else 11 - remainder
        if check != int(cnpj[pos]):
            return False
    return True


def normalize_document(value: str) -> str:
    """Valida CPF ou CNPJ e devolve somente os dígitos."""
    digits = only_digits(value)
    if len(digits) == 11 and is_valid_cpf(digits):
        return digits
    if len(digits) == 14 and is_valid_cnpj(digits):
        return digits
    raise ValueError("CPF ou CNPJ inválido.")
