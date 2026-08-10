# -*- coding: utf-8 -*-
"""
Прайс студии как данные, а не как текст.

ЗАЧЕМ. Раньше цены лежали прозой внутри промпта, и цифру называла модель.
09.08.2026 в первом же живом разговоре во ВКонтакте это дало «фото на
паспорт — 150 ₽» до выяснения, годится ли снимок клиента: модель нашла в
тексте подходящую строку и пересказала её. Теперь цену считает код по
таблице, а модель только собирает параметры. Не хватает параметра —
функция молчит, и бот задаёт следующий вопрос.

УСТРОЙСТВО. Четыре таблицы, как в обычном прайс-калькуляторе:
  PRICES       — строка цены на комбинацию параметров и диапазон тиража;
  ADDONS       — допуслуги, считаются отдельной строкой;
  COEFFICIENTS — множители: срочность, плотность бумаги, картон;
  SYNONYMS     — как клиент называет услугу своими словами.

Цена ищется точным подбором строки, а не формулой на все случаи: у
типографии слишком много исключений, чтобы держать их в одном выражении.

ГДЕ МЕНЯТЬ ЦЕНЫ. Только здесь. config.TARIFFS остаётся для показа человеку
в диалоге, но арифметика идёт по этому файлу.
"""

# ── Услуги ──────────────────────────────────────────────────────────────
SERVICES = {
    "print_docs":  "Распечатка и ксерокопия",
    "photo_paper": "Печать фотографий",
    "photo_docs":  "Фото на документы",
    "flyers":      "Листовки и флаеры",
    "invites":     "Приглашения и открытки",
    "booklets":    "Буклеты",
    "lamination":  "Ламинация",
    "plotter_drawings": "Чертежи на плоттере",
    "plotter_posters":  "Плакаты и постеры на плоттере",
    "design":      "Макет, правка, дизайн",
}

# Обязательные параметры: без них цену не называем. Именно это правило и
# нарушалось, когда цена звучала третьей репликой.
REQUIRED = {
    "print_docs":  ("format", "color", "qty"),
    "photo_paper": ("format", "qty"),
    "photo_docs":  ("kind",),
    "flyers":      ("format", "qty"),
    # layout обязателен: 65 ₽ — цена печати по ГОТОВОМУ макету, и назвать
    # её тому, у кого макета нет, значит пообещать вчетверо дешевле.
    "invites":     ("kind", "format", "qty", "layout"),
    "design":      ("kind",),
    "booklets":    ("format", "qty"),
    # micron обязателен: плёнка 250 мкм стоит вдвое дороже стандартной,
    # и назвать 70 ₽ тому, кому нужна жёсткая, — ошибка в два конца.
    "lamination":  ("format", "micron", "qty"),
    # У чертежа цена зависит от заливки листа, у постера — от носителя.
    # Это разные логики, поэтому и категории разные: иначе клиент принесёт
    # яркий плакат А0 и будет ждать цену инженерного чёрно-белого листа.
    "plotter_drawings": ("format", "color_mode", "qty"),
    "plotter_posters":  ("format", "paper", "qty"),
}

