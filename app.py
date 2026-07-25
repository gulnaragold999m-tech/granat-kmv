import os
import json
import socket
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from flask import Flask, send_from_directory, request, jsonify, redirect

# Принудительно ходим по IPv4. На Amvera исходящие соединения по IPv6 не
# проходят (Errno 101 "Network is unreachable"), а requests может выбрать
# именно IPv6-адрес api.telegram.org и упасть, хотя IPv4 работает.
try:
    import urllib3.util.connection as urllib3_cn

    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception as e:
    print(f"[init] IPv4-режим не включился: {e}", flush=True)

app = Flask(__name__, static_folder=".", static_url_path="")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# Читаем оба варианта имени, чтобы не зависеть от того, как переменная
# названа в панели Amvera.
CHAT_ID = (
    os.getenv("ADMIN_CHAT_ID")
    or os.getenv("TELEGRAM_CHAT_ID")
    or "6080897180"
).strip()

# Постоянное хранилище Amvera: заявка ложится сюда, даже если Telegram молчит.
ORDERS_FILE = "/data/orders.jsonl"

# Контейнер живёт по Гринвичу, а смотреть на заявки нам по-московски.
TZ = ZoneInfo("Europe/Moscow")


def now_msk():
    """Московское время без пометки о зоне — чтобы в файле было понятно
    и сравнение со старыми записями не ломалось."""
    return datetime.now(TZ).replace(tzinfo=None)

OLD_HOST = "granat-site-granatgold999.amvera.io"
NEW_DOMAIN = "https://granat-kmv.ru"


def mask(s):
    """Чтобы токен не утёк ни в лог, ни тем более в ответ браузеру."""
    return s.replace(TOKEN, "***") if TOKEN else s


def save_order(payload, delivered, reason=""):
    record = {
        "at": now_msk().isoformat(timespec="seconds"),
        "delivered": delivered,
        "reason": reason,
        **payload,
    }
    try:
        os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
        with open(ORDERS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[order] заявку не удалось записать на диск: {e}", flush=True)


def send_to_telegram(text):
    """Возвращает (ok, причина). Причину пишем в лог, наружу не отдаём."""
    if not TOKEN:
        print("[telegram] TELEGRAM_BOT_TOKEN не задан", flush=True)
        return False, "no_token"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    last = ""
    for attempt in (1, 2, 3):
        try:
            r = requests.post(
                url, json={"chat_id": CHAT_ID, "text": text}, timeout=15
            )
            if r.status_code == 200:
                return True, ""
            # Главное, чего не хватало раньше: сам ответ Telegram в логе.
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            print(f"[telegram] попытка {attempt} — {mask(last)}", flush=True)
            # 4xx означает, что мы шлём что-то не то (чат не найден, бот
            # заблокирован) — повторять бессмысленно.
            if 400 <= r.status_code < 500:
                break
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            print(f"[telegram] попытка {attempt} — сеть: {mask(last)}", flush=True)
    return False, mask(last)


@app.before_request
def redirect_old_domain():
    if request.host.lower() == OLD_HOST:
        return redirect(NEW_DOMAIN + request.full_path.rstrip("?"), code=301)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/privacy.html")
def privacy():
    return send_from_directory(".", "privacy.html")


def count_undelivered(hours=24):
    """Заявки, зависшие ПОСЛЕ последней успешной отправки.

    Любая дошедшая заявка обнуляет счёт: значит связь восстановилась, и
    вспоминать о прежнем сбое больше незачем. Иначе сторож неделю будет
    поминать давно почившую проблему, и его перестанут читать.
    Старше N часов тоже не считаем — на случай, если успешных не было вовсе.
    """
    cutoff = now_msk() - timedelta(hours=hours)
    pending = 0
    try:
        with open(ORDERS_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("delivered"):
                    pending = 0
                    continue
                try:
                    if datetime.fromisoformat(rec["at"]) >= cutoff:
                        pending += 1
                except Exception:
                    continue
    except FileNotFoundError:
        return 0
    except Exception:
        return -1
    return pending


@app.route("/api/health")
def health():
    """Самопроверка для сторожа: жив ли сайт и принимает ли Telegram наш токен.

    Никому ничего не отправляет — поэтому дёргать можно хоть каждые пять минут.
    Именно этой проверки не хватало 25.07.2026, когда форма молча падала
    с 401 Unauthorized и об этом никто не знал.
    """
    ok, reason = False, "TELEGRAM_BOT_TOKEN не задан"
    if TOKEN:
        # Две попытки и запас по времени: один медленный ответ Telegram
        # не должен выглядеть как поломка формы.
        for _ in range(2):
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=8
                )
                ok = r.status_code == 200 and r.json().get("ok") is True
                if ok:
                    break
                reason = f"HTTP {r.status_code}: {r.text[:200]}"
                if 400 <= r.status_code < 500:
                    break  # чужой токен — повторять бессмысленно
            except Exception as e:
                reason = f"{type(e).__name__}: {e}"

    return jsonify(
        ok=ok,
        telegram="ok" if ok else mask(reason),
        chat_id_set=bool(CHAT_ID),
        undelivered=count_undelivered(),
    )


@app.route("/api/order", methods=["POST"])
def order():
    data = request.get_json(silent=True) or request.form or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(ok=False, error="Укажите имя"), 400

    phone = (data.get("phone") or "").strip()
    service = (data.get("service") or "").strip()
    notes = (data.get("notes") or "").strip()
    payload = {"name": name, "phone": phone, "service": service, "notes": notes}

    lines = ["🔔 НОВАЯ ЗАЯВКА С САЙТА", "", f"👤 Имя: {name}"]
    if phone:
        lines.append(f"📞 Телефон/Telegram: {phone}")
    if service:
        lines.append(f"🛍 Услуга: {service}")
    if notes:
        lines.append(f"📝 Пожелания: {notes}")

    ok, reason = send_to_telegram("\n".join(lines))
    save_order(payload, delivered=ok, reason=reason)

    if ok:
        return jsonify(ok=True)

    # Заявка на диске лежит, но до Telegram не дошла. Браузеру отдаём
    # нейтральный текст — он покажет клиенту кнопки WhatsApp/Telegram.
    print(f"[order] заявка сохранена, но не доставлена: {reason}", flush=True)
    return jsonify(ok=False, saved=True, error="not_delivered"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
