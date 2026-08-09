import os
import json
import smtplib
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import requests
from flask import (Flask, send_from_directory, request, jsonify, redirect,
                   render_template)

import bots
import leads

# Принудительно ходим по IPv4. На Amvera исходящие соединения по IPv6 не
# проходят (Errno 101 "Network is unreachable"), а requests может выбрать
# именно IPv6-адрес api.telegram.org и упасть, хотя IPv4 работает.
try:
    import urllib3.util.connection as urllib3_cn

    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception as e:
    print(f"[init] IPv4-режим не включился: {e}", flush=True)

# То же самое, но для всего остального, что ходит наружу мимо requests —
# в первую очередь для почты: smtplib открывает сокет сам и про настройку
# выше не знает. Без этого письмо с заявкой упало бы на первом же адресе
# IPv6, который вернёт DNS.
_real_getaddrinfo = socket.getaddrinfo


def _getaddrinfo_ipv4_only(*args, **kwargs):
    res = _real_getaddrinfo(*args, **kwargs)
    ipv4 = [r for r in res if r[0] == socket.AF_INET]
    # Если IPv4-адресов нет вовсе, отдаём что есть: пусть лучше попробует
    # и честно упадёт с понятной ошибкой, чем молча вернёт пустой список.
    return ipv4 or res


socket.getaddrinfo = _getaddrinfo_ipv4_only

app = Flask(__name__, static_folder=".", static_url_path="")

# Картинки, логотип и скрипты браузер держит у себя сутки и не запрашивает
# заново на каждой странице. По умолчанию Flask ставит 12 часов и при каждом
# переходе всё равно ходит на сервер спрашивать «не изменилось ли». На
# портфолио это лишние полтора десятка запросов на ровном месте.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400

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


# ── ВКонтакте: второй канал доставки заявок ──────────────────────────────
# ЗАЧЕМ. Telegram — одна точка отказа: 03.08.2026 он перестал принимать
# сообщения, и заявки уходили в пустоту. ВК живёт на отдельном токене и
# отдельной инфраструктуре, поэтому одновременный отказ обоих почти
# невероятен. Каналы независимы: отказ одного не отменяет второй.
#
# ПЕРЕМЕННЫЕ (Amvera → Переменные окружения):
#   VK_TOKEN   — ключ сообщества с правом «Сообщения сообщества».
#   VK_PEER_ID — куда слать: числовой id, короткое имя или ссылка на страницу.
#
# ВАЖНО: сообщество не может написать человеку первым, пока тот сам не
# написал сообществу хотя бы раз — как кнопка «Старт» у ботов Telegram.
# Иначе ВК ответит ошибкой 901.
VK_TOKEN = os.getenv("VK_TOKEN", "").strip()
VK_PEER_ID = os.getenv("VK_PEER_ID", "").strip()

# ── Почта: третий канал доставки заявки ─────────────────────────────────
# 09.08.2026 Telegram отвечал с третьей попытки за пятнадцать секунд, а ключ
# ВКонтакте оказался отозван. Заявка при этом лежала на диске, но узнать о
# ней было неоткуда. Почта на Яндексе живёт внутри страны и не зависит ни от
# того, ни от другого — поэтому она здесь третьей, а не вместо.
#
# ПЕРЕМЕННЫЕ (Amvera → Переменные окружения):
#   MAIL_LOGIN    — полный адрес ящика, например gulnaravibecoder999@yandex.ru
#   MAIL_PASSWORD — ПАРОЛЬ ПРИЛОЖЕНИЯ из Яндекс ID, не пароль от почты.
#                   Обычный пароль Яндекс для программ не принимает.
#   MAIL_TO       — куда слать заявку. Не задан — шлём на сам ящик.
MAIL_HOST = os.getenv("MAIL_HOST", "smtp.yandex.ru").strip()
MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
MAIL_LOGIN = os.getenv("MAIL_LOGIN", "").strip()
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
MAIL_TO = os.getenv("MAIL_TO", "").strip() or MAIL_LOGIN