# ── Цены ────────────────────────────────────────────────────────────────
# (категория, параметры…, тираж от, тираж до, цена, тип цены)
# per_sheet / per_piece — умножаем на количество; per_order — фиксированная.
PRICES = [
    # Ксерокопия и печать с файла
    ("print_docs", {"format": "A4", "color": "bw",    "source": "copy"},  1,  49, 10, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "bw",    "source": "copy"}, 50,  99,  9, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "bw",    "source": "copy"}, 100, 10**6, 8, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "bw",    "source": "file"},  1,  49, 12, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "bw",    "source": "file"}, 50,  99, 10, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "bw",    "source": "file"}, 100, 10**6, 9, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "color"},                    1,  49, 35, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "color"},                   50,  99, 30, "per_sheet"),
    ("print_docs", {"format": "A4", "color": "color"},                  100, 10**6, 27, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "bw"},                       1,  49, 20, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "bw"},                      50,  99, 18, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "bw"},                     100, 10**6, 16, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "color"},                    1,  49, 70, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "color"},                   50,  99, 60, "per_sheet"),
    ("print_docs", {"format": "A3", "color": "color"},                  100, 10**6, 55, "per_sheet"),

    # Фотопечать. 40 ₽ за единичную 10×15 — решение студии 09.08.2026:
    # держим цену городской фотолаборатории, скидку даём за объём.
    ("photo_paper", {"format": "10x15"},   1,   9,  40, "per_piece"),
    ("photo_paper", {"format": "10x15"},  10,  49,  30, "per_piece"),
    ("photo_paper", {"format": "10x15"},  50,  99,  25, "per_piece"),
    ("photo_paper", {"format": "10x15"}, 100, 10**6, 20, "per_piece"),
    ("photo_paper", {"format": "13x18"},   1,   9,  55, "per_piece"),
    ("photo_paper", {"format": "13x18"},  10,  49,  50, "per_piece"),
    ("photo_paper", {"format": "13x18"},  50,  99,  45, "per_piece"),
    ("photo_paper", {"format": "13x18"}, 100, 10**6, 40, "per_piece"),
    ("photo_paper", {"format": "15x21"},   1,   9,  80, "per_piece"),
    ("photo_paper", {"format": "15x21"},  10,  49,  75, "per_piece"),
    ("photo_paper", {"format": "15x21"},  50,  99,  65, "per_piece"),
    ("photo_paper", {"format": "15x21"}, 100, 10**6, 60, "per_piece"),
    ("photo_paper", {"format": "A5"},      1,   9,  90, "per_piece"),
    ("photo_paper", {"format": "A5"},     10,  49,  85, "per_piece"),
    ("photo_paper", {"format": "A5"},     50,  99,  75, "per_piece"),
    ("photo_paper", {"format": "A5"},    100, 10**6, 70, "per_piece"),
    ("photo_paper", {"format": "A4"},      1,   9, 180, "per_piece"),
    ("photo_paper", {"format": "A4"},     10,  49, 165, "per_piece"),
    ("photo_paper", {"format": "A4"},     50,  99, 150, "per_piece"),
    ("photo_paper", {"format": "A4"},    100, 10**6, 140, "per_piece"),
    ("photo_paper", {"format": "A3"},      1,   9, 350, "per_piece"),

    # Фото на документы — цена за услугу, резка входит.
    ("photo_docs", {"kind": "ready_segment"},  1, 10**6, 150, "per_order"),
    ("photo_docs", {"kind": "reprint"},        1, 10**6, 100, "per_order"),
    ("photo_docs", {"kind": "compose"},        1, 10**6, 250, "per_order"),
    ("photo_docs", {"kind": "full_service"},   1, 10**6, 350, "per_order"),

    # Листовки: мелованная 130 г/м², 4+4, при готовом макете.
    ("flyers", {"format": "A6"},    50,  100, 15, "per_piece"),
    ("flyers", {"format": "A6"},   200,  300, 12, "per_piece"),
    ("flyers", {"format": "A6"},   500,  999, 10, "per_piece"),
    ("flyers", {"format": "A6"},  1000, 10**6, 8, "per_piece"),
    ("flyers", {"format": "euro"},  50,  100, 18, "per_piece"),
    ("flyers", {"format": "euro"}, 200,  300, 14, "per_piece"),
    ("flyers", {"format": "euro"}, 500,  999, 12, "per_piece"),
    ("flyers", {"format": "euro"},1000, 10**6, 9, "per_piece"),
    ("flyers", {"format": "A5"},    50,  100, 24, "per_piece"),
    ("flyers", {"format": "A5"},   200,  300, 18, "per_piece"),
    ("flyers", {"format": "A5"},   500,  999, 14, "per_piece"),
    ("flyers", {"format": "A5"},  1000, 10**6, 11, "per_piece"),
    ("flyers", {"format": "A4"},    50,  100, 40, "per_piece"),
    ("flyers", {"format": "A4"},   200,  300, 30, "per_piece"),
    ("flyers", {"format": "A4"},   500,  999, 24, "per_piece"),
    ("flyers", {"format": "A4"},  1000, 10**6, 20, "per_piece"),

    # Открытки и приглашения: картон 300 г/м² — базовая цена.
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A6"},    10,  20, 60, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A6"},    21,  50, 45, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A6"},    51, 100, 35, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A6"},   101, 10**6, 30, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "euro"},  10,  20, 70, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "euro"},  21,  50, 55, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "euro"},  51, 100, 42, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "euro"}, 101, 10**6, 34, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A5"},    10,  20, 90, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A5"},    21,  50, 70, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A5"},    51, 100, 55, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A5"},   101, 10**6, 45, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A6"},      10,  20, 65, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A6"},      21,  50, 50, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A6"},      51, 100, 38, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A6"},     101, 10**6, 32, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "euro"},    10,  20, 75, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "euro"},    21,  50, 58, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "euro"},    51, 100, 45, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "euro"},   101, 10**6, 36, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A5"},      10,  20, 95, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A5"},      21,  50, 75, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A5"},      51, 100, 58, "per_piece"),
    ("invites", {"layout": "ready", "kind": "invite", "format": "A5"},     101, 10**6, 48, "per_piece"),

    # Открытка А4 на плотном материале 300 г/м², 4+4, готовый макет.
    # Отдельно от А6/Евро/А5: площадь вчетверо больше, тираж штучный, и
    # 09.08.2026 такой заказ считали на глаз — в прайсе его просто не было.
    # 200 ₽ за штуку при 6–9 — нижняя нормальная цена; от десятка 180 ₽.
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A4"},  1,   9, 200, "per_piece"),
    ("invites", {"layout": "ready", "kind": "postcard", "format": "A4"}, 10, 10**6, 180, "per_piece"),

    # Индивидуальное приглашение: клиент покупает не лист картона, а
    # готовый персональный продукт — согласование, внесение имён, пробный
    # вариант, подготовка к печати. 200 ₽ — стартовая цена за штуку, точную
    # называем после выбора бумаги, тиража и сложности оформления.
    ("invites", {"layout": "custom", "kind": "invite"},   1, 10**6, 200, "per_piece"),
    ("invites", {"layout": "custom", "kind": "postcard"}, 1, 10**6, 200, "per_piece"),

    # Евробуклет А4: лист 210×297, полноцвет 4+4, две биговки и фальцовка
    # в три панели по 99×210. В цену включены печать, резка и фальцовка —
    # клиенту нельзя показывать «биговка 7 ₽ × 2 линии» отдельными строками,
    # он не поймёт, за что платит дважды.
    #
    # Отдельно от флаеров сознательно: в таблице флаеров А4 стоит 40 ₽, и
    # без разделения клиент не поймёт, откуда взялось 80 ₽ за тот же лист.
    # Он покупает не листовку, а шесть рекламных полос.
    #
    # База — мелованная 115–130 г/м², на ней фальцовка идёт без биговки.
    # Плотнее — коэффициенты бумаги; от 250 г/м² это уже открытка.
    ("booklets", {"format": "a4_trifold"},  10,  20, 80, "per_piece"),
    ("booklets", {"format": "a4_trifold"},  21,  50, 60, "per_piece"),
    ("booklets", {"format": "a4_trifold"},  51, 100, 45, "per_piece"),
    ("booklets", {"format": "a4_trifold"}, 101, 200, 35, "per_piece"),
    ("booklets", {"format": "a4_trifold"}, 201, 500, 25, "per_piece"),
    # Свыше 500 строки нет намеренно: такой тираж выгоднее в офсет, и его
    # считает менеджер, а не бот.

    # Ламинация — за лист. Плёнка одна по цене, матовая и глянцевая
    # стоят одинаково; разница только в толщине. 250 мкм — для жёстких
    # изделий вроде меню и табличек, поэтому и дороже вдвое.
    # Нестандартный размер считаем по ближайшему большему формату.
    ("lamination", {"format": "A6", "micron": "100"},   1, 10, 40, "per_sheet"),
    ("lamination", {"format": "A6", "micron": "100"},  11, 50, 35, "per_sheet"),
    ("lamination", {"format": "A6", "micron": "100"},  51, 10**6, 30, "per_sheet"),
    ("lamination", {"format": "A5", "micron": "100"},   1, 10, 50, "per_sheet"),
    ("lamination", {"format": "A5", "micron": "100"},  11, 50, 45, "per_sheet"),
    ("lamination", {"format": "A5", "micron": "100"},  51, 10**6, 40, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "100"},   1, 10, 70, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "100"},  11, 50, 60, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "100"},  51, 10**6, 50, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "100"},   1, 10, 100, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "100"},  11, 50, 85, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "100"},  51, 10**6, 75, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "150"},   1, 10, 90, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "150"},  11, 50, 80, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "150"},  51, 10**6, 70, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "150"},   1, 10, 130, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "150"},  11, 50, 115, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "150"},  51, 10**6, 100, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "250"},   1, 10, 120, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "250"},  11, 50, 100, "per_sheet"),
    ("lamination", {"format": "A4", "micron": "250"},  51, 10**6, 85, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "250"},   1, 10, 180, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "250"},  11, 50, 150, "per_sheet"),
    ("lamination", {"format": "A3", "micron": "250"},  51, 10**6, 130, "per_sheet"),

    # Плоттер Canon TM-340: чертежи, схемы, проектная документация до А0.
    # Цена за лист и зависит от заливки — чем больше краски, тем дороже.
    ("plotter_drawings", {"format": "A2", "color_mode": "bw"}, 1, 10**6, 60, "per_sheet"),
    ("plotter_drawings", {"format": "A2", "color_mode": "color_20"}, 1, 10**6, 100, "per_sheet"),
    ("plotter_drawings", {"format": "A2", "color_mode": "color_50"}, 1, 10**6, 140, "per_sheet"),
    ("plotter_drawings", {"format": "A2", "color_mode": "color_full"}, 1, 10**6, 220, "per_sheet"),
    ("plotter_drawings", {"format": "A1", "color_mode": "bw"}, 1, 10**6, 110, "per_sheet"),
    ("plotter_drawings", {"format": "A1", "color_mode": "color_20"}, 1, 10**6, 170, "per_sheet"),
    ("plotter_drawings", {"format": "A1", "color_mode": "color_50"}, 1, 10**6, 230, "per_sheet"),
    ("plotter_drawings", {"format": "A1", "color_mode": "color_full"}, 1, 10**6, 320, "per_sheet"),
    ("plotter_drawings", {"format": "A0", "color_mode": "bw"}, 1, 10**6, 190, "per_sheet"),
    ("plotter_drawings", {"format": "A0", "color_mode": "color_20"}, 1, 10**6, 260, "per_sheet"),
    ("plotter_drawings", {"format": "A0", "color_mode": "color_50"}, 1, 10**6, 340, "per_sheet"),
    ("plotter_drawings", {"format": "A0", "color_mode": "color_full"}, 1, 10**6, 450, "per_sheet"),

    # Постеры и плакаты — тот же плоттер, но другие требования к цвету и
    # бумаге, поэтому отдельной категорией и дороже чертежей.
    ("plotter_posters", {"format": "A2", "paper": "plain"}, 1, 10**6, 180, "per_sheet"),
    ("plotter_posters", {"format": "A2", "paper": "photo"}, 1, 10**6, 280, "per_sheet"),
    ("plotter_posters", {"format": "A1", "paper": "plain"}, 1, 10**6, 300, "per_sheet"),
    ("plotter_posters", {"format": "A1", "paper": "photo"}, 1, 10**6, 450, "per_sheet"),
    ("plotter_posters", {"format": "A0", "paper": "plain"}, 1, 10**6, 500, "per_sheet"),
    ("plotter_posters", {"format": "A0", "paper": "photo"}, 1, 10**6, 750, "per_sheet"),

    # Работа с макетом — вилки, поэтому храним нижнюю границу.
    ("design", {"kind": "prepress"},   1, 10**6, 150, "per_order"),
    ("design", {"kind": "adapt"},      1, 10**6, 300, "per_order"),
    ("design", {"kind": "complex"},    1, 10**6, 600, "per_order"),
    ("design", {"kind": "design_new"}, 1, 10**6, 1000, "per_order"),
]

