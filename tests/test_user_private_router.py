import pytest
from unittest.mock import MagicMock, AsyncMock
from aiogram import types
from aiogram.types import Message, CallbackQuery
from handlers.user_private import start_cmd, add_to_cart, user_menu
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_start_cmd():
    # Підготовка
    message = MagicMock(Message)
    session = AsyncMock(AsyncSession)
    media_mock = MagicMock()
    media_mock.media = "media_url"
    media_mock.caption = "Test caption"

    # Мок для get_menu_content
    with patch('handlers.menu_processing.get_menu_content', return_value=(media_mock, MagicMock())) as mock_get_menu:
        await start_cmd(message, session)
        # Перевірка
        mock_get_menu.assert_called_once_with(session, level=0, menu_name="main")
        message.answer_photo.assert_called_once_with("media_url", caption="Test caption",
                                                     reply_markup=mock_get_menu().reply_markup)


@pytest.mark.asyncio
async def test_add_to_cart():
    # Підготовка
    callback = MagicMock(CallbackQuery)
    callback_data = MagicMock()
    callback_data.product_id = 1
    callback.from_user.id = 123
    callback.from_user.first_name = "John"
    callback.from_user.last_name = "Doe"
    session = AsyncMock(AsyncSession)
    # Моки для orm_add_user та orm_add_to_cart
    with patch('database.orm_query.orm_add_user', new_callable=AsyncMock) as mock_add_user, \
            patch('database.orm_query.orm_add_to_cart', new_callable=AsyncMock) as mock_add_to_cart:
        await add_to_cart(callback, callback_data, session)

        # Перевірка
        mock_add_user.assert_called_once_with(session, user_id=123, first_name="John", last_name="Doe", phone=None)
        mock_add_to_cart.assert_called_once_with(session, user_id=123, product_id=1)
        callback.answer.assert_called_once_with("Продукт доданий в корзину.")


@pytest.mark.asyncio
async def test_user_menu_add_to_cart():
    # Підготовка
    callback = MagicMock(CallbackQuery)
    callback_data = MagicMock(MenuCallBack)
    callback_data.menu_name = "add_to_cart"
    callback_data.product_id = 1
    session = AsyncMock(AsyncSession)
    # Тут ми тестуємо випадок, коли вибирається пункт меню "додати до корзини"
    with patch('handlers.user_private.add_to_cart', new_callable=AsyncMock) as mock_add_to_cart:
        await user_menu(callback, callback_data, session)
        # Перевірка
        mock_add_to_cart.assert_called_once_with(callback, callback_data, session)


@pytest.mark.asyncio
async def test_user_menu_other_action():
    # Підготовка
    callback = MagicMock(CallbackQuery)
    callback_data = MagicMock(MenuCallBack)
    callback_data.menu_name = "some_other_action"
    callback_data.level = 1
    callback_data.category = None
    callback_data.page = None
    callback_data.product_id = None
    callback.from_user.id = 123
    session = AsyncMock(AsyncSession)
    # Мок для get_menu_content
    media_mock = MagicMock()
    media_mock.media = "media_url"
    media_mock.caption = "Test caption"
    with patch('handlers.menu_processing.get_menu_content', return_value=(media_mock, MagicMock())) as mock_get_menu:
        await user_menu(callback, callback_data, session)
        # Перевірка
        mock_get_menu.assert_called_once_with(
            session,
            level=1,
            menu_name="some_other_action",
            category=None,
            page=None,
            product_id=None,
            user_id=123,
        )
        await callback.message.edit_media.assert_called_once_with(media=media_mock,
                                                                  reply_markup=mock_get_menu.return_value[1])
        callback.answer.assert_called_once()