# Расшифровки частых кодов: без них «ошибка 901» в логах через месяц
# ничего не скажет тому, кто их откроет.
VK_ERRORS = {
    5: "ключ недействителен или отозван — получите новый в настройках сообщества",
    901: "получатель ни разу не писал сообществу — напишите сообществу любое "
         "сообщение со своей страницы",
    902: "настройки приватности получателя запрещают сообществу писать ему",
    914: "сообщение длиннее допустимого",
    100: "неверный параметр запроса (чаще всего peer_id)",
}

# id получателя спрашиваем у ВК один раз за жизнь процесса и запоминаем:
# короткое имя меняется редко, а лишний запрос на каждую заявку ни к чему.
_vk_peer_cache = None


def vk_peer():
    """Числовой id получателя. Принимает id, короткое имя или ссылку."""
    global _vk_peer_cache
    if _vk_peer_cache:
        return _vk_peer_cache

    raw = VK_PEER_ID.rstrip("/").split("/")[-1]
    if raw.lstrip("-").isdigit():
        _vk_peer_cache = raw
        return raw
    if raw.startswith("id") and raw[2:].isdigit():
        _vk_peer_cache = raw[2:]
        return _vk_peer_cache

    try:
        r = requests.post(
            "https://api.vk.com/method/utils.resolveScreenName",
            data={"access_token": VK_TOKEN, "v": "5.199", "screen_name": raw},
            timeout=15,
        ).json()
        object_id = str(r.get("response", {}).get("object_id") or "")
        if object_id:
            _vk_peer_cache = object_id
            return object_id
        print(f"[vk] не удалось определить id по «{raw}»: {r}", flush=True)
    except Exception as e:
        print(f"[vk] resolveScreenName: {type(e).__name__}: {e}", flush=True)
    return ""


def send_to_vk(text):
    """Дубль заявки в личку ВК. Возвращает (ok, причина).

    Наружу не падает никогда: это второй канал, и его отказ не должен
    ронять обработку заявки.
    """
    if not VK_TOKEN or not VK_PEER_ID:
        return False, "не настроен"

    peer = vk_peer()
    if not peer:
        return False, "не удалось определить id получателя"

    try:
        r = requests.post(
            "https://api.vk.com/method/messages.send",
            data={
                "access_token": VK_TOKEN,
                "v": "5.199",
                "peer_id": peer,
                # random_id обязателен: по нему ВК отбрасывает дубли, если
                # сеть моргнула и запрос ушёл дважды. Должен влезать в int32.
                "random_id": (int(datetime.now().timestamp() * 1000) % 2_000_000_000),
                # 4096 — предел ВК на длину. Режем сами: обрезанная заявка
                # полезнее ошибки 914 и полностью потерянной заявки.
                "message": text[:4000],
            },
            timeout=15,
        ).json()

        if "response" in r:
            return True, ""

        # ВК отвечает HTTP 200 даже на ошибку — причина лежит в теле.
        err = r.get("error", {})
        code = err.get("error_code")
        hint = f" — {VK_ERRORS[code]}" if code in VK_ERRORS else ""
        reason = f"{code} {err.get('error_msg', '')}{hint}"
        print(f"[vk] отказ: {reason}", flush=True)
        return False, reason
    except Exception as e:
        reason = f"сеть: {type(e).__name__}: {e}"
        print(f"[vk] {reason}", flush=True)
        return False, reason


