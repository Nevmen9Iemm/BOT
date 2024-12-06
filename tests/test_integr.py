import pytest


@pytest.mark.asyncio
async def test_dispatcher_includes_routers():
    # from app import dp, user_private_router, user_group_router, admin_router
    #
    # assert user_private_router in dp.routers
    # assert user_group_router in dp.routers
    # assert admin_router in dp.routers

    from app import dp
    from handlers import admin_private, user_group, user_private, menu_processing

    assert admin_private.router in dp.routers
    assert user_group.router in dp.routers
    assert user_private.router in dp.routers
    assert menu_processing.router in dp.routers