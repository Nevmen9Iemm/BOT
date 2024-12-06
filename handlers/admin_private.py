from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_change_banner_image,
    orm_get_categories,
    orm_add_product,
    orm_delete_product,
    orm_get_info_pages,
    orm_get_product,
    orm_get_products,
    orm_update_product,
)

from filters.chat_types import ChatTypeFilter, IsAdmin

from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard(
    "Додати продукт",
    "Асортимент",
    "Додати/Змінити банер",
    placeholder="Виберіть дію",
    sizes=(2,),
)


@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Що Ви хочете зробити?", reply_markup=ADMIN_KB)


@admin_router.message(F.text == 'Асортимент')
async def admin_features(message: types.Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name : f'category_{category.id}' for category in categories}
    await message.answer("Виберіть категорію", reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('category_'))
async def starring_at_product(callback: types.CallbackQuery, session: AsyncSession):
    category_id = callback.data.split('_')[-1]
    for product in await orm_get_products(session, int(category_id)):
        await callback.message.answer_photo(
            product.image,
            caption=f"<strong>{product.name}\
                    </strong>\n{product.description}\nВартість: {round(product.price, 2)}",
            reply_markup=get_callback_btns(
                btns={
                    "Видалити": f"delete_{product.id}",
                    "Змінити": f"change_{product.id}",
                },
                sizes=(2,)
            ),
        )
    await callback.answer()
    await callback.message.answer("ОК, ось перелік товарів ⏫")


@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(callback: types.CallbackQuery, session: AsyncSession):
    product_id = callback.data.split("_")[-1]
    await orm_delete_product(session, int(product_id))

    await callback.answer("Товар видалено")
    await callback.message.answer("Товар видалено!")


################# Мікро FSM для завантаження/зміни банерів ############################

class AddBanner(StatesGroup):
    image = State()

# Відправляємо перелік інформаційних сторінок бота і встановлюємо стан відправки фото
@admin_router.message(StateFilter(None), F.text == 'Додати/Змінити банер')
async def add_image2(message: types.Message, state: FSMContext, session: AsyncSession):
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(f"Надішліть фото банера.\nВ описі вкажіть для якої сторінки:\
                         \n{', '.join(pages_names)}")
    await state.set_state(AddBanner.image)

# Додаємо/змінюємо зображення в таблиці (там вже є записані сторінки по іменам:
# main, catalog, cart(для пустого кошика), about, payment, shipping, order, default)
@admin_router.message(AddBanner.image, F.photo)
async def add_banner(message: types.Message, state: FSMContext, session: AsyncSession):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_names:
        await message.answer(f"Введіть правильну назву сторінки, наприклад:\
                         \n{', '.join(pages_names)}")
        return
    await orm_change_banner_image(session, for_page, image_id,)
    await message.answer("Банер доданий/змінений.")
    await state.clear()

# ловим некоректне введення
@admin_router.message(AddBanner.image)
async def add_banner2(message: types.Message, state: FSMContext):
    await message.answer('Надішліть фото банера або відмініть команду "відміна"')
    if message.text == 'відміна':
        await message.answer('ОК, завершаємо')
        await state.clear()


#########################################################################################



######################### FSM для додовання/змінення товарів адміном ###################

class AddProduct(StatesGroup):
    # Кроки стану
    name = State()
    # description = State()
    category = State()
    price = State()
    image = State()

    product_for_change = None

    texts = {
        "AddProduct:name": "Введіть назву заново:",
        # "AddProduct:description": "Введіть опис заново:",
        "AddProduct:category": "Виберіть категорію заново ⬆️",
        "AddProduct:price": "Введіть вартість заново:",
        "AddProduct:image": "Цей пункт останній, тому...",
    }