def send_to_mail(subject, text):
    """Дубль заявки письмом. Возвращает (ok, причина).

    Наружу не падает никогда: это ещё один параллельный канал, и его отказ
    не должен ронять обработку заявки. Пароль в причину не попадает —
    smtplib его в текст ошибки не кладёт, но на всякий случай прогоняем
    результат через mask(), как и телеграмный.
    """
    if not MAIL_LOGIN or not MAIL_PASSWORD:
        return False, "не настроена"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_LOGIN
    msg["To"] = MAIL_TO
    msg.set_content(text)

    try:
        with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT,
                              context=ssl.create_default_context(),
                              timeout=15) as s:
            s.login(MAIL_LOGIN, MAIL_PASSWORD)
            s.send_message(msg)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        # Самая частая причина: в переменную положили пароль от почты
        # вместо пароля приложения. Пишем прямым текстом, чтобы через месяц
        # не гадать над «535 5.7.8».
        reason = "вход отклонён — нужен пароль приложения из Яндекс ID, а не пароль от почты"
        print(f"[mail] {reason}", flush=True)
        return False, reason
    except Exception as e:
        reason = f"{type(e).__name__}: {e}"
        print(f"[mail] {mask(reason)}", flush=True)
        return False, mask(reason)


def mail_health():
    """Принимает ли ящик наш пароль. Письмо не отправляет — только вход.

    Проверяем по-настоящему, а не «переменная задана»: ровно так мы
    09.08.2026 проглядели отозванный ключ ВКонтакте — он был задан и
    считался рабочим, пока не полезли в логи руками.
    """
    if not MAIL_LOGIN or not MAIL_PASSWORD:
        return "не настроена"
    try:
        with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT,
                              context=ssl.create_default_context(),
                              timeout=10) as s:
            s.login(MAIL_LOGIN, MAIL_PASSWORD)
        return "ok"
    except smtplib.SMTPAuthenticationError:
        return "вход отклонён — нужен пароль приложения из Яндекс ID"
    except Exception as e:
        return mask(f"{type(e).__name__}: {e}")


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


def deliver(subject, text):
    """Разослать заявку по всем каналам сразу. Возвращает три пары (ok, причина).

    Каналы независимы, поэтому ждать их по очереди незачем — а именно так
    и было до 09.08.2026. Худший случай складывался: Telegram три попытки
    по 15 секунд, ВКонтакте 15, почта 15 — больше минуты, и всё это время
    у клиента на кнопке крутится «Отправляем». Форма выглядела зависшей, и
    человек уходил, хотя заявка уже лежала на диске.

    Одновременно ждём самый медленный канал, а не сумму всех трёх. Ответы
    забираем полностью: заявка должна попасть в журнал с честными отметками
    по каждому каналу, иначе счётчик недоставленных снова начнёт врать.
    """
    with ThreadPoolExecutor(max_workers=3) as pool:
        tg = pool.submit(send_to_telegram, text)
        vk = pool.submit(send_to_vk, text)
        mail = pool.submit(send_to_mail, subject, text)
        return tg.result(), vk.result(), mail.result()


@app.before_request
def redirect_old_domain():
    if request.host.lower() == OLD_HOST:
        return redirect(NEW_DOMAIN + request.full_path.rstrip("?"), code=301)


# ── Страницы сайта ──────────────────────────────────────────────────────
# Раньше сайт был одностраничным: все разделы жили в index.html и
# открывались якорями (#pechat, #cifra). Для поиска это одна страница с
# одним заголовком — по запросу «печать приглашений Пятигорск» и по
# запросу «телеграм-бот под ключ» Яндекс видел один и тот же title.
# Теперь у каждого направления свой адрес, свой title и свой description,
# и каждое можно продвигать отдельно.
#
# Разметка не переписана, а разложена по кусочкам: templates/base.html
# держит общую обвязку (шапка, подвал, стили, счётчик, бот-проводник),
# templates/partials/* — те же секции, что были в index.html, слово в слово.


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/pechat")
def pechat():
    return render_template("pechat.html")


@app.route("/cifra")
def cifra():
    return render_template("cifra.html")


@app.route("/raboty")
def raboty():
    return render_template("raboty.html")


@app.route("/kak-rabotaem")
def kak_rabotaem():
    return render_template("kak-rabotaem.html")