# ── Допуслуги ───────────────────────────────────────────────────────────
# fixed — за весь заказ, per_piece — за штуку.
# Какие допуслуги уместны в какой категории — чтобы бот предлагал ретушь
# фотографу, а глиттер тому, кто заказывает открытки, и не наоборот.
ADDON_SCOPE = {
    "photo_paper": ("color_fix", "basic_retouch"),
    "photo_docs":  ("digital_file", "hard_retouch", "urgent_docphoto"),
    "invites":     ("glitter", "glitter_dense", "photo_paper_300",
                    "corner_round", "fold", "packing"),
    "flyers":      ("corner_round", "packing"),
    "booklets":    ("packing",),
    "lamination":  ("corner_round",),
    "plotter_drawings": ("fold_a2", "fold_a1", "fold_a0"),
    "plotter_posters":  (),
}

ADDONS = {
    "color_fix":      ("Коррекция яркости и цвета", "per_piece", 30),
    "basic_retouch":  ("Базовая ретушь", "per_piece", 100),
    "digital_file":   ("Электронный файл готового фото", "fixed", 100),
    "hard_retouch":   ("Замена одежды, сложная ретушь", "fixed", 150),
    "urgent_docphoto": ("Срочно, вне очереди", "fixed", 100),
    "corner_round":   ("Скругление углов", "per_piece", 5),
    "fold":           ("Биговка и сгиб", "per_piece", 7),
    "packing":        ("Индивидуальная упаковка", "per_piece", 10),
    "glitter":        ("Отделка глиттером", "per_piece", 50),
    "glitter_dense":  ("Глиттер, плотное покрытие", "per_piece", 100),
    "photo_paper_300": ("Плотная фотобумага 300 г/м²", "per_piece", 60),
    "fold_a2":        ("Фальцовка чертежа А2 в А4", "per_piece", 20),
    "fold_a1":        ("Фальцовка чертежа А1 в А4", "per_piece", 25),
    "fold_a0":        ("Фальцовка чертежа А0 в А4", "per_piece", 35),
}

