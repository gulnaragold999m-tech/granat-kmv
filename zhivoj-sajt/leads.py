# -*- coding: utf-8 -*-
"""
Общее хранилище заявок: сайт пишет, Джарвис читает.

Зачем отдельный модуль. Заявка рождается на сайте (app.py), а дальше её
подхватывает бот (jarvis_bot.py) — это два разных процесса. Чтобы они не
дублировали логику и не расходились в формате, вся работа с заявками живёт
здесь, а оба импортируют этот файл.

Формат — журнал только на дозапись (append-only jsonl). Каждая строка это
не «состояние заявки», а событие: создана, клиент пришёл в бота, ТЗ собрано.
Состояние собирается из всех событий по её номеру. Так ничего не теряется
при одновременной записи из двух процессов — файл не перезаписывается.

Важно: работает, только если сайт и бот запущены в ОДНОМ контейнере Amvera
(общая папка /data). Если бот вынесен в отдельное приложение — /data у него
своя, и обмен нужен по HTTP, а не через файл.
"""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

DATA_DIR = os.getenv("LEADS_DIR", "/data")
LEADS_FILE = os.path.join(DATA_DIR, "leads.jsonl")
COUNTER_FILE = os.path.join(DATA_DIR, "lead_counter")

BOT_USERNAME = os.getenv("BOT_USERNAME", "GranatJarvis_bot")

TZ = ZoneInfo("Europe/Moscow")


def now_msk_iso() -> str:
    """Контейнер живёт по Гринвичу, а нам смотреть по-московски."""
    return datetime.now(TZ).replace(tzinfo=None).isoformat(timespec="seconds")


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def next_id() -> int:
    """Следующий номер заявки. При недоступном диске отдаём номер из времени —
    заявка всё равно должна получить опознавательный знак, пусть некрасивый."""
    try:
        _ensure_dir()
        cur = 0
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, encoding="utf-8") as f:
                cur = int((f.read() or "0").strip() or 0)
        cur += 1
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(cur))
        return cur
    except Exception as e:
        print(f"[leads] счётчик недоступен ({e}), номер по времени", flush=True)
        return int(datetime.now(TZ).strftime("%d%H%M%S"))


def log(lead_id: int, event: str, **fields) -> None:
    """Дописать событие по заявке. Никогда не падает наружу: потеря строки
    в журнале не должна ломать приём заявки с сайта."""
    record = {"id": lead_id, "at": now_msk_iso(), "event": event, **fields}
    try:
        _ensure_dir()
        with open(LEADS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[leads] событие не записано: {e}", flush=True)


def find(lead_id: int) -> dict | None:
    """Собрать состояние заявки из всех её событий. None — если такой нет."""
    state: dict = {}
    events: list[str] = []
    try:
        with open(LEADS_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("id") != lead_id:
                    continue
                events.append(rec.get("event", ""))
                state.update({k: v for k, v in rec.items() if k != "event"})
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[leads] журнал не прочитан: {e}", flush=True)
        return None
    if not state:
        return None
    state["events"] = events
    return state


def deep_link(lead_id: int) -> str:
    """Ссылка, по которой клиент входит в бота вместе со своей заявкой.

    Telegram передаст боту всё после ?start= в первом же сообщении —
    так Джарвис узнаёт, кто перед ним, ещё до первого вопроса.
    """
    return f"https://t.me/{BOT_USERNAME}?start=lead_{lead_id}"


def pending(minutes: int = 15) -> list[dict]:
    """Заявки, где клиент так и не зашёл в бота за отведённое время.

    Их и должен показывать Генерал: человек оставил контакт, но до диалога
    не дошёл — значит звонить надо руками, иначе он просто потеряется.
    """
    out = []
    seen: dict[int, dict] = {}
    try:
        with open(LEADS_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                lid = rec.get("id")
                if lid is None:
                    continue
                st = seen.setdefault(lid, {"events": []})
                st["events"].append(rec.get("event", ""))
                st.update({k: v for k, v in rec.items() if k != "event"})
    except FileNotFoundError:
        return []
    except Exception:
        return []

    now = datetime.now(TZ).replace(tzinfo=None)
    for lid, st in seen.items():
        ev = st["events"]
        # Клиент дошёл до бота или ТЗ уже собрано — тревожить незачем.
        # "alerted" — про эту заявку Гульнаре уже сказали, второй раз не надо:
        # сторож, который повторяет одно и то же, перестаёт читаться.
        if "entered_bot" in ev or "brief_ready" in ev or "alerted" in ev:
            continue
        try:
            age = (now - datetime.fromisoformat(st["at"])).total_seconds() / 60
        except Exception:
            continue
        if age >= minutes:
            st["id"] = lid
            st["age_min"] = int(age)
            out.append(st)
    return sorted(out, key=lambda x: x["id"])

def norm_phone(raw: str) -> str:
    """Телефон к сравнимому виду: только последние 10 цифр.

    Клиент пишет как хочет — +7 (999) 244-99-99, 89992449999, 9992449999.
    Для узнавания «это тот же человек» важны только последние десять цифр.
    Пустая строка, если цифр меньше — значит опознать нельзя.
    """
    digits = "".join(c for c in (raw or "") if c.isdigit())
    return digits[-10:] if len(digits) >= 10 else ""


def link_client(lead_id: int, chat_id, phone: str = "", username: str = "") -> None:
    """Клиент дошёл до бота. Запоминаем его chat_id — с этого момента Джарвис
    может писать ему первым, и следующая заявка от него пойдёт без кнопки."""
    log(
        lead_id,
        "entered_bot",
        chat_id=chat_id,
        tg_username=username,
        phone_key=norm_phone(phone),
    )


def find_chat_by_phone(phone: str):
    """Знаем ли мы этого человека по телефону. Возвращает chat_id или None.

    Именно эта функция превращает схему в полный автомат для повторных
    клиентов: если chat_id известен, кнопка на сайте уже не нужна.
    """
    key = norm_phone(phone)
    if not key:
        return None
    found = None
    try:
        with open(LEADS_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("chat_id") and rec.get("phone_key") == key:
                    found = rec["chat_id"]  # берём самый свежий
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[leads] поиск по телефону не удался: {e}", flush=True)
        return None
    return found

def mark_alerted(lead_id: int) -> None:
    """Гульнаре сказали про эту тишину. Больше не повторяем."""
    log(lead_id, "alerted")


def cheque(lead: dict) -> str:
    """Человекочитаемый чек из заявки симулятора: сумма и что клиент выбрал."""
    parts = []
    total = lead.get("total")
    if total:
        try:
            parts.append(f"{int(total):,}".replace(",", " ") + " ₽")
        except Exception:
            parts.append(str(total))
    opts = lead.get("options") or []
    if isinstance(opts, str):
        opts = [opts]
    if opts:
        parts.append(", ".join(str(o) for o in opts))
    return " — ".join(parts)
