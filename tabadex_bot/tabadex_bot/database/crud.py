# tabadex_bot/database/crud.py

import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy import desc, update, func

from .models import AppSetting, User, Order, OrderStatus, SavedAddress, Ticket, TicketMessage, TicketStatus

# --- App Settings Functions ---
async def get_setting(session: AsyncSession, key: str, default: str | None = None) -> str | None:
    setting = await session.get(AppSetting, key)
    return setting.value if setting else default

async def set_setting(session: AsyncSession, key: str, value: str):
    setting = await session.get(AppSetting, key)
    if setting:
        setting.value = value
    else:
        setting = AppSetting(key=key, value=value)
        session.add(setting)
    await session.commit()
    return setting

# --- User Functions ---
async def get_or_create_user(session: AsyncSession, user_id: int, username: str | None, first_name: str) -> User:
    result = await session.execute(select(User).filter_by(user_id=user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        db_user = User(user_id=user_id, username=username, first_name=first_name)
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
    return db_user

async def get_users_paginated(session: AsyncSession, page: int = 1, limit: int = 10) -> list[User]:
    offset = (page - 1) * limit
    query = select(User).order_by(desc(User.created_at)).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

async def get_total_user_count(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.id)))
    return result.scalar_one()

async def get_user_by_user_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).filter(User.user_id == user_id))
    return result.scalar_one_or_none()

async def update_user_block_status(session: AsyncSession, user_id: int, is_blocked: bool) -> bool:
    stmt = update(User).where(User.user_id == user_id).values(is_blocked=is_blocked)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

async def get_all_active_user_ids(session: AsyncSession) -> list[int]:
    query = select(User.user_id).filter(User.is_blocked == False)
    result = await session.execute(query)
    return result.scalars().all()

# --- Statistics Functions ---
async def get_new_users_count_since(session: AsyncSession, time_since: datetime.datetime) -> int:
    query = select(func.count(User.id)).filter(User.created_at >= time_since)
    result = await session.execute(query)
    return result.scalar_one()

async def get_orders_count_by_status(session: AsyncSession, status: OrderStatus) -> int:
    query = select(func.count(Order.id)).filter(Order.status == status)
    result = await session.execute(query)
    return result.scalar_one()

async def get_orders_count_since(session: AsyncSession, time_since: datetime.datetime) -> int:
    query = select(func.count(Order.id)).filter(Order.created_at >= time_since)
    result = await session.execute(query)
    return result.scalar_one()

# --- Order Functions ---
async def get_orders_by_user(session: AsyncSession, user_id: int, page: int = 1, limit: int = 5) -> list[Order]:
    offset = (page - 1) * limit
    query = select(Order).filter(Order.user_id == user_id).order_by(desc(Order.created_at)).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

async def get_order_by_id_for_user(session: AsyncSession, order_id: str, user_id: int) -> Order | None:
    query = select(Order).filter(Order.id == order_id, Order.user_id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

# --- SavedAddress Functions ---
async def get_saved_addresses_by_user(session: AsyncSession, user_id: int) -> list[SavedAddress]:
    query = select(SavedAddress).filter(SavedAddress.user_id == user_id).order_by(SavedAddress.name)
    result = await session.execute(query)
    return result.scalars().all()

async def add_saved_address(session: AsyncSession, user_id: int, name: str, address: str, currency_ticker: str) -> SavedAddress:
    new_address = SavedAddress(user_id=user_id, name=name, address=address, currency_ticker=currency_ticker)
    session.add(new_address)
    await session.commit()
    await session.refresh(new_address)
    return new_address

async def delete_saved_address(session: AsyncSession, address_id: int, user_id: int) -> bool:
    result = await session.execute(select(SavedAddress).filter(SavedAddress.id == address_id, SavedAddress.user_id == user_id))
    address_to_delete = result.scalar_one_or_none()
    if address_to_delete:
        await session.delete(address_to_delete)
        await session.commit()
        return True
    return False

# --- Ticket Functions (User-facing) ---
async def create_ticket(session: AsyncSession, user_id: int, title: str, initial_message: str) -> Ticket:
    # وضعیت اولیه تیکت OPEN است، یعنی منتظر پاسخ ادمین
    new_ticket = Ticket(user_id=user_id, title=title, status=TicketStatus.OPEN)
    session.add(new_ticket)
    await session.flush()
    first_message = TicketMessage(ticket_id=new_ticket.id, sender_id=user_id, text=initial_message, is_admin_response=False)
    session.add(first_message)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket

async def get_tickets_by_user(session: AsyncSession, user_id: int) -> list[Ticket]:
    query = select(Ticket).filter(Ticket.user_id == user_id).order_by(desc(Ticket.created_at))
    result = await session.execute(query)
    return result.scalars().all()

async def get_ticket_with_messages(session: AsyncSession, ticket_id: int, user_id: int) -> Ticket | None:
    query = select(Ticket).options(selectinload(Ticket.messages)).filter(Ticket.id == ticket_id, Ticket.user_id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def add_reply_to_ticket(session: AsyncSession, ticket_id: int, sender_id: int, text: str, is_admin: bool) -> TicketMessage:
    new_message = TicketMessage(ticket_id=ticket_id, sender_id=sender_id, text=text, is_admin_response=is_admin)
    new_status = TicketStatus.ANSWERED if is_admin else TicketStatus.PENDING_USER_REPLY
    stmt = update(Ticket).where(Ticket.id == ticket_id).values(status=new_status)
    session.add(new_message)
    await session.execute(stmt)
    await session.commit()
    await session.refresh(new_message)
    return new_message

async def close_ticket_by_user(session: AsyncSession, ticket_id: int, user_id: int) -> bool:
    stmt = update(Ticket).where(Ticket.id == ticket_id, Ticket.user_id == user_id).values(status=TicketStatus.CLOSED)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0

# --- Ticket Functions (Admin-facing) ---
async def get_all_tickets_by_status(session: AsyncSession, status_list: list[TicketStatus]) -> list[Ticket]:
    query = select(Ticket).filter(Ticket.status.in_(status_list)).order_by(Ticket.created_at)
    result = await session.execute(query)
    return result.scalars().all()

async def get_ticket_by_id_for_admin(session: AsyncSession, ticket_id: int) -> Ticket | None:
    query = (select(Ticket).options(selectinload(Ticket.user), selectinload(Ticket.messages)).filter(Ticket.id == ticket_id))
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def close_ticket_by_admin(session: AsyncSession, ticket_id: int) -> bool:
    stmt = update(Ticket).where(Ticket.id == ticket_id).values(status=TicketStatus.CLOSED)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0