# ── Коэффициенты ────────────────────────────────────────────────────────
# Срочность одна на весь прайс: раньше было +20% у фото и +20–30% у флаеров,
# и клиент не понимал, какая ставка к нему применится.
COEFFICIENTS = {
    # applies_to говорит, К ЧЕМУ множитель. Плотность бумаги и картон —
    # свойство самой печати, поэтому они множат ТОЛЬКО базу: иначе наценка
    # за бумагу поднимала бы и ретушь, и упаковку, и клиент платил бы за
    # плотный картон дважды. Срочность — свойство всего заказа, она множит
    # итог: срочно делается вся работа, включая ручную.
    "urgent":         ("Срочно, день в день", 1.30, "total"),
    "paper_150":      ("Бумага 150 г/м²", 1.10, "base"),
    "paper_170":      ("Бумага 170 г/м²", 1.15, "base"),
    "paper_200":      ("Бумага 200 г/м²", 1.25, "base"),
    "carton_250":     ("Картон 250 г/м²", 0.90, "base"),
    "carton_350":     ("Картон 350 г/м²", 1.10, "base"),
    "paper_designer": ("Фактурная дизайнерская бумага", 1.30, "base"),
    "photo_premium":  ("Премиальная фотобумага", 1.20, "base"),
}

# Какие материальные множители вообще уместны в этой услуге. Срочность сюда
# не входит — она применима везде и добавляется отдельно. Без этой таблицы
# боту показывали бы «Картон 250 г/м²» в разделе фотопечати.
COEF_SCOPE = {
    "flyers":   ("paper_150", "paper_170", "paper_200", "paper_designer"),
    "invites":  ("carton_250", "carton_350", "paper_designer"),
    "booklets": ("paper_150", "paper_170", "paper_200"),
    "photo_paper": ("photo_premium",),
}

