# -*- coding: utf-8 -*-
"""
Приём заявки с сайта в Джарвисе. Вставляется в jarvis_bot.py.

Что делает: когда клиент приходит по ссылке t.me/GranatJarvis_bot?start=lead_47,
Telegram передаёт боту строку «lead_47» первым же сообщением. Этот модуль
достаёт по номеру заявку, которую сайт уже сохранил, заполняет ею сессию —
и Джарвис начинает не с нуля, а с того, что клиент уже написал в форме.

Клиента не спрашивают дважды. Имя, телефон и направление уже известны, поэтому
согласие и проверка номера пропускаются: телефон он оставил на сайте сам.

── КАК ПОДКЛЮЧИТЬ ────────────────────────────────────────────────────────────

1. Положить файл рядом с jarvis_bot.py.

2. В jarvis_bot.py добавить импорт:

       import lead_handoff

3. В обработчике /start, в самом начале, до вопроса о согласии:

       async def cmd_start(update, context):
           uid = update.effective_user.id
           sess = get_session(uid)

           picked = lead_handoff.apply(update, sess)
           if picked:
               await update.message.reply_text(
                   lead_handoff.greeting(picked), parse_mode="HTML")
               # дальше — сразу в диалог сбора ТЗ, минуя согласие и телефон
               return await ask_next_question(update, context)

           ... обычный сценарий с нуля ...

4. Добавить обработчик кнопок «Да, уточним детали» / «Позже» — их присылает
   сайт тем клиентам, кому Джарвис написал первым:

       elif data.startswith("lead:"):
           _, action, lead_id = data.split(":")
           if action == "start":
               picked = lead_handoff.apply_by_id(int(lead_id), uid, sess)
               ...
           else:
               lead_handoff.postponed(int(lead_id))

──────────────────────────────────────────────────────────────────────────────
"""

import logging

import leads
import session as sess_mod

logger = logging.getLogger(__name__)

PREFIX = "lead_"


def parse_payload(text: str):
    """'/start lead_47' → 47. Ничего похожего — None."""
    if not text:
        return None
    parts = text.split()
    for p in parts:
        if p.startswith(PREFIX):
            tail = p[len(PREFIX):].strip()
            if tail.isdigit():
                return int(tail)
    return None


def _fill(lead: dict, uid, sess: dict, phone: str = "", username: str = ""):
    """Перенести данные заявки в сессию бота и отметить вход в журнале."""
    sess["consent"] = True          # согласие клиент дал на сайте, в форме
    sess["phone"] = lead.get("phone") or phone or None
    sess["contact_name"] = lead.get("name") or None
    sess["stage"] = sess_mod.STAGE_DIALOG
    sess["order_spec"] = {
        "lead_id": lead.get("id"),
        "источник": "заявка с сайта",
        "имя": lead.get("name", ""),
        "контакт": lead.get("phone", ""),
    }
    if lead.get("service"):
        sess["order_spec"]["что нужно"] = lead["service"]
    if lead.get("notes"):
        sess["order_spec"]["пожелания клиента"] = lead["notes"]
    # Чек из симулятора: сумма и опции, которые клиент сам себе собрал.
    # Джарвис отталкивается от них, а не начинает подбор заново.
    if lead.get("total"):
        sess["order_spec"]["предварительная сумма"] = lead["total"]
    if lead.get("options"):
        sess["order_spec"]["выбранные опции"] = lead["options"]
    if lead.get("scenario"):
        sess["order_spec"]["сфера"] = lead["scenario"]

    # Запоминаем chat_id: со следующего раза Джарвис сможет написать первым,
    # и клиенту уже не придётся ничего нажимать.
    leads.link_client(
        lead["id"], uid,
        phone=lead.get("phone", "") or phone,
        username=username,
    )
    return lead


def apply(update, sess: dict):
    """Разобрать /start. Вернёт заявку, если клиент пришёл по ссылке с сайта."""
    text = getattr(getattr(update, "message", None), "text", "") or ""
    lead_id = parse_payload(text)
    if lead_id is None:
        return None
    return apply_by_id(lead_id, update.effective_user.id, sess,
                       username=getattr(update.effective_user, "username", "") or "")


def apply_by_id(lead_id: int, uid, sess: dict, username: str = ""):
    """То же, но по готовому номеру — для кнопки «Да, уточним детали»."""
    lead = leads.find(lead_id)
    if not lead:
        logger.warning("Заявка %s не найдена в журнале", lead_id)
        return None
    return _fill(lead, uid, sess, username=username)


def greeting(lead: dict) -> str:
    """Первое сообщение: показать клиенту, что его уже знают."""
    name = lead.get("name") or "Здравствуйте"
    out = [f"{name}, вижу вашу заявку с сайта — №{lead.get('id')}."]
    known = []
    if lead.get("service"):
        known.append(f"• Задача: <b>{lead['service']}</b>")
    if lead.get("phone"):
        known.append(f"• Контакт: {lead['phone']}")
    if lead.get("notes"):
        known.append(f"• Пожелания: {lead['notes']}")
    chk = leads.cheque(lead)
    if chk:
        known.append(f"• Конфигурация: <b>{chk}</b>")
    if known:
        out.append("Уже записал:")
        out.extend(known)
    out.append(
        "Заново ничего заполнять не нужно. Уточню несколько деталей — "
        "и Гульнара сразу назовёт стоимость и срок."
    )
    return "\n".join(out)


def postponed(lead_id: int) -> None:
    """Клиент нажал «Позже». Фиксируем — Генерал не будет считать это тишиной,
    но и из виду не потеряет."""
    leads.log(lead_id, "postponed")


def brief_ready(lead_id: int, brief: str) -> None:
    """ТЗ собрано. Отмечаем в журнале, чтобы сторож перестал напоминать
    об этой заявке, а Генерал увидел, что конвейер дошёл до конца."""
    leads.log(lead_id, "brief_ready", brief=brief[:2000])
