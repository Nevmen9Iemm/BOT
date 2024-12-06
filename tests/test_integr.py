import pytest


@pytest.mark.asyncio
async def test_dispatcher_includes_routers():
    from handlers.user_private import user_private_router
    from handlers.user_group import user_group_router
    from handlers.admin_private import admin_router

    from aiogram import Dispatcher

    assert user_private_router in dp.message
    assert user_group_router in dp.message
    assert admin_router in dp.message