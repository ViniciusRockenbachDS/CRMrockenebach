"""Exceções de domínio e handlers globais que padronizam as respostas de erro.

Todo erro sai no formato `ErrorResponse`: {"code", "message", "details", "extra"}.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    message: str = "Não foi possível concluir a operação."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[ErrorDetail] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        self.extra = extra
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Registro não encontrado."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Conflito com um registro existente."


class BusinessRuleError(AppError):
    status_code = 422
    code = "business_rule_violation"
    message = "A operação viola uma regra de negócio."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Não autenticado."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "Você não tem permissão para esta ação."


class AIProviderError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ai_unavailable"
    message = "O serviço de IA está indisponível no momento."


# Nomes de constraints (definidos pela naming convention) → mensagens amigáveis.
_CONSTRAINT_MESSAGES: dict[str, str] = {
    "uq_users_email": "Já existe um usuário com este e-mail.",
    "uq_clients_document_active": "Já existe um cliente ativo com este CPF/CNPJ.",
    "uq_payments_invoice_number": "Número de fatura duplicado.",
    "ck_deals_closed_at_consistency": "Data de fechamento inconsistente com a etapa da negociação.",
    "ck_payments_paid_requires_payment_date": "Pagamentos pagos precisam de data de pagamento.",
    "ck_payments_installment_range": "Número da parcela inválido.",
}

_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Texto muito curto.",
    "string_too_long": "Texto muito longo.",
    "greater_than": "Valor deve ser maior que zero.",
    "greater_than_equal": "Valor abaixo do mínimo permitido.",
    "less_than_equal": "Valor acima do máximo permitido.",
    "enum": "Opção inválida.",
    "literal_error": "Opção inválida.",
    "uuid_parsing": "Identificador inválido.",
    "date_from_datetime_parsing": "Data inválida.",
    "date_parsing": "Data inválida.",
    "decimal_max_places": "Use no máximo 2 casas decimais.",
    "extra_forbidden": "Campo não permitido.",
    "timezone_aware": "Informe data/hora com fuso horário.",
}


def _error_response(exc_status: int, body: ErrorResponse, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=exc_status,
        content=body.model_dump(exclude_none=True, mode="json"),
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return _error_response(
            exc.status_code,
            ErrorResponse(code=exc.code, message=exc.message, details=exc.details, extra=exc.extra),
            headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[ErrorDetail] = []
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", ()) if part not in ("body", "query", "path")]
            err_type = err.get("type", "")
            message = str(err.get("msg", "Valor inválido."))
            if err_type == "value_error":
                message = message.removeprefix("Value error, ")
            else:
                message = _VALIDATION_MESSAGES.get(err_type, message)
            details.append(ErrorDetail(field=".".join(loc) or None, message=message, type=err_type))
        first = details[0].message if details else "Dados inválidos."
        return _error_response(
            422,
            ErrorResponse(code="validation_error", message=first, details=details),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        raw = str(exc.orig)
        for constraint, message in _CONSTRAINT_MESSAGES.items():
            if constraint in raw:
                return _error_response(
                    status.HTTP_409_CONFLICT, ErrorResponse(code="integrity_error", message=message)
                )
        if "foreign key" in raw.lower():
            message = "Registro relacionado não existe ou ainda está em uso."
        else:
            message = "A operação conflita com dados existentes."
        logger.warning("IntegrityError: %s", raw)
        return _error_response(status.HTTP_409_CONFLICT, ErrorResponse(code="integrity_error", message=message))

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Erro não tratado", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorResponse(code="internal_error", message="Erro interno inesperado. Tente novamente."),
        )
