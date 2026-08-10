# -*- coding: utf-8 -*-
"""
Модель сессии пользователя = лёгкий FSM.

Вместо жёсткого ConversationHandler с фиксированными состояниями держим одну
структуру на пользователя. Навигация по меню детерминирована (stage), а внутри
диалога параметры собирает LLM (Dialog Manager), поэтому «жёстких линейных
сценариев» нет — есть цель (собрать order_spec) и свободный диалог к ней.

Хранилище — in-memory dict (как в исходном боте). Для продакшена под нагрузкой
замени на Redis/SQLite: интерфейс get_session/reset_session остаётся тем же.
"""

import re

# Стадии верхнего уровня (детерминированная навигация)
STAGE_CONSENT = "consent"  # согласие на обработку персональных данных
STAGE_PHONE   = "phone"    # подтверждение номера кнопкой Telegram (анти-фрод)
STAGE_FLOW    = "flow"     # выбор направления (2 кнопки)
STAGE_CAT     = "cat"      # выбор категории каскадом
STAGE_PAYER   = "payer"    # спец-шаг «Меню»: юр/физ
STAGE_DIALOG  = "dialog"   # идёт умный опрос под управлением LLM
STAGE_CONFIRM = "confirm"  # ТЗ собрано, ждём подтверждения
STAGE_GIFT    = "gift"     # апсейл после заказа: собираем данные для подарка (стих/песня/раскраска)


# ── Согласие словами, а не кнопкой ──────────────────────────────────────
#
# 10.08.2026 живой человек написал боту «нужно 100 визиток срочно», получил
# приветствие, написал своё имя — и получил приветствие снова. И так по
# кругу: согласие засчитывалось только нажатием кнопки или точным текстом
# «Согласен, продолжим». Кнопку видно не всегда, а многие по привычке
# отвечают словом. Петля без выхода на самом первом шаге — клиент уходит.
#
# Считаем согласием короткую фразу, ВСЕ слова которой утвердительные. Так
# «да», «да, согласна» и «хорошо, давайте» проходят, а «Наталья Семёнова»
# или «да нужно 100 визиток» — нет: там есть слова не из списка.
CONSENT_WORDS = {
    "да", "ага", "угу", "ок", "окей", "ok", "okay", "хорошо", "хорошо",
    "согласен", "согласна", "согласны", "согласие", "соглашаюсь", "даю",
    "принимаю", "разрешаю", "подтверждаю", "конечно", "давай", "давайте",
    "продолжим", "продолжаем", "продолжить", "начнём", "начнем", "начинаем",
    "поехали", "готов", "готова", "идёт", "идет", "лады", "ладно",
}


def consent_given(text: str) -> bool:
    """Согласился ли человек словами. Кнопка обрабатывается отдельно.

    Длинную фразу не считаем согласием намеренно: в ней почти наверняка
    есть суть заказа, и проглотить её молча хуже, чем переспросить.
    """
    words = [w for w in re.split(r"\W+", (text or "").lower()) if w]
    if not words or len(words) > 4:
        return False
    return all(w in CONSENT_WORDS for w in words)


_SESSIONS: dict[int, dict] = {}


def new_session() -> dict:
    return {
        "stage": STAGE_CONSENT,
        "consent": False,      # согласие на обработку ПДн получено
        "phone": None,         # подтверждённый Telegram номер клиента
        "contact_name": None,  # имя/фамилия из подтверждённого контакта
        "flow": None,          # 'print' | 'web'
        "category": None,      # код категории
        "payer": None,         # 'ur' | 'fiz' (только для «Меню»)
        "history": [],         # [{'role': 'user'|'assistant', 'content': str}] для LLM
        "last_options": [],    # варианты-кнопки последнего вопроса LLM
        "order_spec": {},      # накопленные параметры заказа
        "last_quote": None,    # {'min','max','term'} последний расчёт
        "final_brief": None,   # текст финального ТЗ
        "attachments": [],     # [{'type': 'photo'|'document', 'file_id': str, 'caption': str}]
        "business_connection_id": None,  # если клиент пишет в личку через Telegram Business
        "gift_service_type": None,  # 'poem' | 'song' | 'coloring_book' — апсейл-подарок
        "gift_step": 0,         # индекс текущего вопроса в наборе полей подарка
        "gift_data": {},        # {'name','age','relation','facts','style'}
        "gift_coloring_mode": None,  # 'story' | 'photo' — только для coloring_book
    }


def get_session(uid: int) -> dict:
    if uid not in _SESSIONS:
        _SESSIONS[uid] = new_session()
    return _SESSIONS[uid]


def reset_session(uid: int) -> dict:
    """Сброс к началу. Согласие и подтверждённый номер сохраняем —
    клиента нельзя гонять по проверкам при каждом «Заново»."""
    old = _SESSIONS.get(uid)
    fresh = new_session()
    if old and old.get("consent"):
        fresh["consent"] = True
        fresh["phone"] = old.get("phone")
        fresh["contact_name"] = old.get("contact_name")
        # если номер уже подтверждён — сразу к выбору направления
        fresh["stage"] = STAGE_FLOW if old.get("phone") else STAGE_PHONE
    _SESSIONS[uid] = fresh
    return fresh


def push_history(sess: dict, role: str, content: str, limit: int = 24) -> None:
    """Добавить реплику в историю диалога, держим последние `limit` сообщений."""
    sess["history"].append({"role": role, "content": content})
    if len(sess["history"]) > limit:
        sess["history"] = sess["history"][-limit:]
