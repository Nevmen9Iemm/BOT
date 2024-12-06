import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Product, Cart, Order, OrderItem  # Замініть `models` на вашу назву файлу


@pytest.fixture(scope="module")
def test_db():
    # Створюємо SQLite в пам'яті для тестів
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_crud_operations(test_db):
    session = test_db

    # 1. Створення користувача
    user = User(user_id=123456789, first_name="John", last_name="Doe", phone="1234567890")
    session.add(user)
    session.commit()
    assert session.query(User).count() == 1

    # 2. Створення категорії та продуктів
    category = Category(name="Fruits")
    session.add(category)
    session.commit()

    product1 = Product(name="Apple", price=1.50, image="apple.jpg", category_id=category.id)
    product2 = Product(name="Banana", price=2.00, image="banana.jpg", category_id=category.id)
    session.add_all([product1, product2])
    session.commit()
    assert session.query(Product).count() == 2

    # 3. Додавання продуктів у корзину
    cart_item1 = Cart(user_id=user.user_id, product_id=product1.id, quantity=3)
    cart_item2 = Cart(user_id=user.user_id, product_id=product2.id, quantity=2)
    session.add_all([cart_item1, cart_item2])
    session.commit()
    assert session.query(Cart).count() == 2

    # 4. Видалення продукту з корзини
    session.delete(cart_item1)
    session.commit()
    assert session.query(Cart).count() == 1

    # 5. Очищення корзини
    session.query(Cart).delete()
    session.commit()
    assert session.query(Cart).count() == 0

    # 6. Створення замовлення із продуктами
    order = Order(user_id=user.user_id, total_price=7.00)
    session.add(order)
    session.commit()

    order_item1 = OrderItem(order_id=order.id, product_id=product1.id, quantity=2)
    order_item2 = OrderItem(order_id=order.id, product_id=product2.id, quantity=3)
    session.add_all([order_item1, order_item2])
    session.commit()
    assert session.query(Order).count() == 1
    assert session.query(OrderItem).count() == 2

    # 7. Оновлення ціни товару в замовленні
    product2.price = 2.50  # Оновлюємо ціну продукту
    session.commit()
    updated_product = session.query(Product).filter_by(id=product2.id).one()
    assert updated_product.price == 2.50