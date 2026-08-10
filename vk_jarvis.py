# -*- coding: utf-8 -*-
"""
Джарвис во ВКонтакте — второй транспорт для того же диалога.

ЗАЧЕМ. 09.08.2026 Telegram в России перестал открываться, и весь путь
«заявка → сбор ТЗ» встал: клиенту некуда было идти. ВКонтакте работает без
обхода блокировок, и клиенты у студии там уже есть. Один упавший мессенджер
больше не должен останавливать приём заказов.

ЧТО ЗДЕСЬ ЕСТЬ, А ЧЕГО НЕТ.
  Есть: согласие, выбор направления и категории, умный диалог, сводка,
        подтверждение, доставка готового ТЗ Гульнаре.
  Нет:  подтверждения номера телефона — во ВКонтакте нет кнопки «поделиться
        номером», подделать её нельзя, а требовать номер текстом бессмысленно:
        любой может написать любой. Вместо этого в заявку кладём ссылку на
        страницу клиента — по ней Гульнара отвечает прямо в ВК.
  Нет:  апсейл-подарков. Сначала пусть заработает главное.

УСТРОЙСТВО. Крутится в отдельном потоке того же приложения jarvis-bot,
рядом с Telegram-ботом. Движок диалога общий — dialog_manager, тот самый,
что задаёт вопросы в Telegram. Поэтому вопросы, расчёт и формат ТЗ
совпадают, и правка в промпте меняет оба канала сразу.

Падение этого модуля не должно ронять Telegram: поток запускается под
try/except, а внутри цикл сам поднимается после любой ошибки.

── ПЕРЕМЕННЫЕ ПРИЛОЖЕНИЯ jarvis-bot ────────────────────────────────────
    VK_TOKEN     — ключ сообщества с правом «сообщения сообщества».
    VK_GROUP_ID  — числовой id сообщества (для granat-kmv это 238836731).
    VK_PEER_ID   — куда слать готовое ТЗ: id страницы Гульнары.

Без VK_TOKEN модуль молча не запускается, и бот работает как раньше.
────────────────────────────────────────────────────────────────────────
"""

import json
import logging
import os
import threading
import time

import requests

import config
import dialog_manager
try:
    import fraud_check
except Exception:  # noqa: BLE001
    fraud_check = None
try:
    import speech
except Exception:  # noqa: BLE001
    speech = None
try:
    import prices
except Exception:  # noqa: BLE001
    prices = None
import knowledge_base as kb
import session as ss

logger = logging.getLogger("vk-jarvis")

API = "https://api.vk.com/method/"
API_VERSION = "5.199"

VK_TOKEN = os.getenv("VK_TOKEN", "").strip()
VK_GROUP_ID = os.getenv("VK_GROUP_ID", "238836731").strip()
VK_ADMIN_PEER = os.getenv("VK_PEER_ID", "").strip()

# Долгий опрос: держим соединение открытым 25 секунд и ждём событие. Это
# не «раз в 25 секунд» — ответ приходит сразу, как только клиент написал.
WAIT = 25
TIMEOUT = WAIT + 10

# ВК режет сообщения длиннее 4096 символов. Режем сами: обрезанное ТЗ
# полезнее ошибки и потерянной заявки.
MAX_LEN = 4000

# Ограничения клавиатуры ВК: не больше десяти рядов и пяти кнопок в ряду.
MAX_ROWS = 10
MAX_IN_ROW = 5

GREETING = (
    "Здравствуйте! Я Джарвис — цифровой ассистент студии «Гранат» "
    "(г. Лермонтов, работаем по всему КМВ).\n\n"
    "Помогу оформить заказ на печать или IT-разработку и составлю "
    "техническое задание.\n\n"
    # Раньше здесь было «понадобится ваше имя и то, как с вами связаться».
    # Во ВКонтакте бот имя не спрашивает — берёт его из профиля вместе со
    # ссылкой на страницу, так надёжнее. А обещание сбивало: 10.08.2026
    # человек прочитал его как просьбу и написал имя вместо согласия.
    "Расскажите, что нужно напечатать, — остальное спрошу по ходу. "
    "Продолжая, вы даёте согласие на обработку данных заказа: они нужны "
    "только менеджеру студии для связи по нему."
)