@app.route("/kontakty")
def kontakty():
    return render_template("kontakty.html")


# Старые ссылки с якорями остаются рабочими: их присылали в переписке,
# они разошлись по сторис и по чатам. Якорь браузер на сервер не шлёт,
# поэтому ловим только те адреса, что писали руками.
@app.route("/index.html")
def index_html():
    return redirect("/", code=301)


# Статика раздаётся из корня проекта, и без этой заглушки заготовки страниц
# отдавались бы как обычные файлы — со служебной разметкой наружу.
@app.route("/templates/<path:_ignored>")
def templates_are_not_public(_ignored):
    return ("Not Found", 404)


# sitemap.xml и robots.txt отдаём явными маршрутами, а не как обычную статику.
# Внешний загрузчик при проверке 08.08.2026 получил вместо XML нечитаемые
# байты: раздача статики отдаёт файл как есть и полагается на угаданный тип.
# Здесь тип и кодировка заданы прямо, поэтому гадать больше нечего.
@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory(".", "sitemap.xml", mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return send_from_directory(".", "robots.txt", mimetype="text/plain")


# Свой экран вместо служебной страницы Flask: с меню, ссылками на разделы и
# телефоном. Человек, попавший на битую ссылку, остаётся на сайте, а не
# закрывает вкладку с надписью «Not Found» на английском.
@app.errorhandler(404)
def page_not_found(_e):
    return render_template("404.html"), 404


@app.route("/privacy.html")
def privacy():
    return send_from_directory(".", "privacy.html")


@app.route("/consent.html")
def consent():
    """Согласие на обработку ПДн — отдельным документом, как требует
    редакция 152-ФЗ, действующая с 01.09.2025."""
    return send_from_directory(".", "consent.html")


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


def vk_health():
    """Жив ли ключ сообщества. Ничего не отправляет — только спрашивает,
    чьё это сообщество, и на этом проверяет ключ.

    Коды ошибок расшифровываем теми же словами, что и при отправке: «5»
    в отчёте через месяц ничего не скажет, «ключ отозван» — скажет.
    """
    if not VK_TOKEN:
        return "VK_TOKEN не задан"
    if not VK_PEER_ID:
        return "VK_PEER_ID не задан — некуда слать"
    try:
        r = requests.get(
            "https://api.vk.com/method/groups.getById",
            params={"access_token": VK_TOKEN, "v": "5.199"},
            timeout=10,
        ).json()
        if "response" in r:
            return "ok"
        err = r.get("error", {})
        code = err.get("error_code")
        hint = f" — {VK_ERRORS[code]}" if code in VK_ERRORS else ""
        return f"{code} {err.get('error_msg', '')}{hint}"
    except Exception as e:
        return f"сеть: {type(e).__name__}: {e}"


@app.route("/api/health")
def health():
    """Самопроверка для сторожа: жив ли сайт и принимает ли Telegram наш токен.

    Никому ничего не отправляет — поэтому дёргать можно хоть каждые пять минут.
    Именно этой проверки не хватало 25.07.2026, когда форма молча падала
    с 401 Unauthorized и об этом никто не знал.
    """
    # Проверки каналов не зависят друг от друга, поэтому идут одновременно —
    # иначе на медленной почте вся страница проверки ждала бы её одну.
    with ThreadPoolExecutor(max_workers=2) as pool:
        vk_state = pool.submit(vk_health)
        mail_state = pool.submit(mail_health)

        ok, reason = False, "TELEGRAM_BOT_TOKEN не задан"
        if TOKEN:
            # Запас по времени тот же, что у настоящей отправки заявки: три
            # попытки по 15 секунд. Раньше здесь стояло 8 секунд и две попытки,
            # и 09.08.2026 это дало ложную тревогу: проверка кричала «Telegram
            # недоступен», а заявка в это же время спокойно доходила. Проверка,
            # которая строже боевого пути, врёт — и её перестают читать.
            for _ in range(3):
                try:
                    r = requests.get(
                        f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=15
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
        # Резервный канал раньше в проверке не участвовал, и недействительный
        # ключ ВК всплыл только из логов, когда его пошли искать руками.
        vk=vk_state.result(),
        mail=mail_state.result(),
        # Оба бота одним взглядом: кто из них жив и под каким именем.
        bots=bots.health(),
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

    # Канал связи клиент выбирает прямо в форме. Приводим к трём значениям
    # из ТЗ — Telegram / WhatsApp / VK, — чтобы в заявке и в CRM было
    # единообразно, что бы браузер ни прислал.
    _CHANNELS = {"telegram": "Telegram", "whatsapp": "WhatsApp",
                 "vk": "VK", "вконтакте": "VK"}
    channel = _CHANNELS.get((data.get("preferred_channel") or "").strip().lower(), "")

    payload = {"name": name, "phone": phone, "service": service, "notes": notes,
               "preferred_channel": channel}

    # Номер нужен, чтобы Джарвис узнал клиента, когда тот придёт в бота,
    # и чтобы Генерал мог сказать «заявка №47 висит без ответа».
    lead_id = leads.next_id()
    payload["lead"] = lead_id
    leads.log(lead_id, "created", source="site_form", **payload)

    lines = [f"🔔 НОВАЯ ЗАЯВКА С САЙТА №{lead_id}", "", f"👤 Имя: {name}"]
    if phone:
        lines.append(f"📞 Телефон/Telegram: {phone}")
    if channel:
        icon = {"Telegram": "✈️", "WhatsApp": "🟢", "VK": "🔵"}.get(channel, "💬")
        lines.append(f"{icon} Писать в: {channel}")
    if service:
        lines.append(f"🛍 Услуга: {service}")
    if notes:
        lines.append(f"📝 Пожелания: {notes}")
    lines.append("")
    lines.append("Ждём клиента в боте для сбора ТЗ.")

    # ── 1. ГЕНЕРАЛ докладывает Гульнаре ──────────────────────────────────
    # Три канала, независимо друг от друга и одновременно. Заявка считается
    # доставленной, если её принял хотя бы один: отказ Telegram больше не
    # теряет клиента.
    text = "\n".join(lines)
    (ok, reason), (vk_ok, vk_reason), (mail_ok, mail_reason) = deliver(
        f"Заявка с сайта №{lead_id} — {name}", text
    )
    delivered = ok or vk_ok or mail_ok
    save_order(payload, delivered=delivered,
               reason="" if delivered else
                      f"telegram: {reason}; вк: {vk_reason}; почта: {mail_reason}")
    leads.log(lead_id, "notified", delivered=delivered,
              telegram=ok, vk=vk_ok, mail=mail_ok)

    # ── 2. ДЖАРВИС забирает клиента ──────────────────────────────────────
    # Если человек уже когда-то писал боту, его chat_id у нас есть — тогда
    # Джарвис пишет сам, сразу, и клиенту вообще ничего нажимать не надо.
    # Незнакомому написать нельзя: Telegram запрещает боту начинать первым.
    pushed = False
    chat = leads.find_chat_by_phone(phone)
    if chat:
        hello = (
            f"Здравствуйте, {name}! Вы только что оставили заявку "
            f"на сайте granat-kmv.ru (№{lead_id})."
        )
        if service:
            hello += f"\nЗадача: <b>{service}</b>"
        hello += (
            "\n\nЧтобы Гульнара сразу назвала точную сумму и срок, уточню "
            "несколько деталей — это пара минут. Начнём?"
        )
        markup = {
            "inline_keyboard": [[
                {"text": "Да, уточним детали",
                 "callback_data": f"lead:start:{lead_id}"},
                {"text": "Позже", "callback_data": f"lead:later:{lead_id}"},
            ]]
        }
        pushed, why = bots.send_client(chat, hello, markup)
        leads.log(lead_id, "jarvis_pushed", ok=pushed, reason=why, chat_id=chat)
        if pushed:
            bots.send_admin(
                f"🤖 Джарвис сам написал клиенту по заявке №{lead_id} — "
                "он у нас уже был, кнопка не понадобилась."
            )

    if ok or pushed:
        # tg — ссылка «Продолжить в Telegram» для новых клиентов. Номер
        # заявки внутри, поэтому Джарвис узнаёт человека с первого сообщения.
        return jsonify(
            ok=True,
            lead=lead_id,
            tg=leads.deep_link(lead_id),
            pushed=pushed,
        )

    if delivered:
        # Telegram молчит, но заявка ушла письмом или во ВКонтакте — значит
        # она у нас, и пугать клиента запасными кнопками незачем. Ссылку в
        # бота не даём: раз Telegram недоступен нам, клиенту он, скорее
        # всего, тоже не откроется.
        return jsonify(ok=True, lead=lead_id)

    # Заявка на диске лежит, но не дошла ни одним каналом. Браузеру отдаём
    # нейтральный текст — он покажет клиенту кнопки WhatsApp/Telegram.
    print(f"[order] заявка сохранена, но не доставлена: {reason}", flush=True)
    return jsonify(ok=False, saved=True, error="not_delivered"), 200


@app.route("/api/bot-lead", methods=["POST"])
def bot_lead():
    """Заявка из симулятора на странице: контакт + собранная конфигурация.

    Отдельно от /api/order, потому что здесь есть чек — сумма и выбранные
    опции. Он ложится в журнал заявки: в ссылку ?start= его не втиснуть
    (Telegram даёт 64 символа), а по номеру Джарвис поднимет всё целиком.
    """
    data = request.get_json(silent=True) or request.form or {}

    contact = (data.get("contact") or "").strip()
    if not contact:
        return jsonify(ok=False, error="Укажите Telegram или телефон"), 400

    path = data.get("path") or []
    if isinstance(path, str):
        path = [path]
    route_text = " → ".join(str(p) for p in path if str(p).strip())

    try:
        total = int(data.get("total") or 0)
    except (TypeError, ValueError):
        total = 0

    payload = {
        "source": "site_simulator",
        "contact": contact,
        "phone": contact,          # чтобы узнавание по телефону работало и здесь
        "service": route_text,
        "total": total,
        "options": [str(p) for p in path if str(p).strip()],
        "scenario": (data.get("scenario") or "").strip(),
    }

    lead_id = leads.next_id()
    payload["lead"] = lead_id
    leads.log(lead_id, "created", **payload)

    # ── ГЕНЕРАЛ докладывает ──────────────────────────────────────────────
    lines = [f"🤖 ЗАЯВКА ИЗ СИМУЛЯТОРА №{lead_id}", "", f"📞 Контакт: {contact}"]
    if route_text:
        lines.append(f"🧭 Собрал: {route_text}")
    if total:
        lines.append("💰 На сумму: {:,} ₽".format(total).replace(",", " "))
    lines.append("")
    lines.append("Ждём клиента в боте для сбора ТЗ.")

    # Все каналы сразу — как и в заявке с формы выше.
    text = "\n".join(lines)
    (ok, reason), (vk_ok, vk_reason), (mail_ok, mail_reason) = deliver(
        f"Заявка из симулятора №{lead_id}", text
    )
    delivered = ok or vk_ok or mail_ok
    save_order(payload, delivered=delivered,
               reason="" if delivered else
                      f"telegram: {reason}; вк: {vk_reason}; почта: {mail_reason}")
    leads.log(lead_id, "notified", delivered=delivered,
              telegram=ok, vk=vk_ok, mail=mail_ok)

    # ── ДЖАРВИС забирает клиента, если он у нас уже был ──────────────────
    pushed = False
    chat = leads.find_chat_by_phone(contact)
    if chat:
        hello = f"Здравствуйте! Вижу вашу конфигурацию с сайта (заявка №{lead_id})."
        if route_text:
            hello += f"\nВы собрали: <b>{route_text}</b>"
        if total:
            hello += "\nПредварительно: <b>{:,} ₽</b>".format(total).replace(",", " ")
        hello += (
            "\n\nУточню пару деталей — и Гульнара подтвердит точную сумму и срок. "
            "Начнём?"
        )
        markup = {
            "inline_keyboard": [[
                {"text": "Да, уточним детали",
                 "callback_data": f"lead:start:{lead_id}"},
                {"text": "Позже", "callback_data": f"lead:later:{lead_id}"},
            ]]
        }
        pushed, why = bots.send_client(chat, hello, markup)
        leads.log(lead_id, "jarvis_pushed", ok=pushed, reason=why, chat_id=chat)

    if ok or pushed:
        return jsonify(
            ok=True, lead=lead_id, tg=leads.deep_link(lead_id), pushed=pushed
        )

    print(f"[bot-lead] заявка сохранена, но не доставлена: {reason}", flush=True)
    return jsonify(
        ok=False, saved=True, error="not_delivered",
        lead=lead_id, tg=leads.deep_link(lead_id),
    ), 200


@app.route("/api/watch")
def watch():
    """Сторож тишины. Дёргается по расписанию — Amvera → Cron Jobs.

    Находит заявки, где клиент оставил контакт, но до бота не дошёл, и шлёт
    Гульнаре алерт с телефоном: перехватить вручную, пока человек тёплый.
    Про каждую заявку говорит один раз — сторож, повторяющий одно и то же,
    перестаёт читаться.

    Расписание, каждые 5 минут:
        curl -s "https://granat-kmv.ru/api/watch?token=ТОКЕН&minutes=15"
    """
    token = os.getenv("WATCH_TOKEN", "").strip()
    if not token or request.args.get("token", "") != token:
        return jsonify(ok=False, error="forbidden"), 403

    try:
        minutes = int(request.args.get("minutes", "15"))
    except ValueError:
        minutes = 15

    items = leads.pending(minutes)
    sent = 0
    for it in items:
        lines = [
            f"⏳ ЗАЯВКА №{it['id']} — клиент не дошёл до бота",
            "",
            f"Прошло: {it.get('age_min', '?')} мин",
        ]
        if it.get("name"):
            lines.append(f"👤 {it['name']}")
        phone = it.get("phone") or it.get("contact") or ""
        if phone:
            lines.append(f"📞 {phone}")
        if it.get("service"):
            lines.append(f"🛍 {it['service']}")
        chk = leads.cheque(it)
        if chk:
            lines.append(f"💰 Собрал: {chk}")
        if it.get("notes"):
            lines.append(f"📝 {it['notes']}")
        lines.append("")
        lines.append("Позвони сама — бот написать первым не может.")

        ok_send, _ = bots.send_admin("\n".join(lines))
        if ok_send:
            leads.mark_alerted(it["id"])
            sent += 1

    return jsonify(ok=True, alerted=sent, found=len(items), minutes=minutes)


@app.route("/api/pending")
def pending_leads():
    """Для Генерала: заявки, где клиент не дошёл до бота.

    Защищено токеном — иначе список контактов клиентов открыт всему интернету.
    Задай WATCH_TOKEN в переменных Amvera и дёргай так:
        /api/pending?token=...&minutes=15
    """
    token = os.getenv("WATCH_TOKEN", "").strip()
    if not token or request.args.get("token", "") != token:
        return jsonify(ok=False, error="forbidden"), 403
    try:
        minutes = int(request.args.get("minutes", "15"))
    except ValueError:
        minutes = 15
    items = leads.pending(minutes)
    return jsonify(ok=True, count=len(items), minutes=minutes, leads=items)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