# Минимальная стоимость заказа. Ниже неё работа не окупает время.
MIN_ORDER = {
    "print_docs": 50,
    "flyers": 300,
    "booklets": 800,
    "lamination": 50,
    "invites": 700,
    # Штучная открытка А4 с отделкой: ниже этой суммы работа не окупает
    # приёмку, резку и ручную доработку.
    ("invites", "A4"): 1200,
}


def min_order(category: str, params: dict) -> int:
    """Порог для этой позиции. Уточнение по формату важнее общего по категории."""
    return MIN_ORDER.get((category, params.get("format")),
                         MIN_ORDER.get(category, 0))

# ── Как клиент называет услугу ──────────────────────────────────────────
SYNONYMS = {
    "print_docs": ("распечат", "ксерокоп", "копию", "копия", "документ",
                   "скан", "печать с файла", "отксер"),
    "photo_docs": ("на паспорт", "на документ", "загранпаспорт", "на визу",
                   "3х4", "3×4", "на права"),
    # Просто «фото» здесь безопасно, хотя и кажется слишком широким:
    # photo_docs («на паспорт», «на документы») проверяется раньше и забирает
    # своё, а «фото на холсте» раньше уходит в широкоформат. Клиент говорит
    # «сто фото 10 на 15», а не «напечатать фотографии».
    "photo_paper": ("фото", "снимк"),
    # У слов на «-ка» в родительном падеже выпадает гласная: листовка →
    # листовОК, визитка → визитОК, открытка → открытОК. Основа «листовк» их
    # не ловит, а клиент почти всегда пишет «нужно 500 листовок». Поэтому
    # рядом с основой стоит полная форма — и именно она, а не обрезок вроде
    # «листово», чтобы не цеплять «открыто» в вопросе «сегодня открыто?».
    "flyers": ("листовк", "листовок", "флаер"),
    "booklets": ("буклет", "евробуклет", "трифолд", "в три части",
                 "два фальца", "складыва", "фальц"),
    # «приглас» не совпадало с «приглашения» — там «пригла-Ш-ения». Из-за
    # одной буквы самый частый весенний заказ уходил в «не понял задачу».
    # «пригла» покрывает и приглашение, и пригласительный.
    "invites": ("пригла", "открытк", "открыток", "поздравительн"),
    "design": ("макет", "дизайн", "верстк", "правк"),
    # Визитки — самый частый заказ студии, и его тут не было вовсе.
    "visitki": ("визитк", "визиток", "визитн"),
    # Просто «меню» не берём: это слово клиент говорит и про меню бота.
    # Нужен признак, что речь о печати для заведения.
    "menu": ("меню для", "меню кафе", "меню ресторан", "печать меню",
             "барная карта", "винная карта"),
    "wideformat": ("баннер", "широкоформат", "холст", "растяжк", "штендер"),
    # Веб-направление. Здесь оно нужно ещё и как защита: «сайт-визитка»
    # содержит «визитк» и без этой проверки уехало бы в печать визиток.
    "shop": ("интернет-магазин", "маркетплейс"),
    "tgbot": ("телеграм-бот", "телеграм бот", "тг-бот", "чат-бот", "чатбот"),
    "mobile": ("мобильное приложение", "андроид", "ios "),
    "landing": ("сайт", "лендинг", "одностраничник"),
    "lamination": ("ламинац", "ламиниров", "заламин", "плёнк", "пленк"),
    "plotter_posters": ("постер", "плакат", "афиш"),
    "plotter_drawings": ("чертёж", "чертеж", "плоттер", "ватман", "схем",
                         "проектн", "инженерн"),
}


