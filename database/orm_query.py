import math
import logging
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.util import ordered_column_set

from database.models import Banner, Cart, Category, Product, User, Order, OrderItem

logger = logging.getLogger(__name__)


############### Робота із банерами (інформаційними сторінками) ###############

async def orm_add_banner_description(session: AsyncSession, data: dict):
    #Додаємо новий або змінюємо існуючий по іменам
    #пунктів меню: main, about, cart, shipping, payment, catalog, order, orders, default
    query = select(Banner)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Banner(name=name, description=description) for name, description in data.items()]) 
    await session.commit()


async def orm_change_banner_image(session: AsyncSession, name: str, image: str):
    query = update(Banner).where(Banner.name == name).values(image=image)
    await session.execute(query)
    await session.commit()


async def orm_get_banner(session: AsyncSession, page: str):
    query = select(Banner).where(Banner.name == page)
    result = await session.execute(query)
    return result.scalar()


async def orm_get_info_pages(session: AsyncSession):
    query = select(Banner)
    result = await session.execute(query)
    return result.scalars().all()


############################ Категорії ######################################


async def orm_get_categories(session: AsyncSession):
    query = select(Category)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_create_categories(session: AsyncSession, categories: list):
    query = select(Category)
    result = await session.execute(query)
    if result.first():
        return
    session.add_all([Category(name=name) for name in categories]) 
    await session.commit()


############ Адмінка: додати/змінити/видалити товар ########################


async def orm_add_product(session: AsyncSession, data: dict):
    obj = Product(
        name=data["name"],
        # description=data["description"],
        price=float(data["price"]),
        image=data["image"],
        category_id=int(data["category"]),
    )
    session.add(obj)
    await session.commit()


async def orm_get_products(session: AsyncSession, category_id):
    query = select(Product).where(Product.category_id == int(category_id))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_product(session: AsyncSession, product_id: int):
    query = select(Product).where(Product.id == product_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_product(session: AsyncSession, product_id: int, data):
    query = (
        update(Product)
        .where(Product.id == product_id)
        .values(
            name=data["name"],
            # description=data["description"],
            price=float(data["price"]),
            image=data["image"],
            category_id=int(data["category"]),
        )
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_product(session: AsyncSession, product_id: int):
    query = delete(Product).where(Product.id == product_id)
    await session.execute(query)
    await session.commit()


##################### Додаємо юзера в БД #####################################


async def orm_add_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
):
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    if result.first() is None:
        session.add(
            User(user_id=user_id, first_name=first_name, last_name=last_name, phone=phone)
        )
        await session.commit()


######################## Робота із кошиком #######################################


async def orm_add_to_cart(session: AsyncSession, user_id: int, product_id: int):
    query = select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()
    if cart:
        cart.quantity += 1
        await session.commit()
        return cart
    else:
        session.add(Cart(user_id=user_id, product_id=product_id, quantity=1))
        await session.commit()


async def orm_get_user_cart(session: AsyncSession, user_id):
    query = select(Cart).filter(Cart.user_id == user_id).options(joinedload(Cart.product))
    result = await session.execute(query)
    return result.scalars().all()


async def orm_delete_from_cart(session: AsyncSession, user_id: int, product_id: int):
    query = delete(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    await session.execute(query)
    await session.commit()


async def orm_reduce_product_in_cart(session: AsyncSession, user_id: int, product_id: int):
    query = select(Cart).where(Cart.user_id == user_id, Cart.product_id == product_id)
    cart = await session.execute(query)
    cart = cart.scalar()

    if not cart:
        return
    if cart.quantity > 1:
        cart.quantity -= 1
        await session.commit()
        return True
    else:
        await orm_delete_from_cart(session, user_id, product_id)
        await session.commit()
        return False


######################## Робота із замовленням (переробити)#######################################


async def orm_save_order(session: AsyncSession, user_id: int):
    logger.info("Отримуємо кошик для користувача", user_id)
    # Отримати товари з кошика
    carts = await orm_get_user_cart(session, user_id)
    if not carts:
        logger.warning("Кошик порожній для користувача", user_id)
        return None  # Якщо кошик порожній, нічого не робимо

    # Розрахувати загальну вартість
    total_price = sum(cart.quantity * cart.product.price for cart in carts)
    logger.info("Загальна вартість замовлення:", total_price)

    # Створити нове замовлення
    orders = Orders(user_id=user_id, total_price=total_price)
    session.add(orders)
    await session.flush()  # Отримати ID замовлення
    logger.info("Замовлення створено з ID", order.id)

    # Додати товари до замовлення
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

    # Очистити кошик
    # await session.execute(delete(Cart).where(Cart.user_id == user_id))
    await session.commit()
    logger.info("Кошик очищено для користувача", user_id)

    return orders


async def orm_get_order(session: AsyncSession, order_id: int):
    """ Отримати замовлення за його ID """
    query = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            # Завантаження пов'язаних елементів замовлення
            joinedload(Order.items).joinedload(OrderItem.product)
        )
    )
    result = await session.execute(query)
    order = result.scalar_one_or_none()  # Отримати одне замовлення або None
    return order


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