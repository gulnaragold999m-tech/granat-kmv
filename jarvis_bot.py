#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Джарвис — думающий ИИ-агент студии «Гранат».

Архитектура:
  • Навигация — детерминированный каскад inline-кнопок (2 направления →
    категории порциями). Никакой «простыни» из 13 кнопок.
  • Сбор параметров заказа — Dialog Manager (LLM): один умный вопрос за раз,
    авто-сужение материалов, контекст всей беседы.
  • Финал — подтверждение ТЗ клиентом → «🔥 ГОРЯЧАЯ ЗАЯВКА» администратору
    с типом плательщика и прямой ссылкой на диалог (tg://user?id=...).

Запуск: python jarvis_bot.py
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import asyncio
import html
import logging
import random

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, BusinessConnectionHandler, ContextTypes, filters,
)

import config
import dialog_manager
import fraud_check
import gift_manager
import keyboards as kbd
import knowledge_base as kb
import lead_handoff
import session as ss
import speech
import vk_jarvis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# httpx печатает полный адрес каждого запроса к Telegram, а токен бота —
# часть этого адреса. Без этой строки токен попадает в логи Amvera.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("jarvis")


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные
# ─────────────────────────────────────────────────────────────────────────────

GREETING = (
    "🍇 Здравствуй! Я Джарвис — цифровой ассистент студии «Гранат» "
    "(г. Лермонтов, работаем по всему КМВ).\n\n"
    "Помогу оформить заказ на печать или IT-разработку и составлю "
    "техническое задание — как живой технолог, только быстрее.\n\n"
    "Для оформления заявки мне понадобятся твои контактные данные "
    "(имя, номер телефона, username Telegram). Продолжая, ты даёшь "
    "согласие на их обработку — они нужны только менеджеру студии "
    "для связи по заказу и никуда больше не передаются."
)

# Ответ на текст вместо кнопки согласия. Приветствие второй раз подряд не
# повторяем: человек его уже прочитал, а из фразы «понадобятся твои
# контактные данные (имя…)» понял, что надо написать имя, — и написал.
CONSENT_HINT = (
    "Имя и задачу спрошу дальше — сейчас нужно только твоё согласие "
    "на обработку данных.\n\n"
    "Нажми кнопку «✅ Даю согласие» под приветствием — или просто "
    "напиши «да»."
)

ASK_PHONE = (
    "Спасибо! ✅\n\n"
    "Теперь подтверди, пожалуйста, номер телефона — нажми кнопку "
    "«📱 Отправить мой номер» внизу экрана.\n\n"
    "Это защита от мошенников: Telegram передаёт номер только "
    "настоящего владельца аккаунта, вручную его подделать нельзя."
)

WELCOME = "С чего начнём?"


# ── Апсейл-подарок после заказа ────────────────────────────────────────────
# Предлагается ТОЛЬКО кнопками после подтверждённого заказа, и это ПЛАТНАЯ
# услуга — цена показывается сразу, дальше отдельным шагом (kb_gift_price_confirm)
# берётся явное согласие клиента, и только после «да» начинается сбор данных
# и генерация. Стоимость входит в общий счёт заказа (см. GIFT_PRICES).

GIFT_OFFER_TEXT = (
    "🎁 Кстати! Хочешь особенный подарок в придачу — персональный стих, "
    "песню или сказку-раскраску специально для именинника? Сочиню за пару "
    "минут, это платная услуга — добавим в счёт заказа."
)

# (ключ поля, текст вопроса) — по одному вопросу за раз, порядок как в payload.
# Разные наборы полей для разных услуг: у раскраски-сказки своя, более детская
# логика вопросов (имя+возраст одним вопросом, мечты/герои вместо «фактов»).
GIFT_FIELDS_DEFAULT = [  # стих, песня
    ("name",     "Как зовут именинника?"),
    ("age",      "Сколько лет исполняется? (если не хочешь указывать — "
                 "нажми кнопку ниже или напиши «пропустить»)"),
    ("relation", "Кем именинник приходится тебе (или заказчику)?"),
    ("facts",    "Расскажи пару фактов о нём/ней: увлечения, характер, "
                 "забавные привычки, внутренние шутки — чем ярче, тем лучше "
                 "получится подарок"),
]

GIFT_FIELDS_COLORING_STORY = [  # раскраска-сказка (не фото)
    ("name",  "Как зовут ребёнка и сколько ему лет?"),
    ("facts", "Кем мечтает стать или каких супергероев/животных он(а) "
              "любит больше всего? (например: космонавтом, гонщиком, "
              "любит динозавров, щенячий патруль)"),
]


def _gift_fields_for(sess: dict) -> list:
    if sess.get("gift_service_type") == "coloring_book":
        return GIFT_FIELDS_COLORING_STORY
    return GIFT_FIELDS_DEFAULT


GIFT_STYLE_LABELS = {
    "humor": "Юмор",
    "touching": "Трогательно до слез",
    "drive": "Драйв",
    "toast": "Кавказское застолье (мудрые кавказские тосты/притчи)",
    "chanson": "Душевный шансон",
    "poprap": "Современный поп/рэп",
}

GIFT_GENRE_LABELS = {  # жанр раскраски-сказки — переиспользует поле "style" в payload
    "space": "Космическое приключение",
    "knights": "Волшебная сказка с рыцарями",
    "racing": "Весёлые гонки и машины",
    "animals": "Спасение планеты с животными",
}

GIFT_SERVICE_LABELS = {
    "poem": "✍️ Стих / Поздравление",
    "song": "🎵 Персональная песня",
    "coloring_book": "🎨 Книга-раскраска",
}

# (Fix #13: вынесли константы для переиспользования)
PAYER_LABELS = {
    "ur": "🏢 ЮРЛИЦО / ИП",
    "fiz": "👤 ФИЗЛИЦО",
}


async def _send_gift_step(target, sess: dict) -> None:
    """Следующий вопрос гифт-опроса, либо кнопки стиля, если поля закончились.

    Вызывается ВСЕГДА (даже если клиент написал текст вместо нажатия кнопки
    на шаге выбора стиля) — так бот никогда не «зависает» молча, а просто
    повторяет актуальный вопрос/кнопки. Отправка через _send_plain — с
    повторами при сетевых сбоях (иначе один «моргнувший» TimedOut на
    облачном хостинге обрывает диалог без единого сообщения клиенту)."""
    fields = _gift_fields_for(sess)
    step = sess["gift_step"]
    if step < len(fields):
        field_key, question = fields[step]
        markup = kbd.kb_gift_age_controls() if field_key == "age" else kbd.kb_dialog_controls()
        await _send_plain(target, question, markup)
    elif sess.get("gift_service_type") == "coloring_book":
        await _send_plain(
            target, "И последнее — выбери жанр нашей будущей раскраски:",
            kbd.kb_gift_genre(),
        )
    else:
        await _send_plain(
            target, "И последнее — какой стиль подарка выбрать?",
            kbd.kb_gift_style(),
        )


