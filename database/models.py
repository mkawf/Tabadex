# tabadex_bot/database/models.py

import enum
from sqlalchemy import (
    Column, Integer, String, BigInteger, DateTime, ForeignKey,
    Enum as SQLAlchemyEnum, Text, Boolean, func
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# --- کلاس‌های شمارشی برای وضعیت‌ها ---
class OrderStatus(enum.Enum):
    """وضعیت‌های مختلف یک سفارش تبادل ارز."""
    PENDING = "pending"
    WAITING = "waiting"
    CONFIRMING = "confirming"
    EXCHANGING = "exchanging"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"

class TicketStatus(enum.Enum):
    """وضعیت‌های مختلف یک تیکت پشتیبانی."""
    OPEN = "open"
    ANSWERED = "answered"
    PENDING_USER_REPLY = "pending_user_reply"
    CLOSED = "closed"

# --- مدل‌های اصلی دیتابیس ---

class AppSetting(Base):
    """
    مدلی برای ذخیره تنظیمات کلی ربات به صورت کلید-مقدار.
    مانند درصد مارکاپ.
    """
    __tablename__ = 'app_settings'
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    def __repr__(self):
        return f"<AppSetting(key='{self.key}', value='{self.value}')>"

class User(Base):
    """
    مدل مربوط به کاربران ربات.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String)
    first_name = Column(String)
    language_code = Column(String, default='fa')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_blocked = Column(Boolean, default=False)

    # --- Relationships ---
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    addresses = relationship("SavedAddress", back_populates="user", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}')>"

class Order(Base):
    """
    مدل مربوط به سفارش‌های تبادل ارز.
    """
    __tablename__ = 'orders'

    id = Column(String, primary_key=True) # شناسه تراکنش از SwapZone
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True)
    from_currency = Column(String, nullable=False)
    to_currency = Column(String, nullable=False)
    from_amount = Column(String, nullable=False)
    to_amount_estimated = Column(String, nullable=False) # مقداری که پس از کسر مارکاپ محاسبه شده
    to_amount_actual = Column(String) # مقدار واقعی که پس از انجام تراکنش مشخص می‌شود
    deposit_address = Column(String, nullable=False)
    recipient_address = Column(String, nullable=False)
    status = Column(SQLAlchemyEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="orders")

    def __repr__(self):
        return f"<Order(id='{self.id}', status='{self.status}')>"

class SavedAddress(Base):
    """
    مدل مربوط به آدرس‌های کیف پول ذخیره شده توسط کاربر.
    """
    __tablename__ = 'saved_addresses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True)
    name = Column(String, nullable=False) # نام دلخواه کاربر برای آدرس
    address = Column(String, nullable=False)
    currency_ticker = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="addresses")
    
    def __repr__(self):
        return f"<SavedAddress(name='{self.name}', currency='{self.currency_ticker}')>"

class Ticket(Base):
    """
    مدل اصلی برای یک تیکت پشتیبانی.
    """
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True)
    title = Column(String, nullable=False) # موضوع تیکت
    status = Column(SQLAlchemyEnum(TicketStatus), default=TicketStatus.OPEN, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Ticket(id={self.id}, title='{self.title}', status='{self.status}')>"

class TicketMessage(Base):
    """
    مدل برای هر پیام در یک تیکت پشتیبانی.
    """
    __tablename__ = 'ticket_messages'

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False, index=True)
    sender_id = Column(BigInteger, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_admin_response = Column(Boolean, default=False)
    
    ticket = relationship("Ticket", back_populates="messages")
    
    def __repr__(self):
        return f"<TicketMessage(ticket_id={self.ticket_id}, sender_id={self.sender_id})>"