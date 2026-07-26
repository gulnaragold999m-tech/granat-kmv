# -*- coding: utf-8 -*-
"""
Два бота, два токена, две зоны ответственности.

  ГЕНЕРАЛ  (ADMIN_BOT_TOKEN)   — говорит только с Гульнарой: лиды, чеки
                                 калькулятора, эскалации «клиент не пришёл».
  ДЖАРВИС  (JARVIS_BOT_TOKEN)  — говорит только с клиентом: бриф, расчёт, ТЗ.

Зачем разделять. Если бы клиенту писал тот же бот, что и админу, любой лид
видел бы служебные сообщения, а любая ошибка адресата отправляла бы клиенту
внутренние цифры. Разные токены делают такую утечку невозможной физически.

Ограничение платформы, которое определяет всю схему: бот НЕ МОЖЕТ написать
пользователю, который сам не начинал с ним диалог. Поэтому Джарвис пишет
первым только тем, чей chat_id у нас уже есть с прошлого разговора. Всем
остальным сайт отдаёт ссылку-приглашение, и первый шаг делает клиент.
"""

import os
import socket

import requests

# На Amvera исходящий IPv6 не проходит — принудительно IPv4, иначе requests
# может выбрать IPv6-адрес api.telegram.org и упасть на «Network unreachable».
try:
    import urllib3.util.connection as urllib3_cn

    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception as e:  # pragma: no cover
    print(f"[bots] IPv4-режим не включился: {e}", flush=True)


API = "https://api.telegram.org/bot{token}/{method}"

# Генерал. Старое имя переменной TELEGRAM_BOT_TOKEN поддерживаем, чтобы
# ничего не отвалилось до того, как переменные в Amvera переименованы.
ADMIN_TOKEN = (
    os.getenv("ADMIN_BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or ""
).strip()

JARVIS_TOKEN = (
    os.getenv("JARVIS_BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN_JARVIS")
    or ""
).strip()

ADMIN_CHAT_ID = (
    os.getenv("ADMIN_CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or "6080897180"
).strip()


def _mask(text: str) -> str:
    """Токены не должны попадать ни в лог, ни тем более в ответ браузеру."""
    for t in (ADMIN_TOKEN, JARVIS_TOKEN):
        if t:
            text = text.replace(t, "***")
    return text


def _send(token: str, who: str, chat_id, text: str, markup=None):
    """Возвращает (ok, причина). Причину пишем в лог, наружу не отдаём."""
    if not token:
        print(f"[{who}] токен не задан", flush=True)
        return False, "no_token"
    if not chat_id:
        return False, "no_chat_id"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if markup:
        payload["reply_markup"] = markup

    last = ""
    for attempt in (1, 2, 3):
        try:
            r = requests.post(
                API.format(token=token, method="sendMessage"),
                json=payload,
                timeout=15,
            )
            if r.status_code == 200:
                return True, ""
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            print(f"[{who}] попытка {attempt} — {_mask(last)}", flush=True)
            # 4xx — мы шлём что-то не то (чат не найден, бот заблокирован
            # клиентом). Повторять бессмысленно.
            if 400 <= r.status_code < 500:
                break
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            print(f"[{who}] попытка {attempt} — сеть: {_mask(last)}", flush=True)
    return False, _mask(last)


def send_admin(text: str, markup=None):
    """Генерал → Гульнаре."""
    return _send(ADMIN_TOKEN, "general", ADMIN_CHAT_ID, text, markup)


def send_client(chat_id, text: str, markup=None):
    """Джарвис → клиенту. Работает только если клиент когда-то писал боту:
    иначе Telegram вернёт 403 'bot can't initiate conversation'."""
    return _send(JARVIS_TOKEN, "jarvis", chat_id, text, markup)


def health():
    """Живы ли оба токена. Для /api/health и для сторожа."""
    out = {}
    for name, token in (("general", ADMIN_TOKEN), ("jarvis", JARVIS_TOKEN)):
        if not token:
            out[name] = "нет токена"
            continue
        try:
            r = requests.get(API.format(token=token, method="getMe"), timeout=8)
            body = r.json() if r.status_code == 200 else {}
            if body.get("ok"):
                out[name] = "@" + body["result"].get("username", "?")
            else:
                out[name] = _mask(f"HTTP {r.status_code}: {r.text[:150]}")
        except Exception as e:
            out[name] = f"{type(e).__name__}: {e}"
    return out
