"""
Обработка исключений и ошибок
"""
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Any, Dict

logging.basicConfig(level=logging.INFO)

class AcquiringAPIException(Exception):
    """Базовое исключение для API банка"""

    def __init__(
            self,
            message: str,
            status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            details: Dict[str, Any] | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class PaymentException(AcquiringAPIException):
    """Исключения связанные с платежами"""
    pass

class BankAPIException(AcquiringAPIException):
    """Исключения при работе с API банка"""
    pass

class ValidationException(AcquiringAPIException):
    """Исключения валидации данных"""

    def __init__(self, message: str, field_errors: Dict[str, str] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field_errors": field_errors or {}}
        )


async def acquiring_exception_handler(request: Request, exc: AcquiringAPIException) -> JSONResponse:
    """
    Обработчик исключений Acquiring API
    Args:
        request: HTTP запрос
        exc: Исключение Acquiring API
    Returns:
        JSONResponse: JSON ответ с ошибкой
    """

    logging.error(f"Acquiring API Exception: {request.url.path} - {request.method} - {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic
    Args:
        request: HTTP запрос
        exc: Ошибка валидации

    Returns:
        JSONResponse: JSON ответ с ошибкой валидации
    """

    logging.error(f"Validation Error: {request.url.path} - {request.method} - {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Обработчик HTTP исключений
    Args:
        request: HTTP запрос
        exc: HTTP исключение
    Returns:
        JSONResponse: JSON ответ с ошибкой
    """
    logging.error(f"HTTP Exception: {request.url.path} - {request.method} - {exc.status_code}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed"
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Общий обработчик исключений

    Args:
        request: HTTP запрос
        exc: Исключение

    Returns:
        JSONResponse: JSON ответ с ошибкой
    """
    logging.error(f"Unhandled Exception: {request.url.path} - {request.method} - {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error"
        }
    )


def add_exception_handlers(app: FastAPI) -> None:
    """
    Добавление обработчиков исключений в приложение

    Args:
        app: Экземпляр FastAPI приложения
    """
    app.add_exception_handler(AcquiringAPIException, acquiring_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)