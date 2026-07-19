# -*- coding: utf-8 -*-
"""
Callback Data Factory + сборка каскадных клавиатур.

Схема callback_data (компактная, укладывается в лимит Telegram 64 байта):

    <ns>:<a>:<b>

  nav:flow:<print|web>   — выбрано направление
  nav:cat:<code>         — выбрана категория (flow берём из сессии)
  dlg:payer:<ur|fiz>     — быстрый ответ: тип плательщика (для «Меню»)
  sys:back               — шаг назад
  sys:home               — в начало
  sys:confirm            — подтвердить заявку
  sys:cancel             — отменить/начать заново

Каскад: меню выдаётся ПОРЦИЯМИ. На верхнем экране — 2 кнопки направления,
на следующем — только категории выбранного направления, а не вся простыня.
"""

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup,
)
import config
import knowledge_base as kb

SEP = ":"


# ── Фабрика callback_data ────────────────────────────────────────────────────

def cb(ns: str, a: str = "", b: str = "") -> str:
    parts = [ns]
    if a:
        parts.append(a)
    if b:
        parts.append(b)
    return SEP.join(parts)


def parse_cb(data: str):
    """'nav:cat:photo' -> ('nav', 'cat', 'photo'); недостающие -> ''."""
    parts = data.split(SEP)
    while len(parts) < 3:
        parts.append("")
    return parts[0], parts[1], parts[2]


# ── Клавиатуры ───────────────────────────────────────────────────────────────

def kb_consent() -> InlineKeyboardMarkup:
    """Шаг 0: согласие на обработку персональных данных (152-ФЗ)."""
    rows = [[InlineKeyboardButton(
        "✅ Даю согласие", callback_data=cb("sys", "consent"))]]
    return InlineKeyboardMarkup(rows)