CONSENT_BUTTON = "Согласен, продолжим"

# Что говорим, если человек ответил текстом, а не кнопкой. Коротко и без
# повтора приветствия: длинный текст второй раз подряд читать не будут.
CONSENT_HINT = (
    "Имя и задачу спрошу дальше — сейчас нужно только ваше согласие "
    "на обработку данных.\n\n"
    "Нажмите кнопку «Согласен, продолжим» внизу экрана — или просто "
    "напишите «да»."
)
CONFIRM_BUTTON = "Всё верно, оформляем"
AMEND_BUTTON = "Хочу дополнить"
RESTART_BUTTON = "Начать заново"


# ── Обращения к ВК ──────────────────────────────────────────────────────

def api(method: str, **params):
    """Вызов метода ВК. Возвращает response или None. Наружу не падает."""
    if not VK_TOKEN:
        return None
    params.setdefault("access_token", VK_TOKEN)
    params.setdefault("v", API_VERSION)
    try:
        r = requests.post(API + method, data=params, timeout=30).json()
    except Exception as e:  # noqa: BLE001
        logger.warning("%s: сеть: %s: %s", method, type(e).__name__, e)
        return None
    if "error" in r:
        # ВК отвечает HTTP 200 даже на отказ — причина лежит в теле.
        err = r["error"]
        logger.warning("%s: отказ %s %s", method,
                       err.get("error_code"), err.get("error_msg"))
        return None
    return r.get("response")


def keyboard(rows):
    """Клавиатура ВК из списка списков подписей. Пустой список — убрать кнопки.

    ВК не разрешает подписи длиннее 40 символов, а варианты от LLM бывают
    длиннее — режем, иначе сообщение не уйдёт вовсе.
    """
    labels = [str(label)[:40] for row in rows if row for label in row]

    # ВК не принимает больше десяти рядов: сообщение просто не уходит с
    # ошибкой 911. Категорий в типографии двенадцать, поэтому при переполнении
    # раскладываем по двое в ряд, а не режем список — иначе часть услуг
    # молча исчезнет из меню, и клиент их никогда не увидит.
    per_row = 1
    while len(labels) > per_row * MAX_ROWS and per_row < MAX_IN_ROW:
        per_row += 1
    packed = [labels[i:i + per_row] for i in range(0, len(labels), per_row)]
    if len(packed) > MAX_ROWS:
        logger.warning("кнопок больше, чем влезает: %s", len(labels))
        packed = packed[:MAX_ROWS]

    buttons = [
        [
            {
                "action": {"type": "text", "label": label},
                "color": "primary",
            }
            for label in row
        ]
        for row in packed
    ]
    return json.dumps({"one_time": False, "inline": False, "buttons": buttons},
                      ensure_ascii=False)


def send(peer_id, text: str, rows=None, attachment=None):
    """Сообщение клиенту. random_id обязателен: по нему ВК отбрасывает дубли."""
    params = {
        "peer_id": peer_id,
        "message": text[:MAX_LEN],
        "random_id": int(time.time() * 1000) % 2_000_000_000,
    }
    if rows is not None:
        params["keyboard"] = keyboard(rows)
    if attachment:
        params["attachment"] = ",".join(attachment)
    return api("messages.send", **params)


