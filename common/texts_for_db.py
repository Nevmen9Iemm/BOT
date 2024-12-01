from aiogram.utils.formatting import Bold, as_list, as_marked_section


categories = ['Овочі', 'Фрукти', 'Екзотичні фрукти', 'Ягоди','Зелень','Бакалія','Товари для дому', 'Кошики']

description_for_info_pages = {
    "main": "Ласкаво просимо!",
    "about": as_marked_section(
        Bold("Продуктова крамниця OtValentiny:\n"),
        "website: \nhttps://otvalentiny.od.ua/\n",
        "Insgram: \nhttps://www.instagram.com/otvalentiny.od/\n",
        "Facebook: \nhttps://www.facebook.com/otvalentiny.odessa/\n",
        "YouTube: \nhttps://www.youtube.com/channel/UC5klFLutAm3HEOcaV3EeCHg\n"
        "\nГрафік доставки замовлень - 9:00 - 21:00"
    ).as_html(),
    "payment": as_marked_section(
        Bold("Варіанти розрахунку:"),
        "Термінал в магазині",
        "При отриманні - готівка",
        "По реквізитах",
        marker="✅ ",
    ).as_html(),
    "shipping": as_list(
        as_marked_section(
            Bold("Варіанти доставки/замовлення:"),
            "Курʼєр",
            "Нова Пошта",
            "Заберу сам(а)",
            marker="✅ ",
        ),
        as_marked_section(Bold("Не можна:"), "Маршрутка", "Голуби", marker="❌ "),
        sep="\n----------------------\n",
    ).as_html(),
    'catalog': 'Категорії:',
    'cart': 'У кошику нічого немає!',
    'order': 'Ваші замовлення:',
}
