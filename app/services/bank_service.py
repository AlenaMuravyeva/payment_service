"""
Сервис для работы с API банка
"""

import asyncio
import logging
import os
import httpx
import json

from app.core.exceptions import BankAPIException

from dotenv import load_dotenv
from typing import Any, Dict


logging.basicConfig(level=logging.INFO)

load_dotenv()
base_url = os.getenv('BANK_API_URL')
username = os.getenv('BANK_USERNAME')
password = os.getenv('BANK_PASSWORD')
qr_timeout_secs = os.getenv('BANK_QR_TIMEOUT') * 60
verify_ssl = os.getenv('VERIFY_SSL')


class BankService:
    """
    Сервис для взаимодействия с API банка
    """

    def __init__(self):
        """Инициализация сервиса банка"""
        self.base_url = base_url
        self.username = username
        self.password = password
        self.qr_timeout_secs = qr_timeout_secs * 60
        self.client = httpx.AsyncClient(timeout=30.0, verify=verify_ssl, http2=False)
        self.max_retries = 3
        self.retry_delay = 1.0

    async def _make_request_with_retry(
            self,
            method: str,
            url: str,
            json_data: Dict[str, Any],
            operation_name: str) -> Dict[str, Any]:
        """
        Выполнить HTTP запрос с retry логикой
        Args:
            method: HTTP метод (post, get)
            url: URL для запроса
            json_data: JSON данные
            operation_name: Имя операции для логирования
        Returns:
            Dict[str, Any]: Ответ от API
        Raises:
            BankAPIException: При ошибке
        """

        last_error = None

        for attempt in range(self.max_retries):
            try:
                if method.lower() == "post":
                    response = await self.client.post(url, json=json_data)
                else:
                    response = await self.client.get(url, params=json_data)

                response.raise_for_status()
                result = response.json()
                return result

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logging.warning(
                        f"{operation_name} timeout, retrying.\
                         Attempt:{attempt + 1} - max_retries:{self.max_retries}-wait_time:{wait_time}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise BankAPIException(f"Request timed out after {self.max_retries} retries")

            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logging.warning(
                        f"{operation_name} connection error, retrying. Error_type:{type(e).__name__}\
                         - attempt:{attempt + 1} - max_retries:{self.max_retries} - wait_time:{wait_time}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise BankAPIException(f"Network error: {type(e).__name__} after {self.max_retries} retries")

            except httpx.HTTPStatusError as e:
                raise BankAPIException(f"HTTP error {e.response.status_code}: {e.response.text[:200]}")

            except json.JSONDecodeError:
                raise BankAPIException(f"Invalid JSON response from bank")

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logging.warning(
                        f"{operation_name} request error, retrying.\
                         Error_type:{type(e).__name__} - attempt:{attempt + 1}- wait_time:{wait_time}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise BankAPIException(f"Network error: {type(e).__name__}")

        raise BankAPIException(f"Failed after {self.max_retries} retries: {str(last_error)}")

    async def acquiring_start(self, order_id: int, amount: int) -> Dict[str, Any]:
        """
        Создание платежа
        Args:
            order_id: Уникальный номер заказа
            amount: Сумма платежа
        Returns:
            Dict[str, Any]: Ответ от API банка
        Raises:
            AcquiringAPIException: При ошибке API банка
        """

        url = f"{self.base_url}/acquiring_start"

        data = {
            "user_name": self.username,
            "password": self.password,
            "order_id": order_id,
            "amount": amount
        }

        try:
            result = await self._make_request_with_retry(
                "post",
                url,
                data,
                "acquiring_start"
            )
            logging.info(f"Payment created successfully: order_id - {order_id},\
             amount - {amount} - result: {result.get('bank_order_id')}")
            return result

        except BankAPIException:
            raise

        except BaseException as e:
            raise BankAPIException(f"Unexpected error: {type(e).__name__}, order_id - {order_id}")

    async def get_payment_status(self, bank_order_id: str) -> Dict[str, Any]:
        """
        Получение статуса платежа
        Args:
            bank_order_id: ID заказа в банке
        Returns:
            Dict[str, Any]: Статус платежа
        Raises:
            BankAPIException: При ошибке API банка
        """

        url = f"{self.base_url}/acquiring_check"

        data = {
            "user_name": self.username,
            "password": self.password,
            "bank_order_id": bank_order_id
        }

        try:
            logging.info(f"Getting payment status, bank_order_id:{bank_order_id}- url:{url}")

            result = await self._make_request_with_retry(
                "post",
                url,
                data,
                "get_payment_status"
            )
            logging.debug(f"Payment status retrieved, bank_order_id: {bank_order_id}")

            return result

        except BankAPIException:
            raise

        except Exception as e:
            raise BankAPIException(f"Unexpected error: {type(e).__name__}")


    async def refund_payment(self, bank_order_id: str, amount: int) -> Dict[str, Any]:
        """
        Возврат платежа
        Args:
            bank_order_id: ID платежа в банке
            amount: Сумма возврата
        Returns:
            Dict[str, Any]: Результат возврата
        Raises:
            BankAPIException: При ошибке API банка
        """

        url = f"{self.base_url}/acquiring_refund"

        data = {
            "user_name": self.username,
            "password": self.password,
            "bank_order_id": bank_order_id,
            "amount": amount
        }

        try:

            result = await self._make_request_with_retry(
                "post",
                url,
                data,
                "refund_payment"
            )

            logging.info(f"Payment refunded, bank_order_id:{bank_order_id} - amount:{amount}")

            return result

        except BankAPIException:
            raise

        except Exception as e:
            raise BankAPIException(f"Unexpected error: {type(e).__name__}")
