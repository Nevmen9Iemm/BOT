import pytest


@pytest.mark.asyncio
async def test_dispatcher_includes_routers():
    from app import dp, user_private_router, user_group_router, admin_router

    assert user_private_router in dp.routers
    assert user_group_router in dp.routers
    assert admin_router in dp.routers