# Коды категорий у бота свои, исторические (photo, copy, cards), а в этой
# таблице — говорящие (photo_paper, print_docs, invites). Совпадал ровно
# один из десяти, и таблица цен молча не подхватывалась: бот читал старые
# тарифы из config, а цены здесь лежали мёртвым грузом. Сшиваем имена.
ALIASES = {
    "photo": "photo_paper",
    "docphoto": "photo_docs",
    "copy": "print_docs",
    "cards": "invites",
    "invitations": "invites",
    "booklet": "booklets",
    "lamin": "lamination",
    "plotter": "plotter_drawings",
    "posters": "plotter_posters",
    "prepress": "design",
}


def canon(category: str) -> str:
    """Привести код категории к тому, что понимает таблица."""
    cat = (category or "").strip()
    return ALIASES.get(cat, cat)


def detect(text: str) -> str:
    """Категория по словам клиента. Пусто — не угадали, надо спросить.

    Порядок проверки важен, и правило одно: сначала конкретный товар, потом
    общие слова. «Фото на паспорт» должно уйти в photo_docs, а не в обычную
    фотопечать. «Распечатать визитки» — в визитки, а не в «распечатать».
    «Сайт-визитка» — в сайты, а не в печать визиток, поэтому веб проверяется
    раньше. Самые общие — «распечатать» и «макет» — стоят последними, иначе
    они перехватывали бы всё подряд.
    """
    low = (text or "").lower()
    for cat in ("photo_docs", "plotter_posters", "plotter_drawings",
                "booklets", "lamination", "menu", "wideformat",
                "shop", "tgbot", "mobile", "landing",
                "visitki", "invites", "flyers", "photo_paper",
                "print_docs", "design"):
        if any(w in low for w in SYNONYMS[cat]):
            return cat
    return ""


