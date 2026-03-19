from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SQLEnum, VARCHAR, CHAR, Numeric
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime

from enum import Enum

class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy"""
    pass

class OrderStatus(str, Enum):
    """Статусы заказа"""
    PAID = "PAID"
    PART_PAID = "PART PAID"
    NOT_PAID = "NOT_PAID"

class PaymentState(str, Enum):
    """Статусы платежей"""
    PAID = "PAID"
    CREATED = "CREATED"
    DECLINED = "DECLINED"
    REFUNDED = "REFUNDED"

class Order(Base):
    """
       Модель для таблицы orders
       Логирование всех операций с платежами
    """

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_amount = Column(Numeric(10, 2))
    order_status = Column(SQLEnum(OrderStatus), nullable=True, default=OrderStatus.NOT_PAID, comment="Статус заказа")
    payments = relationship("Payment", back_populates='order')

class Payment(Base):
    """
        Модель для таблицы payments
        Логирование всех операций с платежами
    """

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Уникальный идентификатор записи")
    order_sum = Column(Numeric(10, 2), nullable=True, comment="Сумма платежа в минимальных единицах валюты")
    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship("Order", back_populates='payments')
    payment_date = Column(DateTime, default=datetime.now)
    payment_status = Column(SQLEnum(PaymentState), nullable=True, comment="Статус платежа")
    type = Column(String(20))

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'payment'
    }

class AcquiringPayment(Payment):
    __tablename__ = 'acquiring'

    id = Column(Integer, ForeignKey('payments.id'), primary_key=True)
    rq_uid = Column(VARCHAR(32), nullable=True, comment="Уникальный идентификатор запроса")
    error_code = Column(CHAR(6),nullable=True,comment="Код выполнения запроса")
    error_description = Column(VARCHAR(256), nullable=True, comment="Описание ошибки выполнения запроса")
    operation_date_time = Column(DateTime, default=datetime.now,  nullable=True)
    bank_order_id = Column(VARCHAR(36), nullable=True, comment="ID заказа банка")

    __mapper_args__ = {
        'polymorphic_identity': 'acquiring'
    }

class CashPayment(Payment):
    __tablename__ = 'cash'

    id = Column(Integer, ForeignKey('payments.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'cash'
    }