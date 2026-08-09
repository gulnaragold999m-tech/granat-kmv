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
    "design":      "Макет, правка, дизайн",
}

# Обязательные параметры: без них цену не называем. Именно это правило и
# нарушалось, когда цена звучала третьей репликой.
REQUIRED = {
    "print_docs":  ("format", "color", "qty"),
    "photo_paper": ("format", "qty"),
    "photo_docs":  ("kind",),
    "flyers":      ("format", "qty"),
    "invites":     ("kind", "format", "qty"),
    "design":      ("kind",),
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
    ("invites", {"kind": "postcard", "format": "A6"},    10,  20, 60, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A6"},    21,  50, 45, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A6"},    51, 100, 35, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A6"},   101, 10**6, 30, "per_piece"),
    ("invites", {"kind": "postcard", "format": "euro"},  10,  20, 70, "per_piece"),
    ("invites", {"kind": "postcard", "format": "euro"},  21,  50, 55, "per_piece"),
    ("invites", {"kind": "postcard", "format": "euro"},  51, 100, 42, "per_piece"),
    ("invites", {"kind": "postcard", "format": "euro"}, 101, 10**6, 34, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A5"},    10,  20, 90, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A5"},    21,  50, 70, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A5"},    51, 100, 55, "per_piece"),
    ("invites", {"kind": "postcard", "format": "A5"},   101, 10**6, 45, "per_piece"),
    ("invites", {"kind": "invite", "format": "A6"},      10,  20, 65, "per_piece"),
    ("invites", {"kind": "invite", "format": "A6"},      21,  50, 50, "per_piece"),
    ("invites", {"kind": "invite", "format": "A6"},      51, 100, 38, "per_piece"),
    ("invites", {"kind": "invite", "format": "A6"},     101, 10**6, 32, "per_piece"),
    ("invites", {"kind": "invite", "format": "euro"},    10,  20, 75, "per_piece"),
    ("invites", {"kind": "invite", "format": "euro"},    21,  50, 58, "per_piece"),
    ("invites", {"kind": "invite", "format": "euro"},    51, 100, 45, "per_piece"),
    ("invites", {"kind": "invite", "format": "euro"},   101, 10**6, 36, "per_piece"),
    ("invites", {"kind": "invite", "format": "A5"},      10,  20, 95, "per_piece"),
    ("invites", {"kind": "invite", "format": "A5"},      21,  50, 75, "per_piece"),
    ("invites", {"kind": "invite", "format": "A5"},      51, 100, 58, "per_piece"),
    ("invites", {"kind": "invite", "format": "A5"},     101, 10**6, 48, "per_piece"),

    # Работа с макетом — вилки, поэтому храним нижнюю границу.
    ("design", {"kind": "prepress"},   1, 10**6, 150, "per_order"),
    ("design", {"kind": "adapt"},      1, 10**6, 300, "per_order"),
    ("design", {"kind": "complex"},    1, 10**6, 600, "per_order"),
    ("design", {"kind": "design_new"}, 1, 10**6, 1000, "per_order"),
]

# ── Допуслуги ───────────────────────────────────────────────────────────
# fixed — за весь заказ, per_piece — за штуку.
ADDONS = {
    "color_fix":      ("Коррекция яркости и цвета", "per_piece", 30),
    "basic_retouch":  ("Базовая ретушь", "per_piece", 100),
    "digital_file":   ("Электронный файл готового фото", "fixed", 100),
    "hard_retouch":   ("Замена одежды, сложная ретушь", "fixed", 150),
    "urgent_docphoto": ("Срочно, вне очереди", "fixed", 100),
    "corner_round":   ("Скругление углов", "per_piece", 5),
    "fold":           ("Биговка и сгиб", "per_piece", 7),
    "packing":        ("Индивидуальная упаковка", "per_piece", 10),
}