async def _deliver_gift_result(thinking_msg, msg_obj, text: str, markdown: bool = True) -> None:
    """markdown=False — для служебных сообщений (например, текста об ошибке
    с @username студии): звёздочки/подчёркивания там не нужны, а юзернейм с
    "_" ломает Telegram-разметку (пример: 'Can't parse entities').
    (Fix #12: используем _edit_or_reply для избежания повторения кода)"""
    markup = kbd.kb_dialog_controls()
    parse_mode = ParseMode.MARKDOWN if markdown else None
    try:
        await _edit_or_reply(thinking_msg, msg_obj, text, reply_markup=markup, parse_mode=parse_mode)
    except RuntimeError as e:
        # LLM мог вернуть текст, ломающий Markdown-разметку Telegram — не
        # роняем доставку подарка клиенту из-за этого, шлём как есть.
        logger.warning("Markdown-парсинг подарка не прошёл (%s), отправляю без форматирования", e)
        await msg_obj.reply_text(text, reply_markup=markup)


async def _finalize_gift(ctx: ContextTypes.DEFAULT_TYPE, uid: int, sess: dict, msg_obj) -> None:
    """Все поля собраны — один запрос к LLM и доставка готового подарка."""
    payload = {
        "service_type": sess.get("gift_service_type"),
        "name": sess["gift_data"].get("name") or "",
        "age": sess["gift_data"].get("age") or "",
        "relation": sess["gift_data"].get("relation") or "",
        "facts": sess["gift_data"].get("facts") or "",
        "style": sess["gift_data"].get("style") or "",
    }
    thinking = await _send_plain(msg_obj, "🎁 Секунду, сочиняю персональный подарок…")
    try:
        text = await asyncio.to_thread(gift_manager.generate_gift, payload)
    except Exception as e:  # noqa: BLE001
        logger.error("Gift generation error: %s", e)
        await _deliver_gift_result(
            thinking, msg_obj,
            "😔 Не получилось сочинить подарок. Попробуй ещё раз чуть позже "
            f"или напиши нам: {config.STUDIO['contact']}",
            markdown=False,
        )
        sess["stage"] = ss.STAGE_FLOW
        return

    await _deliver_gift_result(thinking, msg_obj, text)
    sess["stage"] = ss.STAGE_FLOW

    if config.ADMIN_ID:
        price = config.GIFT_PRICES.get(payload["service_type"])
        price_line = f"{price} ₽" if price else "цена по договорённости"
        try:
            await ctx.bot.send_message(
                chat_id=config.ADMIN_ID,
                text=(f"🎁 Клиенту сгенерирован платный подарок "
                      f"({GIFT_SERVICE_LABELS.get(payload['service_type'], payload['service_type'])}, "
                      f"{price_line}) для «{payload['name']}» — добавь к счёту заказа:\n\n{text}"),
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Не удалось переслать подарок админу: %s", e)


# Живые фразы ожидания — клиент видит, что его услышали и заказ собирается.
THINKING_PHRASES = [
    "💭 Секунду, обдумываю твой заказ…",
    "🤔 Так, записываю и прикидываю варианты…",
    "✍️ Понял тебя! Минутку, соображаю, что предложить…",
    "🧮 Собираю детали заказа, секундочку…",
]


async def _send_plain(msg_obj, text: str, markup=None, parse_mode=None):
    """Отправка с повторами: сеть до Telegram иногда «моргает» (TimedOut).
    (Fix #11: добавлено логирование успеха)

    parse_mode нужен приветствию по заявке с сайта — там жирным выделена
    задача клиента. Остальные вызовы шлют обычный текст, как и раньше.
    """
    for attempt in range(3):
        try:
            result = await msg_obj.reply_text(
                text, reply_markup=markup, parse_mode=parse_mode)
            if attempt > 0:
                logger.info("Message sent after retry %d", attempt)
            return result
        except (TimedOut, NetworkError) as e:
            if attempt == 2:
                logger.error("Failed to send message after 3 attempts: %s", e)
            else:
                logger.warning("send retry %s/3 after %s", attempt + 1, e)
            await asyncio.sleep(2 * (attempt + 1))
    return None


async def _edit_or_reply(thinking_msg, msg_obj, text: str, **kwargs):
    """Вспомогательная функция для редактирования или отправки нового сообщения.
    (Fix #12: избегаем повторения кода в _deliver и _deliver_gift_result)"""
    if thinking_msg is not None:
        try:
            return await thinking_msg.edit_text(text, **kwargs)
        except (TimedOut, NetworkError, RuntimeError) as e:
            logger.warning("edit failed (%s), отправляю новым сообщением", e)
    return await msg_obj.reply_text(text, **kwargs)


async def _deliver(thinking_msg, msg_obj, text: str, confirm: bool = False,
                   options: list | None = None):
    """Показать ответ клиенту.

    Если ранее отправляли «думаю…» — превращаем его в ответ (edit),
    чтобы не плодить сообщения. Если редактирование не удалось — шлём новым.
    options — кнопки-варианты ответа под вопросом.
    (Fix #12: используем _edit_or_reply для избежания повторения кода)
    """
    if confirm:
        markup = kbd.kb_confirm()
    else:
        markup = kbd.kb_dialog(options or [])
    await _edit_or_reply(thinking_msg, msg_obj, text, reply_markup=markup)


# ── Напоминание о незавершённом заказе ─────────────────────────────────────

REMINDER_DELAY_SECONDS = 20 * 60  # 20 минут без ответа клиента


def _reminder_job_name(uid: int) -> str:
    return f"reminder:{uid}"


def _cancel_reminder(ctx: ContextTypes.DEFAULT_TYPE, uid: int) -> None:
    if not ctx.job_queue:
        return
    for job in ctx.job_queue.get_jobs_by_name(_reminder_job_name(uid)):
        job.schedule_removal()


def _schedule_reminder(ctx: ContextTypes.DEFAULT_TYPE, uid: int, sess: dict) -> None:
    """(Пере)запустить таймер напоминания. Вызывается при каждом сообщении
    Джарвиса в рамках заказа — так напоминание всегда отсчитывается от
    последней реплики бота, на которую клиент не ответил."""
    _cancel_reminder(ctx, uid)
    if not ctx.job_queue:
        return
    ctx.job_queue.run_once(
        _send_reminder, REMINDER_DELAY_SECONDS,
        name=_reminder_job_name(uid),
        data={"uid": uid, "business_connection_id": sess.get("business_connection_id")},
    )


async def _send_reminder(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    data = ctx.job.data
    uid = data["uid"]
    sess = ss.get_session(uid)
    # Заказ уже оформлен/сброшен — напоминать не о чем.
    if sess["stage"] not in (ss.STAGE_DIALOG, ss.STAGE_CONFIRM):
        return
    if sess["stage"] == ss.STAGE_CONFIRM:
        text = (
            "Привет! 👋 Ты дошёл(а) до сводки заказа, но пока не подтвердил(а) "
            "её. Если всё верно — жми кнопку ниже. Если нужно что-то поменять — "
            "просто напиши."
        )
        markup = kbd.kb_confirm()
    else:
        text = (
            "Привет! 👋 Похоже, ты не закончил(а) оформление заказа. Если ещё "
            "актуально — просто продолжи, я на связи. Если передумал(а) — "
            "ничего страшного 🙂"
        )
        markup = kbd.kb_dialog_controls()
    try:
        await ctx.bot.send_message(
            chat_id=uid, text=text, reply_markup=markup,
            business_connection_id=data.get("business_connection_id"),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Не удалось отправить напоминание %s: %s", uid, e)


def _apply_llm_result(sess: dict, result: dict) -> None:
    """Зафиксировать в сессии то, что LLM собрал на этом шаге."""
    collected = result.get("collected") or {}
    if isinstance(collected, dict):
        sess["order_spec"].update(collected)
    if result.get("quote"):
        sess["last_quote"] = result["quote"]
    if result.get("brief"):
        sess["final_brief"] = result["brief"]
    sess["stage"] = ss.STAGE_CONFIRM if result.get("status") == "ready" else ss.STAGE_DIALOG


async def _run_dialog_step(ctx: ContextTypes.DEFAULT_TYPE, uid: int, sess: dict,
                           reply_target, thinking_msg=None) -> None:
    """Один шаг умного диалога: «думаю…» → LLM → ответ клиенту.

    thinking_msg — сообщение-заглушка «думаю…», если его уже показали
    (например, из меню). Если нет — отправим сами, чтобы клиент сразу
    видел: его услышали, заказ собирается.
    """
    msg_obj = getattr(reply_target, "message", None) or reply_target

    if thinking_msg is None:
        thinking_msg = await _send_plain(msg_obj, random.choice(THINKING_PHRASES))

    try:
        result = await asyncio.to_thread(dialog_manager.process, sess)
    except Exception as e:  # noqa: BLE001
        logger.error("LLM error: %s", e)
        await _deliver(
            thinking_msg, msg_obj,
            "😔 Не получилось связаться с мозговым центром. Попробуй ещё раз "
            f"через минуту или напиши нам напрямую: {config.STUDIO['contact']}",
        )
        _schedule_reminder(ctx, uid, sess)
        return

    _apply_llm_result(sess, result)
    ss.push_history(sess, "assistant", result["message"])
    is_confirm = sess["stage"] == ss.STAGE_CONFIRM
    # Fix #10: ограничиваем last_options чтобы избежать накопления данных
    if is_confirm:
        sess["last_options"] = []
    else:
        sess["last_options"] = (result.get("options") or [])[-10:]  # максимум 10 вариантов
    await _deliver(
        thinking_msg, msg_obj, result["message"],
        confirm=is_confirm,
        options=sess["last_options"],
    )
    _schedule_reminder(ctx, uid, sess)


def _payer_label(payer: str) -> str:
    """Возвращает человеческое описание типа плательщика (Fix #13: используем константу)."""
    return PAYER_LABELS.get(payer, "не указан")


async def _notify_admin(ctx: ContextTypes.DEFAULT_TYPE, user, sess: dict) -> bool:
    """Skill 3: «🔥 ГОРЯЧАЯ ЗАЯВКА» администратору."""
    if not config.ADMIN_ID:
        logger.warning("ADMIN_ID не задан в .env — заявка не отправлена админу!")
        return False

    flow_title = kb.FLOWS[sess["flow"]]["title"] if sess.get("flow") else "—"
    cat_title = kb.category_title(sess.get("flow") or "", sess.get("category") or "")
    name = html.escape(sess.get("contact_name") or user.full_name or "клиент")
    username = f"@{user.username}" if user.username else "нет username"
    phone = html.escape(sess.get("phone") or "не подтверждён")
    brief = html.escape(sess.get("final_brief") or "— (см. параметры ниже)")

    # Канал связи показываем отдельной строкой вверху: это первое, что нужно
    # знать перед ответом клиенту, а не строчка в общем списке параметров.
    spec = dict(sess.get("order_spec", {}))
    channel = spec.pop(dialog_manager.CHANNEL_FIELD, "") or "не указан"
    channel_icons = {"Telegram": "✈️", "WhatsApp": "🟢", "VK": "🔵"}
    channel_line = f"{channel_icons.get(channel, '❔')} {html.escape(str(channel))}"

    spec_lines = "\n".join(
        f"  • {html.escape(str(k))}: {html.escape(str(v))}"
        for k, v in spec.items()
    ) or "  —"
    att_line = ""
    n_att = len(sess.get("attachments") or [])
    if n_att:
        att_line = f"\n📎 Вложений от клиента: {n_att} (см. выше в чате)\n"

    # Fix #5: явно преобразуем user.id в int для безопасности
    user_id = int(user.id)
    text = (
        "🔥 <b>ГОРЯЧАЯ ЗАЯВКА</b>\n\n"
        f"👤 Клиент: <a href=\"tg://user?id={user_id}\">{name}</a> ({username})\n"
        f"📞 Телефон (подтверждён Telegram): {phone}\n"
        f"💬 Писать клиенту в: <b>{channel_line}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💼 Плательщик: {_payer_label(sess.get('payer'))}\n"
        f"📂 Направление: {flow_title}\n"
        f"📌 Категория: {cat_title}\n"
        f"{att_line}\n"
        f"<b>ТЗ:</b>\n<pre>{brief}</pre>\n"
        f"<b>Параметры:</b>\n{spec_lines}\n\n"
        f"➡️ Написать клиенту: <a href=\"tg://user?id={user_id}\">открыть диалог</a>"
    )
    try:
        await ctx.bot.send_message(
            chat_id=config.ADMIN_ID, text=text,
            parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Не удалось отправить заявку админу: %s", e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Хендлеры
# ─────────────────────────────────────────────────────────────────────────────

FRAUD_NO_FILES = (
    "Я читаю только текст — картинку разобрать не могу.\n\n"
    "Перешлите сообщение текстом или перескажите своими словами: что "
    "пишут, чего просят, есть ли ссылка."
)


async def _fraud_guard(msg_obj, sess: dict, text: str,
                       has_files: bool = False) -> bool:
    """Разбор мошеннических сообщений. True — ответили, дальше не идём.

    Стоит ПЕРЕД проверками согласия и номера сознательно: человеку, которому
    прямо сейчас звонит «служба безопасности», нельзя предлагать сначала
    подтвердить телефон. Персональные данные здесь и не собираются — текст
    разбирается на месте, никуда не отправляется и не попадает в заявку.
    """
    if sess.get("fraud_mode"):
        if has_files and not text:
            await _send_plain(msg_obj, FRAUD_NO_FILES)
            return True
        if fraud_check.wants_exit(text):
            sess["fraud_mode"] = False
            await msg_obj.reply_text(fraud_check.EXIT_MESSAGE,
                                     reply_markup=kbd.kb_flows())
            return True
        await _send_plain(msg_obj, fraud_check.answer(text))
        return True

    action = fraud_check.triage(text)

    if action == "stolen":
        sess["fraud_mode"] = True
        await _send_plain(msg_obj, fraud_check.STOLEN)
    elif action == "enter":
        sess["fraud_mode"] = True
        await _send_plain(msg_obj, fraud_check.ENTER_MESSAGE)
    elif action == "report":
        sess["fraud_mode"] = True
        await _send_plain(msg_obj, fraud_check.answer(text))
    elif action == "alarm":
        # Человек переслал сообщение, ни о чём не прося, — а в нём набор
        # классических приёмов. Молчать нельзя. Режим при этом НЕ включаем:
        # настоящий клиент должен продолжить оформлять заказ, а не застрять
        # в проверке из-за неудачной формулировки.
        await _send_plain(
            msg_obj,
            "⚠️ Стоп. Это не похоже на заказ — это похоже на обман.\n\n"
            + fraud_check.report(text)
            + "\n\nЕсли вы всё-таки по заказу — напишите «меню».",
        )
    else:
        return False
    return True


async def cmd_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/check — включить проверку на мошенников."""
    sess = ss.get_session(update.effective_user.id)
    sess["fraud_mode"] = True
    await _send_plain(update.effective_message, fraud_check.ENTER_MESSAGE)


async def _start_from_site_lead(ctx: ContextTypes.DEFAULT_TYPE, uid: int,
                                sess: dict, msg_obj, lead: dict) -> None:
    """Начать разговор с уже известной заявкой вместо расспросов с нуля."""
    await _send_plain(msg_obj, lead_handoff.greeting(lead),
                      parse_mode=ParseMode.HTML)
    ss.push_history(sess, "user", lead_handoff.first_message(lead))
    await _run_dialog_step(ctx, uid, sess, msg_obj)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    _cancel_reminder(ctx, uid)
    sess = ss.reset_session(uid)
    msg = update.effective_message

    # Клиент пришёл по ссылке с сайта: /start lead_47. Имя, телефон и задача
    # у нас уже есть — он всё это заполнил в форме, а согласие дал там же.
    # Заявку забираем у сайта по сети: журнал лежит на его диске, у нас
    # своего доступа к нему нет. Запрос блокирующий, поэтому в отдельном
    # потоке — иначе на время ожидания встал бы весь бот.
    picked = await asyncio.to_thread(lead_handoff.apply, update, sess)
    if picked:
        await _start_from_site_lead(ctx, uid, sess, msg, picked)
        return

    # Проверки проходятся один раз: согласие → номер → меню
    if not sess["consent"]:
        await msg.reply_text(GREETING, reply_markup=kbd.kb_consent())
    elif not sess["phone"]:
        await msg.reply_text(ASK_PHONE, reply_markup=kbd.kb_contact())
    else:
        await msg.reply_text(WELCOME, reply_markup=kbd.kb_flows())


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


async def on_business_connection(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Telegram Business: подключили/отключили Джарвиса к личному аккаунту.
    Только лог для контроля — сам диалог дальше идёт через business_message,
    который приходит как обычный Update и обрабатывается теми же хендлерами."""
    bc = update.business_connection
    state = "включён ✅" if bc.is_enabled else "отключён"
    logger.info(
        "Business-подключение %s: аккаунт %s, id=%s",
        state, bc.user.full_name, bc.id,
    )


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    sess = ss.get_session(uid)
    sess["business_connection_id"] = getattr(q.message, "business_connection_id", None)
    ns, a, b = kbd.parse_cb(q.data)

    # ── Заявка с сайта ──────────────────────────────────────────────────────
    # Эти кнопки сайт присылает тем, чей chat_id он уже знает: человеку не
    # нужно ничего нажимать на странице, Джарвис пишет ему сам. Кнопки
    # приходили, но обработчика для них не было — нажатие не делало ничего.
    if ns == "lead":
        lead_id = int(b) if b.isdigit() else 0

        if a == "later":
            lead_handoff.postponed(lead_id)
            await q.edit_message_text(
                "Хорошо, не тороплю. Напишите, когда будет удобно, — "
                "я помню вашу заявку и продолжу с того же места."
            )
            return

        if a == "start":
            picked = await asyncio.to_thread(
                lead_handoff.apply_by_id, lead_id, uid, sess,
                getattr(q.from_user, "username", "") or "",
            )
            if not picked:
                # Заявку не отдали — вести диалог вслепую хуже, чем честно
                # начать сначала.
                await q.edit_message_text(
                    "Не нашёл эту заявку. Давайте соберём заново — это быстро."
                )
                await q.message.reply_text(WELCOME, reply_markup=kbd.kb_flows())
                return
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001
                pass
            await _start_from_site_lead(ctx, uid, sess, q.message, picked)
            return

    # ── Системные кнопки ────────────────────────────────────────────────────
    if ns == "sys":
        if a == "consent":
            sess["consent"] = True
            sess["stage"] = ss.STAGE_PHONE
            await q.edit_message_text(GREETING + "\n\n✅ Согласие получено.")
            # reply-клавиатуру с кнопкой контакта нельзя прикрепить через
            # редактирование — шлём отдельным сообщением
            await q.message.reply_text(ASK_PHONE, reply_markup=kbd.kb_contact())
            return

        if a in ("home", "cancel"):
            _cancel_reminder(ctx, uid)
            sess = ss.reset_session(uid)
            if not sess["consent"]:
                await q.edit_message_text(GREETING, reply_markup=kbd.kb_consent())
            elif not sess["phone"]:
                await q.message.reply_text(ASK_PHONE, reply_markup=kbd.kb_contact())
            else:
                await q.edit_message_text(WELCOME, reply_markup=kbd.kb_flows())
            return

        if a == "back":
            # один шаг назад по каскаду — заказ, который тут собирали, брошен
            _cancel_reminder(ctx, uid)
            if sess["stage"] in (ss.STAGE_PAYER, ss.STAGE_DIALOG, ss.STAGE_CONFIRM) and sess["flow"]:
                sess["stage"] = ss.STAGE_CAT
                sess["category"] = None
                sess["payer"] = None
                sess["history"].clear()
                sess["order_spec"].clear()
                await q.edit_message_text(
                    f"{kb.FLOWS[sess['flow']]['title']} — выбери категорию:",
                    reply_markup=kbd.kb_categories(sess["flow"]),
                )
            else:
                sess = ss.reset_session(uid)
                await q.edit_message_text(WELCOME, reply_markup=kbd.kb_flows())
            return

        if a == "amend":
            # клиент хочет дополнить ТЗ — возвращаемся в диалог
            sess["stage"] = ss.STAGE_DIALOG
            await q.edit_message_text(
                "✏️ Хорошо! Напиши, что изменить или добавить к заказу.",
                reply_markup=kbd.kb_dialog_controls(),
            )
            _schedule_reminder(ctx, uid, sess)
            return

        if a == "confirm":
            if sess["stage"] != ss.STAGE_CONFIRM:
                await q.edit_message_text(WELCOME, reply_markup=kbd.kb_flows())
                return
            sent = await _notify_admin(ctx, q.from_user, sess)

            # Заявка с сайта дошла до конца конвейера: сторож тишины должен
            # перестать про неё напоминать, а в журнале — остаться ТЗ.
            site_lead = sess.get("order_spec", {}).get("lead_id")
            if site_lead:
                lead_handoff.brief_ready(site_lead, sess.get("final_brief") or "")

            s = config.STUDIO
            if sent:
                msg = (
                    "✅ Заявка оформлена и уже у менеджера!\n\n"
                    "Менеджер рассчитает точную стоимость и свяжется с тобой. "
                    "Напомню: работаем по предоплате 50% — реквизиты пришлёт "
                    "менеджер.\n\n"
                    f"Если срочно: {s['phone']} или {s['contact']}\n"
                    f"📍 {s['address']} ({s['hours']})"
                )
            else:
                msg = (
                    "✅ Заявка сохранена, но автоуведомление менеджеру не прошло.\n"
                    f"Продублируй, пожалуйста, напрямую: {s['contact']} "
                    f"или {s['phone']}"
                )
            # Сводку заказа не затираем — убираем только кнопки под ней,
            # а подтверждение шлём отдельным сообщением.
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001
                pass
            await _send_plain(q.message, msg)
            _cancel_reminder(ctx, uid)
            ss.reset_session(uid)
            # Апсейл-подарок — только по явному согласию клиента (кнопки
            # ниже, «Нет, спасибо» ничего не запускает).
            await _send_plain(q.message, GIFT_OFFER_TEXT, kbd.kb_gift_offer())
            return

    # ── Навигация по каскаду ────────────────────────────────────────────────
    if ns == "nav":
        if a == "flow" and b in kb.FLOWS:
            sess["flow"] = b
            sess["stage"] = ss.STAGE_CAT
            await q.edit_message_text(
                f"{kb.FLOWS[b]['title']} — выбери категорию:",
                reply_markup=kbd.kb_categories(b),
            )
            return

        if a == "cat" and sess.get("flow"):
            sess["category"] = b
            sess["history"].clear()
            sess["order_spec"].clear()
            sess["final_brief"] = None
            sess["last_quote"] = None

            # Спец-ветка: «Меню» → сначала фильтр Юрлицо/Физлицо
            if b == "menu":
                sess["stage"] = ss.STAGE_PAYER
                await q.edit_message_text(
                    "🍽️ Печать меню — отличный выбор!\n\n"
                    "Подскажи, оформляем заказ на физическое лицо или от "
                    "организации (Юрлицо/ИП) с закрывающими документами?",
                    reply_markup=kbd.kb_payer(),
                )
                return

            # Обычная категория → сразу запускаем умный диалог
            sess["stage"] = ss.STAGE_DIALOG
            cat_title = kb.category_title(sess["flow"], b)
            ss.push_history(sess, "user", f"Клиент выбрал категорию: {cat_title}. Начни диалог.")
            thinking = await q.edit_message_text(
                f"{cat_title} — секунду, вникаю в задачу… 🤔"
            )
            await _run_dialog_step(ctx, uid, sess, q.message, thinking_msg=thinking)
            return

    # ── Быстрые ответы диалога ──────────────────────────────────────────────
    if ns == "dlg":
        if a == "opt":
            # Клиент нажал кнопку-вариант ответа
            opts = sess.get("last_options") or []
            try:
                choice = opts[int(b)]
            except (ValueError, IndexError):
                # Fix #8: сообщаем клиенту, что кнопка неактивна, вместо молчаливого игнора
                await q.answer("Эта кнопка уже неактивна, выбери из текущих вариантов ⬇️", show_alert=False)
                return
            sess["last_options"] = []
            # фиксируем выбор прямо в сообщении с вопросом, кнопки убираем
            try:
                await q.edit_message_text(f"{q.message.text}\n\n✅ {choice}")
            except Exception:  # noqa: BLE001
                pass
            ss.push_history(sess, "user", choice)
            await _run_dialog_step(ctx, uid, sess, q.message)
            return

        if a == "payer" and b in ("ur", "fiz"):
            sess["payer"] = b
            sess["stage"] = ss.STAGE_DIALOG
            ss.push_history(
                sess, "user",
                f"Клиент выбрал категорию: Печать меню. Тип плательщика: "
                f"{'юрлицо/ИП' if b == 'ur' else 'физлицо'}. Начни диалог.",
            )
            thinking = await q.edit_message_text(
                "Принято! Секунду, вникаю в задачу… 🤔"
            )
            await _run_dialog_step(ctx, uid, sess, q.message, thinking_msg=thinking)
            return

    # ── Апсейл-подарок (только после подтверждённого заказа) ────────────────
    if ns == "gift":
        if a == "offer" and b in GIFT_SERVICE_LABELS:
            # Платная услуга — сначала цена и явное согласие, сбор данных
            # начинается только после «Да» (см. a == "agree" ниже).
            price = config.GIFT_PRICES.get(b)
            label = GIFT_SERVICE_LABELS[b]
            if not price:
                price_line = "цену назовёт дизайнер"
            elif b == "coloring_book":
                # раскраска — либо сказка (фикс-цена), либо по фото (цена
                # дизайнера) — итоговая цена зависит от выбора на следующем шаге
                price_line = f"от {price} ₽"
            else:
                price_line = f"{price} ₽"
            try:
                await q.edit_message_text(f"{q.message.text}\n\n👉 {label}")
            except Exception:  # noqa: BLE001
                pass
            await _send_plain(
                q.message,
                f"Стоимость услуги «{label}» — {price_line}, добавлю в счёт к "
                f"твоему заказу. Согласен(а) продолжить?",
                kbd.kb_gift_price_confirm(b),
            )
            return

        if a == "agree" and b in GIFT_SERVICE_LABELS:
            sess["stage"] = ss.STAGE_GIFT
            sess["gift_service_type"] = b
            sess["gift_step"] = 0
            sess["gift_data"] = {}
            sess["gift_coloring_mode"] = None
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001
                pass
            if b == "coloring_book":
                await _send_plain(
                    q.message,
                    "Отлично! Оригинальную сказку с ребёнком-героем сочиним, "
                    "или превратим ваше семейное фото в раскраску?",
                    kbd.kb_gift_coloring_mode(),
                )
            else:
                await _send_gift_step(q.message, sess)
            return

        if a == "skip":
            try:
                await q.edit_message_text(f"{q.message.text}\n\n✅ Не в этот раз")
            except Exception:  # noqa: BLE001
                pass
            return

        if a == "colormode" and b in ("story", "photo") and sess.get("stage") == ss.STAGE_GIFT:
            sess["gift_coloring_mode"] = b
            if b == "photo":
                price = config.GIFT_PRICES.get("photo_coloring")
                await _send_plain(
                    q.message,
                    f"Пришли, пожалуйста, семейное фото прямо в этот чат — "
                    f"дизайнер подготовит из него раскраску (один лист, цифровой "
                    f"дизайн) — от {price} ₽.\n\n"
                    f"Если захочешь ещё распечатать и заламинировать готовую "
                    f"раскраску — это уже отдельная услуга, стоимость обсудим "
                    f"отдельно с менеджером.",
                )
            else:
                await _send_gift_step(q.message, sess)
            return

        if a == "skipage" and sess.get("stage") == ss.STAGE_GIFT:
            fields = _gift_fields_for(sess)
            step = sess.get("gift_step", 0)
            if step < len(fields) and fields[step][0] == "age":
                # Fix #9: используем пустую строку вместо "не указан" для правильного типа
                sess["gift_data"]["age"] = ""
                sess["gift_step"] += 1
                await _send_gift_step(q.message, sess)
            return

        if a == "style" and b in GIFT_STYLE_LABELS and sess.get("stage") == ss.STAGE_GIFT:
            sess["gift_data"]["style"] = GIFT_STYLE_LABELS[b]
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001
                pass
            await _finalize_gift(ctx, uid, sess, q.message)
            return

        if a == "genre" and b in GIFT_GENRE_LABELS and sess.get("stage") == ss.STAGE_GIFT:
            sess["gift_data"]["style"] = GIFT_GENRE_LABELS[b]
            try:
                await q.edit_message_reply_markup(reply_markup=None)
            except Exception:  # noqa: BLE001
                pass
            await _finalize_gift(ctx, uid, sess, q.message)
            return


async def on_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Подтверждение номера. Анти-фрод: принимаем ТОЛЬКО собственный контакт
    отправителя — Telegram помечает его user_id, подделать нельзя."""
    uid = update.effective_user.id
    sess = ss.get_session(uid)
    msg = update.effective_message
    sess["business_connection_id"] = getattr(msg, "business_connection_id", None)
    contact = msg.contact

    if contact.user_id != uid:
        # Прислали чужой контакт из записной книжки — отклоняем.
        await msg.reply_text(
            "🚫 Это не твой номер — так не пойдёт. Нажми, пожалуйста, кнопку "
            "«📱 Отправить мой номер»: Telegram сам передаст номер владельца "
            "аккаунта. Это наша защита от мошенников.",
            reply_markup=kbd.kb_contact(),
        )
        return

    sess["phone"] = contact.phone_number
    name = " ".join(filter(None, [contact.first_name, contact.last_name]))
    sess["contact_name"] = name or update.effective_user.full_name
    sess["stage"] = ss.STAGE_FLOW

    await msg.reply_text(
        "✅ Номер получен и подтверждён.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await msg.reply_text(WELCOME, reply_markup=kbd.kb_flows())


async def _forward_attachment_to_admin(ctx: ContextTypes.DEFAULT_TYPE, user,
                                        att_type: str, file_id: str, caption: str) -> bool:
    """Сразу пересылаем образец/макет админу — не ждём финальной заявки."""
    if not config.ADMIN_ID:
        return False
    name = html.escape(user.full_name or "клиент")
    username = f"@{user.username}" if user.username else "нет username"
    head = (
        f"📎 <b>Файл от клиента</b>\n"
        f"👤 <a href=\"tg://user?id={user.id}\">{name}</a> ({username})"
        + (f"\n💬 {html.escape(caption)}" if caption else "")
    )
    try:
        if att_type == "photo":
            await ctx.bot.send_photo(
                chat_id=config.ADMIN_ID, photo=file_id,
                caption=head, parse_mode=ParseMode.HTML,
            )
        else:
            await ctx.bot.send_document(
                chat_id=config.ADMIN_ID, document=file_id,
                caption=head, parse_mode=ParseMode.HTML,
            )
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Не удалось переслать вложение админу: %s", e)
        return False


async def on_attachment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Клиент прислал фото или файл — обычно это образец/готовый макет."""
    uid = update.effective_user.id
    sess = ss.get_session(uid)
    msg = update.effective_message
    sess["business_connection_id"] = getattr(msg, "business_connection_id", None)

    # Скриншот подозрительного сообщения — самый естественный способ его
    # переслать. Текста в нём для нас нет, но и молчать нельзя.
    if await _fraud_guard(msg, sess, (msg.caption or "").strip(),
                          has_files=True):
        return

    if not sess["consent"]:
        await msg.reply_text(GREETING, reply_markup=kbd.kb_consent())
        return
    # Fix #2: проверяем не только наличие, но и непустоту номера
    if not sess.get("phone") or not sess["phone"].strip():
        await msg.reply_text(
            "Сначала подтверди номер — нажми кнопку «📱 Отправить мой номер» "
            "внизу экрана 🙌",
            reply_markup=kbd.kb_contact(),
        )
        return

    if msg.photo:
        att_type = "photo"
        file_id = msg.photo[-1].file_id  # самое крупное фото
    elif msg.document:
        att_type = "document"
        file_id = msg.document.file_id
    else:
        return

    caption = (msg.caption or "").strip()
    sess["attachments"].append({"type": att_type, "file_id": file_id, "caption": caption})
    delivered = await _forward_attachment_to_admin(ctx, update.effective_user, att_type, file_id, caption)

    # Апсейл «раскраска из семейного фото» — ручная работа дизайнера, без LLM.
    if (sess["stage"] == ss.STAGE_GIFT and sess.get("gift_service_type") == "coloring_book"
            and sess.get("gift_coloring_mode") == "photo"):
        price = config.GIFT_PRICES.get("photo_coloring")
        note = (
            f"✅ Фото получено, уже переслал дизайнеру! Цифровой дизайн одного "
            f"листа — от {price} ₽ (добавим в счёт заказа). Если захочешь ещё "
            f"печать и ламинацию готовой раскраски — это обсудим отдельно."
        )
        if not delivered:
            note += f"\n\nЕсли долго нет ответа, продублируй: {config.STUDIO['contact']}"
        await msg.reply_text(note, reply_markup=kbd.kb_flows())
        sess["stage"] = ss.STAGE_FLOW
        if config.ADMIN_ID:
            try:
                await ctx.bot.send_message(
                    chat_id=config.ADMIN_ID,
                    text=f"🎁📷 Заказ «Раскраска из семейного фото» (см. фото выше) "
                         f"— цифровой дизайн от {price} ₽. Если клиент захочет ещё "
                         f"печать+ламинацию — обсуди с ним стоимость отдельно.",
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("Не удалось отправить пометку по фото-раскраске: %s", e)
        return

    if sess["stage"] in (ss.STAGE_DIALOG, ss.STAGE_CONFIRM):
        if sess["stage"] == ss.STAGE_CONFIRM:
            sess["stage"] = ss.STAGE_DIALOG
        note = "[Клиент прислал фото/файл — вероятно образец/макет.]"
        if caption:
            note += f" Подпись клиента: {caption}"
        ss.push_history(sess, "user", note)
        sess["last_options"] = []
        try:
            await msg.chat.send_action(
                "typing", business_connection_id=getattr(msg, "business_connection_id", None)
            )
        except (TimedOut, NetworkError):
            pass
        await _run_dialog_step(ctx, uid, sess, msg)
        return

    # Файл пришёл до старта заказа (например, клиент сразу скинул образец)
    if delivered:
        text = "✅ Файл получен, уже переслал менеджеру! Чтобы оформить заказ, выбери направление:"
    else:
        text = "✅ Файл получен. Чтобы оформить заказ, выбери направление:"
    await msg.reply_text(text, reply_markup=kbd.kb_flows())


async def _forward_voice_to_admin(ctx: ContextTypes.DEFAULT_TYPE, user,
                                  file_id: str, note: str = "") -> bool:
    """Переслать голосовое Гульнаре. Делается ВСЕГДА и первым делом.

    Распознавание может не сработать по десятку причин — от кончившихся денег
    на ключе до сети. Ни одна из них не должна означать, что клиента не
    услышали: голос уходит человеку независимо от того, получился текст или
    нет.
    """
    if not config.ADMIN_ID:
        return False
    name = html.escape(user.full_name or "клиент")
    username = f"@{user.username}" if user.username else "нет username"
    head = (f"🎤 <b>Голосовое от клиента</b>\n"
            f"👤 <a href=\"tg://user?id={user.id}\">{name}</a> ({username})")
    if note:
        head += f"\n{html.escape(note)}"
    try:
        await ctx.bot.send_voice(chat_id=config.ADMIN_ID, voice=file_id,
                                 caption=head, parse_mode=ParseMode.HTML)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("Не удалось переслать голосовое админу: %s", e)
        return False


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Голосовое сообщение или кружок.

    До 10.08.2026 такие сообщения не ловил ни один обработчик: клиент
    наговаривал задачу и получал тишину. Порядок здесь выстроен так, чтобы
    тишины не было ни при каком исходе:

      1. Голос уходит Гульнаре — всегда, до всяких попыток распознать.
      2. Если распознавание выключено или запись длинная — честно говорим
         об этом и просим пару слов текстом.
      3. Если получилось — показываем расшифровку и ведём разговор дальше
         тем же путём, что и напечатанный текст.
    """
    uid = update.effective_user.id
    sess = ss.get_session(uid)
    msg = update.effective_message
    sess["business_connection_id"] = getattr(msg, "business_connection_id", None)

    media = msg.voice or msg.video_note or msg.audio
    if not media:
        return

    duration = getattr(media, "duration", None)
    size = getattr(media, "file_size", None)
    await _forward_voice_to_admin(ctx, update.effective_user, media.file_id,
                                  f"⏱ {duration} сек" if duration else "")

    async def give_up(reason: str) -> None:
        """Текста не будет — сказать об этом понятно и не бросить разговор."""
        await _send_plain(msg, reason)
        if sess.get("consent") and sess["stage"] in (ss.STAGE_DIALOG,
                                                     ss.STAGE_CONFIRM):
            return  # разговор уже идёт, клиент просто ответит текстом
        if not sess.get("consent"):
            await msg.reply_text(GREETING, reply_markup=kbd.kb_consent())

    if not speech.enabled():
        await give_up(speech.CANT_HEAR)
        return
    if speech.too_long(duration, size):
        await give_up(speech.TOO_LONG)
        return

    try:
        await msg.chat.send_action(
            "typing",
            business_connection_id=getattr(msg, "business_connection_id", None),
        )
    except (TimedOut, NetworkError):
        pass  # «печатает…» — косметика

    try:
        tg_file = await media.get_file()
        audio = bytes(await tg_file.download_as_bytearray())
    except Exception as e:  # noqa: BLE001
        logger.error("Не скачалось голосовое: %s: %s", type(e).__name__, e)
        await give_up(speech.CANT_HEAR)
        return

    # Распознавание синхронное и ходит в сеть — в отдельном потоке, иначе на
    # эти секунды встал бы весь бот и остальные клиенты ждали бы молча.
    text, why = await asyncio.to_thread(speech.recognize, audio)
    if why or not text:
        if why:
            logger.info("Голосовое не распознано: %s", why)
        await give_up(speech.CANT_HEAR)
        return

    # Показываем расшифровку до того, как пустить её в работу: распознавание
    # ошибается на именах и числах, а число здесь — это тираж, то есть деньги.
    await _send_plain(msg, speech.heard(text))
    await on_text(update, ctx, text_override=text)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                  text_override: str = None):
    """Свободный текст клиента — топливо для Dialog Manager.

    `text_override` подставляет расшифровку голосового: у такого сообщения
    `msg.text` пустой, а дальше по коду всё одинаково. Так голосовое проходит
    ровно тот же путь, что и напечатанное, включая проверку на мошенников.
    """
    uid = update.effective_user.id
    sess = ss.get_session(uid)
    msg = update.effective_message
    sess["business_connection_id"] = getattr(msg, "business_connection_id", None)
    text = text_override if text_override is not None else (msg.text or "").strip()

    # Проверка на мошенников идёт до всех остальных проверок — см. _fraud_guard.
    if await _fraud_guard(msg, sess, text):
        return

    # Пока не пройдены согласие и подтверждение номера — в диалог не пускаем.
    if not sess["consent"]:
        if ss.consent_given(text):
            # Согласие словом, а не кнопкой. 10.08.2026 выяснилось, что
            # человек, отвечающий текстом, ходил по кругу: любое сообщение
            # до согласия возвращало то же приветствие, и выхода не было.
            sess["consent"] = True
            sess["stage"] = ss.STAGE_PHONE
            await msg.reply_text(ASK_PHONE, reply_markup=kbd.kb_contact())
        elif sess.get("greeted"):
            await msg.reply_text(CONSENT_HINT, reply_markup=kbd.kb_consent())
        else:
            sess["greeted"] = True
            await msg.reply_text(GREETING, reply_markup=kbd.kb_consent())
        return
    # Fix #2: проверяем не только наличие, но и непустоту номера
    if not sess.get("phone") or not sess["phone"].strip():
        await msg.reply_text(
            "Сначала подтверди номер — нажми кнопку «📱 Отправить мой номер» "
            "внизу экрана 🙌",
            reply_markup=kbd.kb_contact(),
        )
        return

    if sess["stage"] == ss.STAGE_GIFT:
        if (sess.get("gift_service_type") == "coloring_book"
                and sess.get("gift_coloring_mode") == "photo"):
            # Ждём именно фото — реагировать на текст нечем, просто напомнить.
            await msg.reply_text("Жду именно фото 🙂 Пришли его прямо в этот чат.")
            return
        # Апсейл-подарок: свободные ответы (имя/возраст/кем приходится/факты).
        # _send_gift_step вызывается ВСЕГДА — если клиент написал текст на
        # шаге выбора стиля/жанра (кнопками), просто повторяем вопрос, а не молчим.
        fields = _gift_fields_for(sess)
        step = sess["gift_step"]
        if step < len(fields):
            field_key, _q = fields[step]
            sess["gift_data"][field_key] = text
            sess["gift_step"] += 1
        await _send_gift_step(msg, sess)
        return

    if sess["stage"] in (ss.STAGE_DIALOG, ss.STAGE_CONFIRM):
        # На стадии подтверждения текст = клиент хочет что-то дополнить
        if sess["stage"] == ss.STAGE_CONFIRM:
            sess["stage"] = ss.STAGE_DIALOG
        ss.push_history(sess, "user", text)
        sess["last_options"] = []  # клиент ответил текстом — старые кнопки неактуальны
        try:
            await msg.chat.send_action(
                "typing", business_connection_id=getattr(msg, "business_connection_id", None)
            )
        except (TimedOut, NetworkError):
            pass  # «печатает…» — косметика, не роняем обработку из-за неё
        await _run_dialog_step(ctx, uid, sess, msg)
        return

    # Клиент пишет текстом до выбора направления — не отфутболиваем в /start,
    # а мягко направляем в каскад (умный секретарь, а не автоответчик).
    await msg.reply_text(
        "Понял тебя! Чтобы я сразу включил нужного эксперта, выбери направление:",
        reply_markup=kbd.kb_flows(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        sys.exit(1)
    if not config.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY не найден в .env")
        sys.exit(1)

    # Щедрые сетевые лимиты: дефолтные 5 секунд слишком строги для облачного
    # хостинга — при заминке сети получаем telegram.error.TimedOut.
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(20)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(20)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(BusinessConnectionHandler(on_business_connection))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.CONTACT, on_contact))
    # Голосовые — до общего обработчика вложений: голосовое это не «файл»,
    # у него свой путь через распознавание.
    app.add_handler(MessageHandler(
        filters.VOICE | filters.VIDEO_NOTE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, on_attachment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    # Второй транспорт: тот же Джарвис отвечает во ВКонтакте. Запускаем до
    # Telegram и под try/except — ВК не должен мешать основному каналу ни
    # падением, ни отсутствием настроек.
    try:
        vk_started = vk_jarvis.start()
    except Exception as e:  # noqa: BLE001
        logger.error("ВК-Джарвис не запустился: %s: %s", type(e).__name__, e)
        vk_started = False

    print("\n" + "=" * 60)
    print("🚀 ДЖАРВИС 2.0 (думающая архитектура) ЗАПУЩЕН!")
    print("🔵 ВКонтакте: " + ("слушает сообщения сообщества"
                              if vk_started else "выключен"))
    print("=" * 60)
    print("\n📱 Бот: @GranatJarvis_bot   Команда: /start")
    if not config.ADMIN_ID:
        print("⚠️  ADMIN_ID не задан в .env — заявки НЕ будут падать админу!")
    print("=" * 60 + "\n")

    # allowed_updates=ALL_TYPES — иначе апдейты business_connection/business_message
    # (нужны для работы Джарвиса через личный аккаунт, Telegram Business) могут не долетать.
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
