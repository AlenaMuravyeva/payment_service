"""
Сервис для работы с платежами
"""
import hashlib
import logging
import random

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PaymentException
from app.models.models import AcquiringPayment, PaymentState, Order, Payment, OrderStatus
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentStatusResponse,
    PaymentRefundResponse
)
from app.services.bank_service import BankService

logging.basicConfig(level=logging.INFO)


class PaymentService:
    """
    Сервис для управления платежами банка
    """

    def __init__(self, db: AsyncSession, bank_service: BankService):
        """
        Инициализация сервиса платежей
        Args:
            db: Сессия базы данных
            bank_service: Сервис для работы с банком,
        """

        self.db = db
        self.bank_service = bank_service

    async def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResponse:
        """
        Создание нового платежа
        Args:
            request: Данные для создания платежа
        Returns:
            PaymentCreateResponse: Результат создания платежа
        Raises:
            PaymentException: При ошибке создания платежа
        """

        try:
            order  = await self._get_order_by_id(request.order_id)

            #Проверяем есть ли заказ с таким id в базе
            if not order.id:
                logging.error(f"Order not found: ID - {request.order_id}")
                return PaymentCreateResponse(
                    success=False,
                    order_id=request.order_id,
                    amount=request.amount,
                    payment_id=None,
                    message=f"Заказ не найден: ID-{request.order_id}",
                    bank_order_id=None
                )

            # Проверяем оплачен ли заказ с таким id
            if order.order_status == OrderStatus.PAID:
                logging.error(f"Order paid : ID - {request.order_id}")
                return PaymentCreateResponse(
                    success=False,
                    order_id=request.order_id,
                    amount=request.amount,
                    payment_id=None,
                    message=f"Заказ оплачен: ID-{request.order_id}",
                    bank_order_id=None
                )

            #Извлекаем все оплаты по номеру заказу
            all_payments = await self._get_payments_by_order_id(order.id)
            sum_all_payments = Decimal()
            if all_payments:
                sum_all_payments = sum([payment.order_sum for payment in all_payments])

            # Проверяем соответствует ли запрошенная сумма сумме заказа и успешных оплат
            available_sum = order.order_amount - sum_all_payments
            if request.amount > available_sum:
                logging.error(
                    f"Summa request payment: {request.amount} > available summa: \
                    {available_sum}, ID - {request.order_id}"
                )
                return PaymentCreateResponse(
                    success=False,
                    order_id=request.order_id,
                    amount=request.amount,
                    payment_id=None,
                    message=f"Summa request payment: {float(request.amount)} > available summa: {available_sum}",
                    bank_order_id=None
                )

            # Генерация уникального идентификатора запроса
            rq_uid = self._generate_rq_uid()

            # Создание записи в базе данных
            payment_data = {
                "order_id": request.order_id,
                "rq_uid": rq_uid,
                "order_sum": float(request.amount),
                "payment_status": PaymentState.CREATED,
                "payment_date": datetime.now(),
                "type": "acquiring"
            }

            payment = await self._create_payment(payment_data)

            # Отправка платежа в API банка
            try:
                bank_response = await self.bank_service.acquiring_start(
                    order_id=payment.order_id,
                    amount=int(request.amount * 100),
                )
            except Exception as e:
                error_msg = str(e)
                error_code = "999"

                await self._update_payment_by_id(
                    payment.id,
                    {
                        "error_code": error_code,
                        "error_description": error_msg,
                        "payment_status": PaymentState.DECLINED,
                        "operation_date_time": datetime.now()
                    }
                )

                logging.error(
                    f"Failed to create payment to bank API, payment_id: \
                    {payment.id} - rq_uid:{rq_uid} - error: {error_msg}"
                )

                return PaymentCreateResponse(
                    success=False,
                    order_id = request.order_id,
                    amount=request.amount,
                    payment_id=payment.id,
                    message=f"Failed to create payment to bank API: error: {error_msg}",
                    bank_order_id=None
                )

            # Обновление записи с данными от банка
            update_data = {
                "error_code": bank_response.get("error_code", "0"),
                "operation_date_time": datetime.now()
            }

            # Проверка на ошибки от банка
            if bank_response.get("error_code") != "0":
                update_data["error_description"] = bank_response.get("error_message")
                update_data["payment_status"] = PaymentState.DECLINED

                await self._update_payment_by_id(payment.id, update_data)

                logging.error(
                    f"Bank API error during payment creation, payment_id:{payment.id}-error_code:\
                    {bank_response.get("error_code")} - error_message:{bank_response.get("error_message")}"
                )

                return PaymentCreateResponse(
                    success=False,
                    order_id=request.order_id,
                    amount=request.amount,
                    payment_id=payment.id,
                    message=f"Bank API error during payment creation: error: {bank_response.get("error_message")}",
                    bank_order_id=None
                )

            # Извлечение ID платежа из ответа при успешном создании
            bank_order_id = bank_response.get("bank_order_id")
            if not bank_order_id:
                update_data["error_description"] = "Bank order id not received from bank"
                update_data["payment_status"] = PaymentState.DECLINED

                await self._update_payment_by_id(payment.id, update_data)

                logging.error(
                    f"Bank order id not received from bank, payment_id:{payment.id} - bank_response:{bank_response}",
                )

                return PaymentCreateResponse(
                    success=False,
                    order_id=request.order_id,
                    amount=request.amount,
                    payment_id=payment.id,
                    message="Bank order id not received from bank",
                    bank_order_id=None
                )

            # Успешное создание платежа
            update_data["bank_order_id"] = bank_response["bank_order_id"]
            update_data["payment_status"] = PaymentState.PAID

            await self._update_payment_by_id(payment.id, update_data)

            logging.info(
                f"Payment created successfully. \
                Payment_id: {payment.id} - amount: {request.amount} - bank_order_id: {bank_response["bank_order_id"]}"
            )

            #Обновляем статус заказа
            await self._update_order_status(order, request.amount, available_sum)

            return PaymentCreateResponse(
                success=True,
                order_id=request.order_id,
                amount=request.amount,
                payment_id=payment.id,
                message="Payment created successfully",
                bank_order_id=bank_response.get("bank_order_id")
            )

        except PaymentException:
            raise
        except Exception as e:
            raise PaymentException(f"Failed to create payment: {type(e).__name__}")

    async def get_payment_status(self, bank_order_id: str) -> PaymentStatusResponse:
        """
        Получение статуса платежа
        Args:
            bank_order_id: Уникальный bank_order_id в таблице acquiring
        Returns:
            PaymentStatusResponse: Статус платежа
        Raises:
            PaymentException: При ошибке получения статуса
        """

        try:
            # Поиск платежа в базе данных
            payment = await self._get_payment_by_bank_order_id(bank_order_id)
            if not payment:
                raise PaymentException("Payment not found")

            # Получение статуса из API банка
            bank_status = None
            try:
                bank_status = await self.bank_service.get_payment_status(bank_order_id)

                if bank_status.get("error_code") == "0":
                    new_status = bank_status.get("bank_order_status")

                    update_data = {
                        "error_code": None,
                        "error_description": None
                    }
                    await self._update_payment_by_id(payment.id, update_data)

                    # Обновление статуса в базе, если он изменился
                    if payment.payment_status != PaymentState(new_status):
                        update_data["payment_status"] = new_status

                        await self._update_payment_by_id(payment.id, update_data)

                        # Обновление статуса заказа
                        await self._update_order_status_by_payment(payment)

            except Exception as e:
                logging.error(
                    f"Failed to get status from bank API, bank_order_id: {bank_order_id} - error:{str(e)}",
                )
            return PaymentStatusResponse(
                success=True,
                order_id=bank_status.get('order_id'),
                amount=bank_status.get('amount'),
                status=bank_status.get("bank_order_status"),
                bank_order_id=bank_order_id,
                created_at=bank_status.get('created_at'),
                operation_time=bank_status.get('operation_time')
            )
        except PaymentException:
            raise
        except Exception as e:
            raise PaymentException(f"Failed to get payment status: {str(e)}")


    async def refund_payment(self, bank_order_id: str) -> PaymentRefundResponse:
        """
        Возврат платежа
        Args:
            bank_order_id: ID заказа в банке
        Returns:
            PaymentRefundResponse: Результат возврата платежа
        Raises:
            PaymentException: При ошибке возврата платежа
        """

        try:
            payment = await self._get_payment_by_bank_order_id(bank_order_id)
            if not payment:
                raise PaymentException("Payment not found")

            if payment.payment_status != PaymentState.PAID:
                raise PaymentException("Payment  status is not PAID")

            # Возврат платежа через API банка
            refund_result = await self.bank_service.refund_payment(
                bank_order_id, payment.order_sum
            )

            if refund_result.get("error_code") != "0":
                error_msg = refund_result.get("error_message", "Unknown error")
                return PaymentRefundResponse(
                    success=False,
                    payment_id=payment.id,
                    bank_order_id=bank_order_id,
                    status=PaymentState.DECLINED,
                    refund_amount=None,
                    message=f"Failed to refund payment: {error_msg}"
                )

            # Обновление статуса платежа в базе
            await self._update_payment_by_id(
                    payment.id,
                {
                    "payment_status": PaymentState.REFUNDED,
                    "operation_date_time": datetime.now()
                }
            )

            logging.info(
                f"Payment refunded successfully,bank_order_id:{bank_order_id} - refund_amount:{payment.order_sum}"
            )

            #Обновление статуса заказа в базе
            await self._update_order_status_by_payment(payment)
            logging.info(
                f"Status order successfully updated, order_id:{payment.order_id}"
            )

            return PaymentRefundResponse(
                success=True,
                payment_id=payment.id,
                bank_order_id=bank_order_id,
                status=PaymentState.REFUNDED,
                refund_amount=payment.order_sum,
                message="Payment refunded successfully"
            )

        except PaymentException:
            raise
        except Exception as e:
            raise PaymentException(f"Failed to refund payment: {str(e)}")

    async def _create_payment(self, payment_data: dict) -> AcquiringPayment:
        """
        Создание платежа в db
        Args:
            payment_data: Данные платежа
        Returns:
            AcquiringPayment: Созданная запись
        """

        payment = AcquiringPayment(**payment_data)
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment


    async def _get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """
        Поиск платежа по id
        Args:
            payment_id: ID записи в таблице payments
        Returns:
            Optional[Payment]: Найденный платеж или None
        """

        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def _get_payment_by_bank_order_id(self, bank_order_id: str) -> Optional[AcquiringPayment]:
        """
        Поиск платежа по bank_order_id
        Args:
            bank_order_id: ID записи платежа банка в таблице acquiring
        Returns:
            Optional[AcquiringPayment]: Найденный платеж или None
        """

        result = await self.db.execute(
            select(AcquiringPayment).where(AcquiringPayment.bank_order_id == bank_order_id)
        )
        return result.scalar_one_or_none()

    async def _update_payment_by_id(self, payment_id: int, update_data: dict) -> None:
        """
        Обновление заказа по ID
        Args:
            payment_id: ID записи в таблице payments
            update_data: Данные для обновления
        """

        payment = await self._get_payment_by_id(payment_id)
        if payment:
            for key, value in update_data.items():
                if hasattr(payment, key):
                    setattr(payment, key, value)
            await self.db.commit()


    def _generate_rq_uid(self) -> str:
        """
        Генерация уникального идентификатора запроса
        Returns:
            str: Уникальный идентификатор
        """

        current_date = datetime.now().isoformat()
        md5_hash = hashlib.md5(current_date.encode()).hexdigest()
        while len(md5_hash) < 32:
            md5_hash += str(random.randint(0, 9))

        return md5_hash[:32]


    async def _get_order_by_id(self, order_id: int) -> Optional[Order]:
        """
        Проверка наличия статуса заказа в базе
        Args:
            order_id: Номер заказа
        Returns:
            Optional[Order]: Найденный заказ или None
        """

        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def _get_payments_by_order_id(self, order_id: int) -> List[Payment] | None:
        """
        Извлекаем все платежи  по номеру заказа наличные и безналичные
        Args:
            order_id: Номер заказа
        Returns:
            List[Payment]: Найденные оплаты или None
        """

        result = await self.db.execute(select(Payment).where(
            Payment.order_id == order_id, Payment.payment_status == PaymentState.PAID)
        )
        records = result.scalars().all()
        return records


    async def _update_order_status(self, order, request_amount, available_summ) -> None:
        """
        Обновление с статуса заказа
        Args:
            order: Заказ
            request_amount: Оплаченная сумма
            available_summ: Доступная сумма для оплаты
        """

        if request_amount == available_summ:
            order.order_status=OrderStatus.PAID
        elif request_amount < available_summ:
            order.order_status = OrderStatus.PART_PAID
        await self.db.commit()

    async def _update_order_status_by_payment(self, payment) -> None:
        """
        Обновление статуса заказа в базе
        Args:
            payment: Экземпляр AcquiringPayment
        """

        order_id = payment.order_id
        order = await self._get_order_by_id(order_id)
        all_payments = await self._get_payments_by_order_id(order_id)
        sum_all_payments = Decimal()
        if all_payments:
            sum_all_payments = sum([payment.order_sum for payment in all_payments])
        if not sum_all_payments:
            order.order_status = OrderStatus.NOT_PAID
        elif order.order_amount == sum_all_payments and order.order_status != OrderStatus.PAID:
            order.order_status = OrderStatus.PAID
        elif order.order_amount > sum_all_payments and order.order_status != OrderStatus.PART_PAID:
            order.order_status = OrderStatus.PART_PAID
        await self.db.commit()