from aiogram import F, types, Router
from aiogram.filters import CommandStart

from sqlalchemy import delete
from database.models import Order, OrderItem
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_to_cart,
    orm_add_user,
    orm_get_user_carts,
    orm_get_order,

)

from filters.chat_types import ChatTypeFilter
from handlers.menu_processing import get_menu_content
from kbds.inline import MenuCallBack, get_callback_btns



user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    media, reply_markup = await get_menu_content(session, level=0, menu_name="main")

    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


async def add_to_cart(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    user = callback.from_user
    await orm_add_user(
        session,
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=None,
    )
    await orm_add_to_cart(session, user_id=user.id, product_id=callback_data.product_id)
    await callback.answer("Продукт додано в корзину.")


async def orm_get_user_orders(session: AsyncSession, user_id: int):
    """ Отримати всі замовлення користувача """
    query = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product)
        )
        .order_by(Order.created_at.desc())  # Сортування за датою
    )
    result = await session.execute(query)
    orders = result.scalars().all()  # Отримати всі замовлення
    return orders


@user_private_router.message(F.text == "Мої замовлення")
async def get_user_orders(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    orders = await orm_get_user_orders(session, user_id)

    if not orders:
        await message.answer("У вас немає замовлень.")
        return

    message_text = "Ваші замовлення:\n\n"
    for order in orders:
        message_text += f"Замовлення №{order.id} - {order.total_price}$ ({order.created_at.strftime('%Y-%m-%d')})\n"
    await message.answer(message_text)


@user_private_router.callback_query(MenuCallBack.filter())
async def user_menu(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):

    if callback_data.menu_name == "add_to_cart":
        await add_to_cart(callback, callback_data, session)
        return

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id,
    )

    if not media:
        await callback.message.answer("На жаль, банер не знайдено.")
        return

    await callback.message.edit_media(media=media, reply_markup=reply_markup)
    await callback.answer()


async def process_order(callback: types.CallbackQuery, session: AsyncSession):
    user_id = callback.from_user.id

    # Зберегти замовлення
    order = await orm_save_order(session, user_id)
    if not order:
        await callback.answer("Ваш кошик порожній!", show_alert=True)
        return

    # Підготувати підсумок замовлення
    order_items = "\n".join(
        [f"{item.product.name} ({item.quantity} шт.) - {item.quantity * item.price}$"
         for item in order.items]
    )
    message = (
        f"Ваше замовлення №{order.id} сформовано:\n\n{order_items}\n\n"
        f"<strong>Загальна сума:</strong> {order.total_price}$\n"
        f"Дата створення: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "З вами зв'яжеться наш менеджер для уточнення деталей."
    )
    await callback.message.answer(message)
    await callback.answer("Замовлення сформовано!", show_alert=True)


async def orm_save_order(session: AsyncSession, user_id: int):
    logger.info("Отримуємо товари з кошика для користувача %s", user_id)
    # Отримуємо товари з кошика
    carts = await orm_get_user_carts(session, user_id)
    if not carts:
        logger.warning("Кошик порожній для користувача %s", user_id)
        return None

    # Розрахунок загальної вартості замовлення
    total_price = sum(cart.quantity * cart.product.price for cart in carts)
    logger.info("Загальна сума замовлення: %s", total_price)

    # Створення запису в таблиці Order
    order = Order(user_id=user_id, total_price=total_price)
    session.add(order)
    await session.flush()  # Отримання ID замовлення перед комітом
    logger.info("Замовлення створено з ID %s", order.id)

    # Додавання товарів до замовлення
    order_items = [
        OrderItem(
            order_id=order.id,
            product_id=cart.product.id,
            quantity=cart.quantity,
            price=cart.product.price,
        )
        for cart in carts
    ]
    session.add_all(order_items)

    # Видалення кошика
    await session.execute(delete(Cart).where(Cart.user_id == user_id))
    await session.commit()
    logger.info("Кошик очищено для користувача %s", user_id)

    return order


async def handle_order(callback: types.CallbackQuery, session: AsyncSession):
    await process_order(callback, session)