# ── Коэффициенты ────────────────────────────────────────────────────────
# Срочность одна на весь прайс: раньше было +20% у фото и +20–30% у флаеров,
# и клиент не понимал, какая ставка к нему применится.
COEFFICIENTS = {
    "urgent":         ("Срочно, день в день", 1.30),
    "paper_150":      ("Бумага 150 г/м²", 1.10),
    "paper_170":      ("Бумага 170 г/м²", 1.15),
    "paper_200":      ("Бумага 200 г/м²", 1.25),
    "carton_250":     ("Картон 250 г/м²", 0.90),
    "carton_350":     ("Картон 350 г/м²", 1.10),
    "paper_designer": ("Фактурная дизайнерская бумага", 1.30),
    "photo_premium":  ("Премиальная фотобумага", 1.20),
}

# Минимальная стоимость заказа. Ниже неё работа не окупает время.
MIN_ORDER = {
    "print_docs": 50,
    "flyers": 300,
    "invites": 700,
}

# ── Как клиент называет услугу ──────────────────────────────────────────
SYNONYMS = {
    "print_docs": ("распечат", "ксерокоп", "копию", "копия", "документ",
                   "скан", "печать с файла", "отксер"),
    "photo_docs": ("на паспорт", "на документ", "загранпаспорт", "на визу",
                   "3х4", "3×4", "на права"),
    "photo_paper": ("фотограф", "фотобумаг", "напечатать фото", "печать фото",
                    "снимк"),
    "flyers": ("листовк", "флаер", "буклет"),
    "invites": ("приглас", "открытк", "поздравительн"),
    "design": ("макет", "дизайн", "верстк", "правк"),
}


def detect(text: str) -> str:
    """Категория по словам клиента. Пусто — не угадали, надо спросить.

    Порядок проверки важен: «фото на паспорт» должно уйти в photo_docs,
    а не в обычную фотопечать, поэтому photo_docs стоит раньше photo_paper.
    """
    low = (text or "").lower()
    for cat in ("photo_docs", "print_docs", "photo_paper", "flyers",
                "invites", "design"):
        if any(w in low for w in SYNONYMS[cat]):
            return cat
    return ""


def missing(category: str, params: dict) -> tuple:
    """Каких обязательных параметров ещё не хватает."""
    return tuple(f for f in REQUIRED.get(category, ())
                 if not params.get(f))


def find(category: str, params: dict, qty: int = 1):
    """Строка прайса под эти параметры. None — такой комбинации нет."""
    for cat, cond, lo, hi, price, kind in PRICES:
        if cat != category:
            continue
        if any(params.get(k) != v for k, v in cond.items()):
            continue
        if lo <= qty <= hi:
            return {"price": price, "type": kind, "match": cond}
    return None


def quote(category: str, params: dict, qty: int = 1,
          addons=(), coefficients=()):
    """Посчитать заказ. Возвращает словарь с итогом и расшифровкой.

    Никогда не гадает: нет параметра или нет строки — так и говорит, а
    решение «спросить или отдать менеджеру» принимает вызывающий код.
    """
    lack = missing(category, {**params, "qty": qty})
    if lack:
        return {"ok": False, "reason": "not_enough", "missing": lack}

    row = find(category, params, qty)
    if not row:
        return {"ok": False, "reason": "no_row"}

    base = row["price"] * (qty if row["type"] != "per_order" else 1)
    lines = [(SERVICES.get(category, category), base)]

    for code in addons:
        title, kind, value = ADDONS[code]
        amount = value * qty if kind == "per_piece" else value
        lines.append((title, amount))

    total = sum(a for _t, a in lines)

    applied = []
    for code in coefficients:
        title, k = COEFFICIENTS[code]
        total *= k
        applied.append((title, k))

    total = round(total)
    floor = MIN_ORDER.get(category, 0)
    raised = total < floor
    if raised:
        total = floor

    return {
        "ok": True,
        "total": total,
        "lines": lines,
        "coefficients": applied,
        "min_order_applied": raised,
        "unit": row["type"],
    }


def block(category: str) -> str:
    """Строки прайса по категории — текстом для промпта.

    Модель видит те же цифры, что и калькулятор, и не выдумывает своих.
    """
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
    if category in MIN_ORDER:
        out.append(f"  Минимальный заказ — {MIN_ORDER[category]} ₽.")
    return "\n".join(out)
