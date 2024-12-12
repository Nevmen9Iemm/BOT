from idlelib.debugobj import myrepr

from aiogram.types import InputMediaPhoto
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from database.get_menu_content import my_orders
from database.orm_query import (
    orm_add_to_cart,
    orm_delete_from_cart,
    orm_get_banner,
    orm_get_categories,
    orm_get_products,
    orm_get_user_cart,
    orm_reduce_product_in_cart,
)

from kbds.inline import (
    get_products_btns,
    get_user_cart,
    get_user_catalog_btns,
    get_user_main_btns,
    get_user_orders,
)

from utils.paginator import Paginator


async def main_menu(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    kbds = get_user_main_btns(level=level)

    return image, kbds


async def catalog(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)
    if not banner:
        image = InputMediaPhoto(media=banner.image("default.jpg"), caption="Інформація недоступна")
        return image

    categories = await orm_get_categories(session)
    kbds = get_user_catalog_btns(level=level, categories=categories)

    return image, kbds


def pages(paginator: Paginator):
    btns = dict()
    if paginator.has_previous():
        btns["◀ Попер."] = "previous"

    if paginator.has_next():
        btns["Слід. ▶"] = "next"

    return btns


async def products(session, level, category, page):
    products = await orm_get_products(session, category_id=category)

    paginator = Paginator(products, page=page)
    product = paginator.get_page()[0]

    image = InputMediaPhoto(
        media=product.image,
        caption=f"<strong>{product.name}\
                </strong>\nВартість: {round(product.price, 2)} грн.\n\
                <strong>Продукт {paginator.page} з {paginator.pages}</strong>",
    )

    pagination_btns = pages(paginator)

    kbds = get_products_btns(
        level=level,
        category=category,
        page=page,
        pagination_btns=pagination_btns,
        product_id=product.id,
    )

    return image, kbds


async def cart(session, level, menu_name, page, user_id, product_id):
    if menu_name == "delete":
        await orm_delete_from_cart(session, user_id, product_id)
        if page > 1:
            page -= 1
    elif menu_name == "decrement":
        is_cart = await orm_reduce_product_in_cart(session, user_id, product_id)
        if page > 1 and not is_cart:
            page -= 1
    elif menu_name == "increment":
        await orm_add_to_cart(session, user_id, product_id)

    carts = await orm_get_user_cart(session, user_id)

    if not carts:
        banner = await orm_get_banner(session, "cart")
        image = InputMediaPhoto(
            media=banner.image, caption=f"<strong>{banner.description}</strong>"
        )

        kbds = get_user_cart(
            level=level,
            page=None,
            pagination_btns=None,
            product_id=None,
        )

    else:
        paginator = Paginator(carts, page=page)

        cart = paginator.get_page()[0]

        cart_price = round(cart.quantity * cart.product.price, 2)
        total_price = round(
            sum(cart.quantity * cart.product.price for cart in carts), 2
        )
        image = InputMediaPhoto(
            media=cart.product.image,
            caption=f"<strong>{cart.product.name}</strong>\n{cart.product.price}$ x {cart.quantity} = {cart_price} грн.\
                    \nПродукт {paginator.page} з {paginator.pages} в кошику.\nЗагальна вартість товарів у кошику {total_price} грн.",
        )

        pagination_btns = pages(paginator)

        kbds = get_user_cart(
            level=level,
            page=page,
            pagination_btns=pagination_btns,
            product_id=cart.product.id,
        )

    return image, kbds


async def orders(session, level, user_id, product_id=None):
    # Отримати всі замовлення користувача з БД
    query = select(Order).where(Order.user_id == user_id).order_by(Order.created.desc())
    result = await session.execute(query)
    my_orders = result.scalars().all()

    if not my_orders:
        message_text = "Ви ще не зробили жодного замовлення."
        return message_text, None

    message_text = "Ваші замовлення:\n\n"
    for order in my_orders:
        message_text += f"Замовлення №{order.id} - {order.total_price}$ ({order.created_at.strftime('%Y-%m-%d')})\n"

    # Створити кнопки для взаємодії
    kbds = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="На головну", callback_data="main_menu"))
    return message_text, kbds


async def get_menu_content(
    session: AsyncSession,
    level: int,
    menu_name: str,
    category: int | None = None,
    page: int | None = None,
    product_id: int | None = None,
    user_id: int | None = None,
):
    if level == 0:
        return await main_menu(session, level, menu_name)
    elif level == 1:
        return await catalog(session, level, menu_name)
    elif level == 2:
        return await products(session, level, category, page)
    elif level == 3:
        return await cart(session, level, menu_name, page, user_id, product_id)
    elif level == 4:
        return await my_orders(session, level, user_id, product_id)

    # Якщо нічого не знайдено, повертаємо None
    message_text = "Немає такої сторінки"
    return message_text, None
