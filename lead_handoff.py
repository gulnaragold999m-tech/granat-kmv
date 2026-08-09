# -*- coding: utf-8 -*-
"""
Приём заявки с сайта в Джарвисе.

ЗАЧЕМ. Клиент заполняет форму на granat-kmv.ru и получает ссылку
t.me/GranatJarvis_bot?start=lead_47. Telegram передаёт боту строку «lead_47»
первым же сообщением. Этот модуль достаёт заявку по номеру и заполняет ею
сессию — Джарвис начинает не с нуля, а с того, что человек уже написал.

Клиента не спрашивают дважды: имя, телефон и задача известны, согласие он
дал в форме. Раньше номер молча выбрасывался, и человек, только что
заполнивший форму, отвечал на те же вопросы второй раз.

ПОЧЕМУ ПО СЕТИ, А НЕ ИЗ ФАЙЛА. Сайт и Джарвис — два разных приложения
Amvera, у каждого свой диск /data. Журнал заявок лежит на диске сайта, и
прочитать его отсюда нельзя физически. Поэтому сайт отдаёт заявку по
защищённому адресу, а мы её забираем.

── ЧТО НУЖНО ЗАДАТЬ В ПЕРЕМЕННЫХ ПРИЛОЖЕНИЯ jarvis-bot ─────────────────
    SITE_URL    — https://granat-kmv.ru
    SITE_TOKEN  — то же значение, что WATCH_TOKEN у сайта.

Без них модуль молчит и не мешает: Джарвис просто работает как раньше,
с нуля. Так задумано — отсутствие настройки не должно ронять бота.
────────────────────────────────────────────────────────────────────────
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor

import requests

import session as sess_mod

logger = logging.getLogger(__name__)

PREFIX = "lead_"

SITE_URL = os.getenv("SITE_URL", "https://granat-kmv.ru").strip().rstrip("/")
SITE_TOKEN = os.getenv("SITE_TOKEN", "").strip()

# Сколько ждём сайт. Клиент в это время смотрит на экран, поэтому лимит
# короткий: лучше начать разговор с нуля, чем молчать десять секунд.
TIMEOUT = 5

# Отметки о ходе заявки шлём в фоне: клиент не должен ждать, пока сайт
# запишет строчку в журнал.
_REPORTER = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lead-report")


def enabled() -> bool:
    return bool(SITE_TOKEN)


def parse_payload(text: str):
    """'/start lead_47' → 47. Ничего похожего — None."""
    if not text:
        return None
    for p in text.split():
        if p.startswith(PREFIX):
            tail = p[len(PREFIX):].strip()
            if tail.isdigit():
                return int(tail)
    return None


def fetch(lead_id: int):
    """Забрать заявку у сайта. None — если нет, не настроено или не ответил."""
    if not enabled():
        logger.info("SITE_TOKEN не задан — заявку с сайта не забираю")
        return None
    try:
        r = requests.get(
            f"{SITE_URL}/api/lead/{lead_id}",
            params={"token": SITE_TOKEN},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return (r.json() or {}).get("lead")
        logger.warning("Заявка %s: сайт ответил %s", lead_id, r.status_code)
    except Exception as e:  # noqa: BLE001
        logger.warning("Заявка %s не забрана: %s: %s", lead_id, type(e).__name__, e)
    return None


def report(lead_id: int, event: str, **fields) -> None:
    """Отметить событие в журнале сайта. Наружу не падает никогда."""
    if not enabled() or not lead_id:
        return

    def job():
        try:
            requests.post(
                f"{SITE_URL}/api/lead/{lead_id}/event",
                params={"token": SITE_TOKEN},
                json={"event": event, **fields},
                timeout=TIMEOUT,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Отметка «%s» по заявке %s не ушла: %s",
                           event, lead_id, e)

    _REPORTER.submit(job)


def cheque(lead: dict) -> str:
    """Человекочитаемый чек из заявки симулятора: сумма и что клиент выбрал."""
    parts = []
    total = lead.get("total")
    if total:
        try:
            parts.append(f"{int(total):,}".replace(",", " ") + " ₽")
        except Exception:  # noqa: BLE001
            parts.append(str(total))
    opts = lead.get("options") or []
    if isinstance(opts, str):
        opts = [opts]
    if opts:
        parts.append(", ".join(str(o) for o in opts))
    return " — ".join(parts)


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
    if lead.get("preferred_channel"):
        sess["order_spec"]["писать в"] = lead["preferred_channel"]
    # Чек из симулятора: сумма и опции, которые клиент сам себе собрал.
    # Джарвис отталкивается от них, а не начинает подбор заново.
    if lead.get("total"):
        sess["order_spec"]["предварительная сумма"] = lead["total"]
    if lead.get("options"):
        sess["order_spec"]["выбранные опции"] = lead["options"]
    if lead.get("scenario"):
        sess["order_spec"]["сфера"] = lead["scenario"]

    # Запоминаем chat_id на стороне сайта: со следующего раза Джарвис сможет
    # написать первым, и клиенту уже не придётся ничего нажимать.
    report(lead.get("id"), "entered_bot", chat_id=uid,
           phone=lead.get("phone", "") or phone, username=username)
    return lead


def apply(update, sess: dict):
    """Разобрать /start. Вернёт заявку, если клиент пришёл по ссылке с сайта."""
    text = getattr(getattr(update, "message", None), "text", "") or ""
    lead_id = parse_payload(text)
    if lead_id is None:
        return None
    return apply_by_id(
        lead_id, update.effective_user.id, sess,
        username=getattr(update.effective_user, "username", "") or "",
    )


def apply_by_id(lead_id: int, uid, sess: dict, username: str = ""):
    """То же, но по готовому номеру — для кнопки «Да, уточним детали»."""
    lead = fetch(lead_id)
    if not lead:
        return None
    lead.setdefault("id", lead_id)
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
    chk = cheque(lead)
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


def first_message(lead: dict) -> str:
    """Реплика клиента для истории диалога — его же словами из формы.

    Джарвису нужна хотя бы одна реплика собеседника: с пустой историей LLM
    задаёт первый вопрос вслепую и переспрашивает то, что человек уже
    написал на сайте. Здесь мы отдаём ей ровно то, что он написал.
    """
    parts = []
    if lead.get("service"):
        parts.append(f"Мне нужно: {lead['service']}")
    if lead.get("notes"):
        parts.append(lead["notes"])
    chk = cheque(lead)
    if chk:
        parts.append(f"На сайте я собрал конфигурацию: {chk}")
    if not parts:
        parts.append("Я оставил заявку на сайте, подробности пока не написал.")
    return ". ".join(parts)


def postponed(lead_id: int) -> None:
    """Клиент нажал «Позже». Фиксируем — Генерал не будет считать это тишиной,
    но и из виду не потеряет."""
    report(lead_id, "postponed")


def brief_ready(lead_id: int, brief: str) -> None:
    """ТЗ собрано. Отмечаем в журнале, чтобы сторож перестал напоминать
    об этой заявке, а Генерал увидел, что конвейер дошёл до конца."""
    report(lead_id, "brief_ready", brief=(brief or "")[:2000])