def missing(category: str, params: dict) -> tuple:
    """Каких обязательных параметров ещё не хватает."""
    category = canon(category)
    return tuple(f for f in REQUIRED.get(category, ())
                 if not params.get(f))


def find(category: str, params: dict, qty: int = 1):
    """Строка прайса под эти параметры. None — такой комбинации нет."""
    category = canon(category)
    for cat, cond, lo, hi, price, kind in PRICES:
        if cat != category:
            continue
        if any(params.get(k) != v for k, v in cond.items()):
            continue
        if lo <= qty <= hi:
            return {"price": price, "type": kind, "match": cond}
    return None


def addons_sum(codes, qty: int):
    """Допуслуги отдельно от поиска цены: сама ничего не ищет и категорию
    не меняет, только складывает надбавки по правилам.

    Возвращает (фиксированные, поштучные, расшифровка).
    """
    fixed = per_unit = 0
    lines = []
    for code in codes:
        title, kind, value = ADDONS[code]
        if kind == "per_piece":
            amount = value * qty
            per_unit += amount
        else:
            amount = value
            fixed += amount
        lines.append((title, amount))
    return fixed, per_unit, lines


def quote(category: str, params: dict, qty: int = 1,
          addons=(), coefficients=()):
    """Посчитать заказ. Возвращает итог и расшифровку по шагам.

    Порядок расчёта: база → коэффициенты базы → допуслуги → коэффициенты
    итога → минимальный заказ. По шагам, а не одной формулой: так видно,
    из чего сложилась сумма, и клиенту можно показать расшифровку.

    Никогда не гадает: нет параметра или нет строки — так и говорит, а
    решение «спросить или отдать менеджеру» принимает вызывающий код.
    """
    category = canon(category)
    lack = missing(category, {**params, "qty": qty})
    if lack:
        return {"ok": False, "reason": "not_enough", "missing": lack}

    row = find(category, params, qty)
    if not row:
        return {"ok": False, "reason": "no_row", "manager_required": True}

    base = row["price"] * (qty if row["type"] != "per_order" else 1)

    applied = []
    base_adjusted = base
    for code in coefficients:
        title, k, scope = COEFFICIENTS[code]
        if scope == "base":
            base_adjusted *= k
            applied.append((title, k, "к печати"))

    fixed, per_unit, addon_lines = addons_sum(addons, qty)
    subtotal = base_adjusted + fixed + per_unit

    total = subtotal
    for code in coefficients:
        title, k, scope = COEFFICIENTS[code]
        if scope == "total":
            total *= k
            applied.append((title, k, "ко всему заказу"))

    total = round(total)
    floor = min_order(category, params)
    raised = total < floor
    if raised:
        total = floor

    return {
        "ok": True,
        "total": total,
        "base": round(base),
        "base_adjusted": round(base_adjusted),
        "addons": addon_lines,
        "subtotal": round(subtotal),
        "coefficients": applied,
        "min_order_applied": raised,
        "unit": row["type"],
    }


def breakdown(result: dict) -> str:
    """Расшифровка для клиента: из чего сложилась сумма."""
    if not result.get("ok"):
        return ""
    out = [f"Печать: {result['base_adjusted']} ₽"]
    for title, amount in result["addons"]:
        out.append(f"{title}: {amount} ₽")
    for title, k, scope in result["coefficients"]:
        out.append(f"{title} — ×{k} {scope}")
    if result["min_order_applied"]:
        out.append("Поднято до минимального заказа")
    out.append(f"Итого: {result['total']} ₽")
    return "\n".join(out)