def stamp() -> str:
    """Московское время для заявки. Студия и клиенты в одном поясе."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y, %H:%M")


def user_card(from_id) -> str:
    """Имя и ссылка на страницу клиента — по ним Гульнара отвечает в ВК.

    Телефон во ВКонтакте не спрашиваем: подтвердить его там нечем, а
    непроверенный номер в заявке хуже, чем честная ссылка на страницу.
    """
    link = f"vk.com/id{from_id}"
    got = api("users.get", user_ids=from_id)
    if got:
        u = got[0]
        name = " ".join(filter(None, [u.get("first_name"), u.get("last_name")]))
        if name:
            return f"{name} ({link})"
    return link


# ── Разговор ────────────────────────────────────────────────────────────

def attachment_ids(msg: dict) -> list:
    """Вложения сообщения в виде «photo-123_456» — так их принимает ВК обратно.

    Нужны, чтобы переслать образец Гульнаре как вложение, а не описанием.
    access_key появляется у файлов из закрытых источников; без него ВК
    вложение не отдаст.
    """
    out = []
    for att in msg.get("attachments") or []:
        kind = att.get("type")
        obj = att.get(kind) or {}
        owner, oid = obj.get("owner_id"), obj.get("id")
        if not kind or owner is None or oid is None:
            continue
        item = f"{kind}{owner}_{oid}"
        if obj.get("access_key"):
            item += f"_{obj['access_key']}"
        out.append(item)
    return out


def voice_from(msg: dict):
    """Голосовое из сообщения ВК, если оно там есть.

    ВКонтакте часто расшифровывает голосовые сам и кладёт текст в
    `transcript` — это бесплатно и уже готово, грех не воспользоваться.
    Когда своей расшифровки нет, отдаём ссылку на ogg: формат ровно тот,
    что принимает SpeechKit, перекодировать не нужно.
    """
    for att in msg.get("attachments") or []:
        if att.get("type") != "audio_message":
            continue
        obj = att.get("audio_message") or {}
        ready = obj.get("transcript_state") == "done"
        return {
            "transcript": (obj.get("transcript") or "").strip() if ready else "",
            "url": obj.get("link_ogg") or "",
            "duration": obj.get("duration") or 0,
        }
    return None


def fetch_audio(url: str):
    """Скачать голосовое. Возвращает (байты, причина_отказа).

    Размер режем на лету: чужая ссылка не должна утянуть в память сколько
    угодно, а всё, что больше лимита быстрого распознавания, всё равно не
    пригодится.
    """
    if not url:
        return b"", "нет ссылки"
    try:
        with requests.get(url, timeout=20, stream=True) as r:
            if r.status_code != 200:
                return b"", f"файл не отдался ({r.status_code})"
            out = bytearray()
            for chunk in r.iter_content(64 * 1024):
                out += chunk
                if len(out) > speech.MAX_BYTES:
                    return b"", "запись длиннее 30 секунд"
            return bytes(out), ""
    except Exception as e:  # noqa: BLE001
        logger.warning("голосовое не скачалось: %s: %s", type(e).__name__, e)
        return b"", "сеть"


def handle_voice(peer_id, from_id, voice: dict, attachments) -> bool:
    """Голосовое клиента. True — разобрались, дальше идти не нужно.

    Порядок тот же, что в Telegram, и по той же причине: сначала голос
    уходит Гульнаре, и только потом мы пробуем его расшифровать. Что бы ни
    случилось с распознаванием, клиента услышали.
    """
    if VK_ADMIN_PEER:
        send(VK_ADMIN_PEER,
             f"🎤 Голосовое от клиента {user_card(from_id)}"
             + (f"\n⏱ {voice['duration']} сек" if voice.get("duration") else ""),
             attachment=attachments)

    text = voice.get("transcript") or ""
    if not text:
        if speech is None or not speech.enabled():
            send(peer_id, speech.CANT_HEAR if speech else
                 "Голосовое передал Гульнаре. Напишите, пожалуйста, коротко: "
                 "что нужно и в каком количестве?")
            return True
        if speech.too_long(voice.get("duration")):
            send(peer_id, speech.TOO_LONG)
            return True
        audio, why = fetch_audio(voice.get("url"))
        if why:
            send(peer_id, speech.CANT_HEAR)
            return True
        text, why = speech.recognize(audio)
        if why or not text:
            send(peer_id, speech.CANT_HEAR)
            return True

    # Расшифровку показываем до того, как пустить в работу: ошибка в числе —
    # это ошибка в тираже, то есть в деньгах.
    send(peer_id, speech.heard(text) if speech else f"📝 Я услышал: «{text}»")
    handle(peer_id, from_id, text)
    return True


def skey(peer_id) -> str:
    """Ключ сессии. С префиксом, чтобы id страницы ВК не столкнулся с
    Telegram-id: хранилище сессий у обоих транспортов общее."""
    return f"vk:{peer_id}"


def flows_rows():
    return [[data["title"][:40]] for data in kb.FLOWS.values()]


def match_flow(text: str):
    """Какое направление выбрал клиент. Сверяем по подписи кнопки."""
    for code, data in kb.FLOWS.items():
        if data["title"][:40].lower() == text.lower():
            return code
    return None


def categories_rows(flow: str):
    return [[title[:40]] for _code, title in kb.FLOWS[flow]["categories"]]


def match_category(flow: str, text: str):
    for code, title in kb.FLOWS[flow]["categories"]:
        if title[:40].lower() == text.lower():
            return code
    return None


def start_over(peer_id, sess):
    """Вернуть клиента к выбору направления, сохранив согласие."""
    sess["stage"] = ss.STAGE_FLOW
    sess["flow"] = None
    sess["category"] = None
    sess["payer"] = None
    sess["history"].clear()
    sess["order_spec"].clear()
    sess["final_brief"] = None
    send(peer_id, "С чего начнём?", flows_rows())


def run_dialog_step(peer_id, sess):
    """Один шаг умного диалога: LLM → ответ клиенту с кнопками-вариантами."""
    try:
        result = dialog_manager.process(sess)
    except Exception as e:  # noqa: BLE001
        logger.error("LLM: %s: %s", type(e).__name__, e)
        send(peer_id,
             "Не получилось связаться с мозговым центром. Напишите ещё раз "
             f"через минуту или свяжитесь напрямую: {config.STUDIO['phone']}")
        return

    collected = result.get("collected") or {}
    if isinstance(collected, dict):
        sess["order_spec"].update(collected)
    if result.get("quote"):
        sess["last_quote"] = result["quote"]
    if result.get("brief"):
        sess["final_brief"] = result["brief"]

    ready = result.get("status") == "ready"
    sess["stage"] = ss.STAGE_CONFIRM if ready else ss.STAGE_DIALOG
    ss.push_history(sess, "assistant", result["message"])

    if ready:
        sess["last_options"] = []
        rows = [[CONFIRM_BUTTON], [AMEND_BUTTON]]
    else:
        sess["last_options"] = result.get("options") or []
        rows = [[o] for o in sess["last_options"]] or []
        rows.append([RESTART_BUTTON])

    send(peer_id, result["message"], rows)


def hand_over(peer_id, sess, from_id):
    """ТЗ собрано и подтверждено — отдаём его Гульнаре."""
    spec = dict(sess.get("order_spec") or {})
    channel = spec.pop(dialog_manager.CHANNEL_FIELD, "") or "ВКонтакте"
    lines = [
        "🔥 ГОРЯЧАЯ ЗАЯВКА ИЗ ВКОНТАКТЕ",
        # Дата и время: без них по письму не понять, свежая заявка или
        # позавчерашняя, а для срочных это решает, успеваем мы или нет.
        f"🕒 {stamp()} (мск)",
        "",
        f"👤 Клиент: {user_card(from_id)}",
        f"💬 Писать клиенту в: {channel}",
        "",
        "ТЗ:",
        sess.get("final_brief") or "— (см. параметры ниже)",
        "",
        "Параметры:",
    ]
    lines += [f"  • {k}: {v}" for k, v in spec.items()] or ["  —"]
    text = "\n".join(lines)

    delivered = False
    if VK_ADMIN_PEER:
        delivered = bool(send(VK_ADMIN_PEER, text))
    # Дубль в Telegram — если он в этот момент жив. Два независимых канала:
    # ровно из-за их отсутствия сегодня и потеряли полдня.
    if config.TELEGRAM_BOT_TOKEN and config.ADMIN_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": config.ADMIN_ID, "text": text},
                timeout=15,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("дубль заявки в Telegram не ушёл: %s", e)

    s = config.STUDIO
    if delivered:
        answer = (
            "✅ Заявка оформлена и уже у менеджера!\n\n"
            "Менеджер рассчитает точную стоимость и свяжется с вами здесь же. "
            f"{config.PAYMENT_TERMS}\n\n"
            f"Если срочно: {s['phone']}\n📍 {s['address']} ({s['hours']})"
        )
    else:
        answer = (
            "✅ Заявка записана, но уведомление менеджеру не прошло.\n"
            f"Продублируйте, пожалуйста, напрямую: {s['phone']}"
        )
    send(peer_id, answer, [])
    ss.reset_session(skey(peer_id))


# ── Проверка на мошенников ──────────────────────────────────────────────

FRAUD_ROWS = [["Меня обманули, что делать"], ["Меню"]]

FRAUD_NO_FILES = (
    "Я читаю только текст — картинку разобрать не могу.\n\n"
    "Перешлите сообщение текстом или перескажите своими словами: что "
    "пишут, чего просят, есть ли ссылка."
)


def fraud_guard(peer_id, sess, text: str, has_files: bool) -> bool:
    """Разбор мошеннических сообщений. True — ответили, дальше не идём.

    Стоит ПЕРЕД согласием и меню сознательно: человек, которому прямо
    сейчас звонит «служба безопасности», не должен сначала соглашаться на
    обработку данных и выбирать направление печати. Персональные данные
    здесь и не собираются — текст разбирается на месте и никуда не уходит.
    """
    if fraud_check is None:
        return False

    if sess.get("fraud_mode"):
        if has_files and not text:
            send(peer_id, FRAUD_NO_FILES, FRAUD_ROWS)
            return True
        if fraud_check.wants_exit(text):
            sess["fraud_mode"] = False
            send(peer_id, fraud_check.EXIT_MESSAGE,
                 flows_rows() if sess.get("consent") else [[CONSENT_BUTTON]])
            return True
        send(peer_id, fraud_check.answer(text), FRAUD_ROWS)
        return True

    action = fraud_check.triage(text)

    if action == "stolen":
        sess["fraud_mode"] = True
        send(peer_id, fraud_check.STOLEN, FRAUD_ROWS)
    elif action == "enter":
        sess["fraud_mode"] = True
        send(peer_id, fraud_check.ENTER_MESSAGE, FRAUD_ROWS)
    elif action == "report":
        sess["fraud_mode"] = True
        send(peer_id, fraud_check.answer(text), FRAUD_ROWS)
    elif action == "alarm":
        # Человек переслал сообщение, ни о чём не прося, — а в нём набор
        # классических приёмов. Молчать нельзя. Режим при этом НЕ включаем:
        # настоящий клиент должен продолжить оформлять заказ, а не застрять
        # в проверке из-за неудачной формулировки.
        send(peer_id,
             "⚠️ Стоп. Это не похоже на заказ — это похоже на обман.\n\n"
             + fraud_check.report(text)
             + "\n\nЕсли вы всё-таки по заказу — напишите «меню».",
             FRAUD_ROWS)
    else:
        return False
    return True


def handle(peer_id, from_id, text: str, attachments=None, voice=None):
    """Одно входящее сообщение клиента."""
    text = (text or "").strip()
    attachments = attachments or []
    if not text and not attachments:
        return

    sess = ss.get_session(skey(peer_id))
    stage = sess.get("stage")

    # Голосовое разбираем раньше общей ветки вложений: это не «файл-образец»,
    # а сказанные слова, и путь у них свой.
    if voice and handle_voice(peer_id, from_id, voice, attachments):
        return

    if fraud_guard(peer_id, sess, text, bool(attachments)):
        return

    # Образец или готовый макет. Джарвис сам просит прислать фото — значит
    # обязан на него отреагировать: молчание в ответ на присланный файл
    # выглядит как поломка. Пересылаем Гульнаре сразу, не дожидаясь конца
    # разговора: по образцу она часто отвечает быстрее, чем по ТЗ.
    if attachments:
        sess.setdefault("attachments", []).extend(attachments)
        if VK_ADMIN_PEER:
            send(VK_ADMIN_PEER,
                 f"📎 Файл от клиента {user_card(from_id)}"
                 + (f"\n💬 {text}" if text else ""),
                 attachment=attachments)
        note = "[Клиент прислал фото/файл — вероятно образец/макет.]"
        if text:
            note += f" Подпись клиента: {text}"
        if sess.get("consent") and stage in (ss.STAGE_DIALOG, ss.STAGE_CONFIRM):
            sess["stage"] = ss.STAGE_DIALOG
            ss.push_history(sess, "user", note)
            sess["last_options"] = []
            run_dialog_step(peer_id, sess)
        else:
            send(peer_id, "Файл получил, передал Гульнаре 👍")
        return

    # «Начать заново» работает на любом шаге: клиент не должен искать выход.
    if text.lower() == RESTART_BUTTON.lower():
        start_over(peer_id, sess)
        return

    if not sess.get("consent"):
        if text.lower() == CONSENT_BUTTON.lower() or ss.consent_given(text):
            sess["consent"] = True
            # Человек пришёл не с пустыми руками: первым сообщением он уже
            # сказал, что ему нужно. Заставлять его повторяться после
            # согласия — верный способ потерять клиента на ровном месте.
            asked = sess.pop("first_words", "")
            if asked:
                handle(peer_id, from_id, asked)
            else:
                start_over(peer_id, sess)
        elif sess.get("greeted"):
            # Второй раз одно и то же приветствие не шлём. 10.08.2026 клиент
            # так и ходил по кругу: написал задачу — приветствие, написал имя
            # — снова приветствие. Он не понимал, чего от него хотят, потому
            # что в приветствии сказано «понадобится ваше имя», и выглядит
            # это как просьба имя написать.
            send(peer_id, CONSENT_HINT, [[CONSENT_BUTTON]])
        else:
            sess["greeted"] = True
            # Запоминаем ровно одну фразу — ту, с которой человек пришёл.
            sess.setdefault("first_words", text)
            send(peer_id, GREETING, [[CONSENT_BUTTON]])
        return

    if stage in (ss.STAGE_CONSENT, ss.STAGE_PHONE, ss.STAGE_FLOW):
        flow = match_flow(text)
        if not flow:
            # Клиент написал словами, а не нажал кнопку. Раньше он получал в
            # ответ то же меню — и на второй раз уходил. В прайсе лежит
            # распознавание услуги по словам: «заламинировать», «чертёж»,
            # «фото на паспорт». Если узнали — сразу в разговор, с его же
            # фразой, а не заставляем искать нужную кнопку.
            guess = prices.detect(text) if prices else ""
            if guess:
                sess["category"] = guess
                sess["stage"] = ss.STAGE_DIALOG
                sess["history"].clear()
                sess["order_spec"].clear()
                ss.push_history(sess, "user", text)
                send(peer_id, "Секунду, вникаю в задачу…")
                run_dialog_step(peer_id, sess)
                return
            send(peer_id, "Не понял задачу. Выберите направление:", flows_rows())
            return
        sess["flow"] = flow
        sess["stage"] = ss.STAGE_CAT
        send(peer_id, f"{kb.FLOWS[flow]['title']} — выберите категорию:",
             categories_rows(flow))
        return

    if stage == ss.STAGE_CAT:
        cat = match_category(sess["flow"], text)
        if not cat:
            guess = prices.detect(text) if prices else ""
            if guess:
                sess["category"] = guess
                sess["stage"] = ss.STAGE_DIALOG
                sess["history"].clear()
                sess["order_spec"].clear()
                ss.push_history(sess, "user", text)
                send(peer_id, "Секунду, вникаю в задачу…")
                run_dialog_step(peer_id, sess)
                return
            send(peer_id, "Выберите категорию из списка:",
                 categories_rows(sess["flow"]))
            return
        sess["category"] = cat
        sess["history"].clear()
        sess["order_spec"].clear()

        # Спец-ветка «Меню»: сначала юрлицо или физлицо — как в Telegram.
        if cat == "menu":
            sess["stage"] = ss.STAGE_PAYER
            send(peer_id,
                 "Оформляем заказ на физическое лицо или от организации "
                 "(Юрлицо/ИП) с закрывающими документами?",
                 [["Организация (Юрлицо/ИП)"], ["Физлицо (частный заказ)"]])
            return

        sess["stage"] = ss.STAGE_DIALOG
        title = kb.category_title(sess["flow"], cat)
        ss.push_history(sess, "user",
                        f"Клиент выбрал категорию: {title}. Начни диалог.")
        send(peer_id, f"{title} — секунду, вникаю в задачу…")
        run_dialog_step(peer_id, sess)
        return

    if stage == ss.STAGE_PAYER:
        low = text.lower()
        payer = "ur" if "органи" in low or "юр" in low else (
            "fiz" if "физ" in low else None)
        if not payer:
            send(peer_id, "Выберите одно из двух:",
                 [["Организация (Юрлицо/ИП)"], ["Физлицо (частный заказ)"]])
            return
        sess["payer"] = payer
        sess["stage"] = ss.STAGE_DIALOG
        ss.push_history(
            sess, "user",
            "Клиент выбрал категорию: Печать меню. Тип плательщика: "
            f"{'юрлицо/ИП' if payer == 'ur' else 'физлицо'}. Начни диалог.",
        )
        send(peer_id, "Принято! Секунду, вникаю в задачу…")
        run_dialog_step(peer_id, sess)
        return

    if stage == ss.STAGE_CONFIRM:
        if text.lower() == CONFIRM_BUTTON.lower():
            hand_over(peer_id, sess, from_id)
            return
        # Любой другой ответ — клиент хочет что-то поправить. Возвращаемся
        # в диалог и передаём его слова движку как есть.
        sess["stage"] = ss.STAGE_DIALOG
        if text.lower() != AMEND_BUTTON.lower():
            ss.push_history(sess, "user", text)
            run_dialog_step(peer_id, sess)
        else:
            send(peer_id, "Хорошо! Напишите, что изменить или добавить.", [])
        return

    # STAGE_DIALOG и всё остальное — свободный текст в движок.
    sess["stage"] = ss.STAGE_DIALOG
    ss.push_history(sess, "user", text)
    sess["last_options"] = []
    run_dialog_step(peer_id, sess)


# ── Долгий опрос ────────────────────────────────────────────────────────

def poll_once(state):
    """Один цикл ожидания событий. Возвращает обновлённое состояние опроса."""
    if not state:
        got = api("groups.getLongPollServer", group_id=VK_GROUP_ID)
        if not got:
            return None
        state = got

    try:
        r = requests.get(
            state["server"],
            params={"act": "a_check", "key": state["key"],
                    "ts": state["ts"], "wait": WAIT},
            timeout=TIMEOUT,
        ).json()
    except Exception as e:  # noqa: BLE001
        logger.warning("опрос: %s: %s", type(e).__name__, e)
        return state

    # failed=1 — устарел ts, 2/3 — протух ключ: перезапрашиваем сервер.
    if "failed" in r:
        if r["failed"] == 1 and "ts" in r:
            state["ts"] = r["ts"]
            return state
        return None

    state["ts"] = r.get("ts", state["ts"])
    for event in r.get("updates", []):
        if event.get("type") != "message_new":
            continue
        msg = (event.get("object") or {}).get("message") or {}
        peer_id = msg.get("peer_id")
        from_id = msg.get("from_id")
        # Сообщения самого сообщества игнорируем, иначе бот заговорит сам
        # с собой: его собственные реплики тоже приходят событиями.
        if not peer_id or not from_id or from_id < 0:
            continue
        try:
            handle(peer_id, from_id, msg.get("text", ""), attachment_ids(msg),
                   voice_from(msg))
        except Exception as e:  # noqa: BLE001
            logger.exception("разговор с %s оборвался: %s", peer_id, e)
            send(peer_id,
                 "Что-то пошло не так на моей стороне. Напишите ещё раз, "
                 "пожалуйста — или сразу Гульнаре: "
                 f"{config.STUDIO['phone']}")
    return state


def run():
    """Вечный цикл. Любая ошибка — пауза и заход заново, без остановки."""
    logger.info("ВК-Джарвис слушает сообщения сообщества %s", VK_GROUP_ID)
    state = None
    while True:
        try:
            state = poll_once(state)
        except Exception as e:  # noqa: BLE001
            logger.exception("цикл опроса упал: %s", e)
            state = None
        if state is None:
            # Не долбим ВК в лоб: если ключ не выдают, пауза перед заходом.
            time.sleep(5)


def start():
    """Поднять ВК-Джарвиса в фоне. Возвращает True, если запустился.

    Отдельный поток и демон: падение ВК-части не должно ронять Telegram —
    сегодня один недоступный мессенджер уже остановил всю цепочку, второй
    раз наступать на это нельзя.
    """
    if not VK_TOKEN:
        logger.info("VK_TOKEN не задан — ВК-Джарвис не запускается")
        return False
    if not VK_ADMIN_PEER:
        logger.warning("VK_PEER_ID не задан — заявки из ВК будет некуда слать")
    threading.Thread(target=run, name="vk-jarvis", daemon=True).start()
    return True
