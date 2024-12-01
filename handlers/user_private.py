from aiogram import F, types, Router
from aiogram.filters import CommandStart

from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_add_to_cart,
    orm_add_user,
    orm_get_user_carts,

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
    await callback.answer("Продукт доданий в корзину.")


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
    carts = await orm_get_user_carts(session, user_id)

    if not carts:
        await callback.answer("Ваш кошик порожній!", show_alert=True)
        return

    total_price = sum(cart.quantity * cart.product.price for cart in carts)
    order_summary = "\n".join(
        [f"{cart.product.name} ({cart.quantity} шт.) - {cart.quantity * cart.product.price}$"
         for cart in carts]
    )
    message = (
        f"Ваше замовлення сформовано:\n\n{order_summary}\n\n"
        f"<strong>Загальна сума:</strong> {total_price}$\n\n"
        "З вами зв'яжеться наш менеджер для уточнення деталей."
    )
    await callback.message.answer(message)

    # Тут можна додати логіку для збереження замовлення до бази
    await callback.answer("Замовлення сформовано!", show_alert=True)