def block(category: str) -> str:
    """Строки прайса по категории — текстом для промпта.

    Модель видит те же цифры, что и калькулятор, и не выдумывает своих.
    """
    category = canon(category)
    rows = [r for r in PRICES if r[0] == category]
    if not rows:
        return ""
    out = [f"ПРАЙС — {SERVICES.get(category, category)}:"]
    for _cat, cond, lo, hi, price, kind in rows:
        what = ", ".join(f"{k}={v}" for k, v in cond.items())
        span = "" if kind == "per_order" else (
            f", {lo}–{hi} шт" if hi < 10**6 else f", от {lo} шт")
        unit = {"per_sheet": "за лист", "per_piece": "за штуку",
                "per_order": "за услугу"}[kind]
        out.append(f"  • {what}{span} — {price} ₽ {unit}")
    extras = ADDON_SCOPE.get(category, ())
    if extras:
        out.append("  Допуслуги (в базовую цену НЕ входят, спроси про них):")
        for code in extras:
            title, kind, value = ADDONS[code]
            unit = "за штуку" if kind == "per_piece" else "за заказ"
            out.append(f"    • {title} — {value} ₽ {unit}")

    # Множители. До 10.08.2026 их здесь не было вовсе, и это стоило денег:
    # бот назвал срочному клиенту 450 ₽ вместо 585 ₽, потому что видел
    # только базовую цену и про наценку за срочность просто не знал.
    out.append("  Множители (применяются К НАЗВАННОЙ ЦЕНЕ, не забудь их):")
    title, mult, _scope = COEFFICIENTS["urgent"]
    out.append(f"    • {title} — ×{mult} ко ВСЕМУ заказу, вместе с допуслугами")
    for code in COEF_SCOPE.get(category, ()):
        title, mult, _scope = COEFFICIENTS[code]
        out.append(f"    • {title} — ×{mult} только к базовой печати")
    floor = MIN_ORDER.get(category)
    if floor:
        out.append(f"  Минимальный заказ — {floor} ₽.")
    special = [(k[1], v) for k, v in MIN_ORDER.items()
               if isinstance(k, tuple) and k[0] == category]
    for fmt, amount in special:
        out.append(f"  Минимальный заказ по формату {fmt} — {amount} ₽.")
    return "\n".join(out)


# ── Самопроверка распознавания услуги по словам ─────────────────────────
#
# Запуск: python prices.py. Проверяет detect() — ту самую функцию, через
# которую проходит клиент, написавший или наговоривший задачу своими
# словами вместо нажатия кнопки. 10.08.2026 она не узнавала визитки,
# приглашения и меню: у слов на «-ка» в родительном падеже выпадает
# гласная (визитка → визитОК), а у приглашений была неверная основа.
#
# Вторая половина случаев — обычные фразы клиента, на которые срабатывать
# НЕЛЬЗЯ: ложное срабатывание уводит человека в чужую услугу.

if __name__ == "__main__":
    CASES = [
        ("нужно сто визиток срочно", "visitki"),
        ("распечатать визитки", "visitki"),
        ("500 листовок а6", "flyers"),
        ("20 открыток", "invites"),
        ("приглашения на свадьбу", "invites"),
        ("сделать меню для кафе", "menu"),
        ("нужен баннер", "wideformat"),
        ("фото на холсте", "wideformat"),
        ("нужен сайт-визитка", "landing"),
        ("телеграм бот", "tgbot"),
        ("интернет-магазин", "shop"),
        ("заламинировать 20 листов", "lamination"),
        ("фото на паспорт", "photo_docs"),
        ("100 фото 10 на 15", "photo_paper"),
        ("чертёж А1", "plotter_drawings"),
        ("плакат", "plotter_posters"),
        ("евробуклет", "booklets"),
        ("распечатать документы", "print_docs"),
        ("нужен макет", "design"),
        # ── дальше срабатывать не должно ────────────────────────────────
        ("здравствуйте", ""),
        ("сегодня открыто?", ""),
        ("вы работаете завтра?", ""),
        ("спасибо", ""),
        ("сколько это стоит", ""),
    ]
    bad = 0
    for text, want in CASES:
        got = detect(text)
        good = got == want
        bad += not good
        print(f"  [{'OK ' if good else 'FAIL'}] {got or '—':<18} "
              f"ждали {want or '—':<18} | {text}")
    print("\nВсе случаи разобраны верно." if not bad
          else f"\nРасхождений: {bad}")