# Стаємо в стан очікування вводу name
@admin_router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_product_callback(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    product_id = callback.data.split("_")[-1]

    product_for_change = await orm_get_product(session, int(product_id))

    AddProduct.product_for_change = product_for_change

    await callback.answer()
    await callback.message.answer(
        "Введіть назву продукту", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


# Стаємо в стан очікування вводу name
@admin_router.message(StateFilter(None), F.text == "Додати продукт")
async def add_product(message: types.Message, state: FSMContext):
    await message.answer(
        "Введіть назву продукту", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


# Хендлер відміни та скидання стану повинен бути завжди тут
# після того, як тільки стали в стан номер 1 (елементарна черга фільтрів)

@admin_router.message(StateFilter("*"), Command("відміна"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "відміна")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddProduct.product_for_change:
        AddProduct.product_for_change = None
    await state.clear()
    await message.answer("Дії відмінено", reply_markup=ADMIN_KB)


# Повернутись на крок назад (на попередній стан)
@admin_router.message(StateFilter("*"), Command("назад"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddProduct.name:
        await message.answer(
            'Попереднього кроку немає, або введіть назву продукту або напишіть "відміна"'
        )
        return

    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                f"Добре, ви повернулися до минулого кроку \n {AddProduct.texts[previous.state]}"
            )
            return
        previous = step


# Ловимо дані для стану name і потім міняємо стан на description
@admin_router.message(AddProduct.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        # Тут можна зробити додаткову перевірку і вийти із стану хендлера
        # не змінюючи стан з відправкою відповідного повідомлення
        # наприклад, якщо введення більшого ніж 150 символів:
        if 4 >= len(message.text) >= 150:
            await message.answer(
                "Назва продукту не повинна перевищувати 150 символів\nабо бути менше 5 символів. \n Введіть заново"
            )
            return

        await state.update_data(name=message.text)
    await message.answer("Введіть опис продукту")
    await state.set_state(AddProduct.description)

# Хендлер для відлову некоректных вводів для стану name
@admin_router.message(AddProduct.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer("Ви ввели неприпустимі дані, введіть текст назви продукту")


# Ловимо дані для стану description =і потім міняємо стан на price
@admin_router.message(AddProduct.description, F.text)
async def add_description(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(description=AddProduct.product_for_change.description)
    else:
        if 4 >= len(message.text):
            await message.answer(
                "Занадто короткий опис. \n Введіть повторно"
            )
            return
        await state.update_data(description=message.text)

    categories = await orm_get_categories(session)
    btns = {category.name : str(category.id) for category in categories}
    await message.answer("Виберіть категорію", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddProduct.category)

# Хендлер для відлову некоректних вводів для стану description
@admin_router.message(AddProduct.description)
async def add_description2(message: types.Message, state: FSMContext):
    await message.answer("Ви ввели недопустимі дані, введіть текст опису продукту")


# Ловимо callback вибору категорії
@admin_router.callback_query(AddProduct.category)
async def category_choice(callback: types.CallbackQuery, state: FSMContext , session: AsyncSession):
    if int(callback.data) in [category.id for category in await orm_get_categories(session)]:
        await callback.answer()
        await state.update_data(category=callback.data)
        await callback.message.answer('Тепер введіть ціну.')
        await state.set_state(AddProduct.price)
    else:
        await callback.message.answer('Виберіть категорію з кнопок.')
        await callback.answer()

#Ловимо любі некоректні дії, окрім натискання на кнопку вибору категорії
@admin_router.message(AddProduct.category)
async def category_choice2(message: types.Message, state: FSMContext):
    await message.answer("'Виберіть категорію з кнопок.'")


# Ловимо дані для стану price і потім міняємо стан на image
@admin_router.message(AddProduct.price, F.text)
async def add_price(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(price=AddProduct.product_for_change.price)
    else:
        try:
            float(message.text)
        except ValueError:
            await message.answer("Введіть коректне значення ціни")
            return

        await state.update_data(price=message.text)
    await message.answer("Завантажте зображення продукту")
    await state.set_state(AddProduct.image)

# Хендлер для відлову некоректного вводу для стану price
@admin_router.message(AddProduct.price)
async def add_price2(message: types.Message, state: FSMContext):
    await message.answer("Ви ввели неприпустимі дані, введіть вартість продукту")


# Ловимо дані для сстану image і потім виходимо із станів
@admin_router.message(AddProduct.image, or_f(F.photo, F.text == "."))
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text == "." and AddProduct.product_for_change:
        await state.update_data(image=AddProduct.product_for_change.image)

    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Надішліть фото їжі")
        return
    data = await state.get_data()
    try:
        if AddProduct.product_for_change:
            await orm_update_product(session, AddProduct.product_for_change.id, data)
        else:
            await orm_add_product(session, data)
        await message.answer("Продукт доданий/змінений", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Помилка: \n{str(e)}\nЗвернись до програміста, він знову грошей хоче",
            reply_markup=ADMIN_KB,
        )
        await state.clear()

    AddProduct.product_for_change = None

# Ловимо всю іншу некоректну поведінку для цього стану
@admin_router.message(AddProduct.image)
async def add_image2(message: types.Message, state: FSMContext):
    await message.answer("Надішліть фото їжі")