def kb_contact() -> ReplyKeyboardMarkup:
    """Шаг 1: подтверждение номера. request_contact — Telegram отдаёт номер
    ТОЛЬКО владельца аккаунта, подделать его нельзя (анти-фрод)."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Отправить мой номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def kb_flows() -> InlineKeyboardMarkup:
    """Экран 1: два направления. Никакой простыни."""
    rows = [
        [InlineKeyboardButton(kb.FLOWS["print"]["title"], callback_data=cb("nav", "flow", "print"))],
        [InlineKeyboardButton(kb.FLOWS["web"]["title"],   callback_data=cb("nav", "flow", "web"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_categories(flow: str) -> InlineKeyboardMarkup:
    """Экран 2: категории выбранного направления (по одной кнопке в ряд)."""
    rows = [
        [InlineKeyboardButton(title, callback_data=cb("nav", "cat", code))]
        for code, title in kb.FLOWS[flow]["categories"]
    ]
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data=cb("sys", "home"))])
    return InlineKeyboardMarkup(rows)


def kb_payer() -> InlineKeyboardMarkup:
    """Спец-шаг для категории «Меню»: юрлицо / физлицо."""
    rows = [
        [InlineKeyboardButton("🏢 Организация (Юрлицо/ИП)", callback_data=cb("dlg", "payer", "ur"))],
        [InlineKeyboardButton("👤 Физлицо (частный заказ)",  callback_data=cb("dlg", "payer", "fiz"))],
        [InlineKeyboardButton("⬅️ Назад", callback_data=cb("sys", "back"))],
    ]
    return InlineKeyboardMarkup(rows)


def _controls_row():
    return [
        InlineKeyboardButton("🏠 В начало", callback_data=cb("sys", "home")),
        InlineKeyboardButton("🔄 Заново",   callback_data=cb("sys", "cancel")),
    ]


def kb_dialog_controls() -> InlineKeyboardMarkup:
    """Небольшая панель во время диалога — не мешает вводу текста."""
    return InlineKeyboardMarkup([_controls_row()])


def kb_dialog(options: list[str]) -> InlineKeyboardMarkup:
    """Вопрос с кнопками-вариантами ответа + панель управления снизу.

    Кнопка несёт только индекс (dlg:opt:N) — сам текст варианта хранится
    в сессии (callback_data ограничен 64 байтами).
    """
    rows = []
    for i, opt in enumerate(options):
        rows.append([InlineKeyboardButton(opt, callback_data=cb("dlg", "opt", str(i)))])
    rows.append(_controls_row())
    return InlineKeyboardMarkup(rows)


def kb_gift_offer() -> InlineKeyboardMarkup:
    """Апсейл после подтверждённого заказа — платная услуга, цена сразу в
    кнопке. Ничего не генерируется, пока клиент сам не согласится (следующий
    шаг — kb_gift_price_confirm)."""
    p = config.GIFT_PRICES
    rows = [
        [InlineKeyboardButton(f"✍️ Стих / Поздравление — {p['poem']} ₽",
                               callback_data=cb("gift", "offer", "poem"))],
        [InlineKeyboardButton(f"🎵 Персональная песня — {p['song']} ₽",
                               callback_data=cb("gift", "offer", "song"))],
        [InlineKeyboardButton(f"🎨 Книга-раскраска — от {p['coloring_book']} ₽",
                               callback_data=cb("gift", "offer", "coloring_book"))],
        [InlineKeyboardButton("Нет, спасибо", callback_data=cb("gift", "skip"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_gift_price_confirm(service_type: str) -> InlineKeyboardMarkup:
    """Явное согласие на платную услугу ДО сбора данных и генерации —
    услуга включается в счёт заказа, а не выдаётся бесплатно."""
    rows = [
        [InlineKeyboardButton("✅ Да, согласен(а)", callback_data=cb("gift", "agree", service_type))],
        [InlineKeyboardButton("❌ Нет, передумал(а)", callback_data=cb("gift", "skip"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_gift_style() -> InlineKeyboardMarkup:
    """Стиль для стиха/песни — включая региональные варианты под КМВ."""
    rows = [
        [InlineKeyboardButton("😄 Юмор", callback_data=cb("gift", "style", "humor"))],
        [InlineKeyboardButton("🥹 Трогательно до слёз", callback_data=cb("gift", "style", "touching"))],
        [InlineKeyboardButton("🔥 Драйв", callback_data=cb("gift", "style", "drive"))],
        [InlineKeyboardButton("🍷 Кавказское застолье", callback_data=cb("gift", "style", "toast"))],
        [InlineKeyboardButton("🎶 Душевный шансон", callback_data=cb("gift", "style", "chanson"))],
        [InlineKeyboardButton("🎤 Современный поп/рэп", callback_data=cb("gift", "style", "poprap"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_gift_age_controls() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("⏭ Не указывать возраст", callback_data=cb("gift", "skipage"))],
        _controls_row(),
    ]
    return InlineKeyboardMarkup(rows)


def kb_gift_coloring_mode() -> InlineKeyboardMarkup:
    """Раскраска: оригинальная сказка (ИИ-текст + промты) или раскраска из
    семейного фото (ручная работа дизайнера, цена по фото)."""
    rows = [
        [InlineKeyboardButton("📖 Оригинальная сказка", callback_data=cb("gift", "colormode", "story"))],
        [InlineKeyboardButton("📷 Раскраска из семейного фото", callback_data=cb("gift", "colormode", "photo"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_gift_genre() -> InlineKeyboardMarkup:
    """Жанр сказки-раскраски — 4 варианта, как в сценарии."""
    rows = [
        [InlineKeyboardButton("🚀 Космическое приключение", callback_data=cb("gift", "genre", "space"))],
        [InlineKeyboardButton("🐉 Волшебная сказка с рыцарями", callback_data=cb("gift", "genre", "knights"))],
        [InlineKeyboardButton("🏎️ Весёлые гонки и машины", callback_data=cb("gift", "genre", "racing"))],
        [InlineKeyboardButton("🐾 Спасение планеты с животными", callback_data=cb("gift", "genre", "animals"))],
    ]
    return InlineKeyboardMarkup(rows)


def kb_confirm() -> InlineKeyboardMarkup:
    """Финал: подтвердить ТЗ (→ горячая заявка) или продолжить уточнения."""
    rows = [
        [InlineKeyboardButton("✅ Всё верно, оформить заявку", callback_data=cb("sys", "confirm"))],
        [InlineKeyboardButton("✏️ Хочу дополнить", callback_data=cb("sys", "amend"))],
        [InlineKeyboardButton("🔄 Начать заново",  callback_data=cb("sys", "cancel"))],
    ]
    return InlineKeyboardMarkup(rows)
