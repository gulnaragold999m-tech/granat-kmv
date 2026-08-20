import os
import json
import smtplib
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests
from flask import (Flask, send_from_directory, request, jsonify, redirect,
                   render_template, Response)

import bots
import contact
import leads
import uslugi

# Цены для страниц услуг. Читаются один раз при старте: файл собирается
# командой `npm run sajt-ceny` из data/prices.ts, и в рантайме не меняется.
# Нет файла — страницы услуг всё равно открываются, просто без таблиц:
# сайт не должен падать из-за несобранного прайса.
try:
    with open("ceny.json", encoding="utf-8") as _f:
        CENY_STRANIC = json.load(_f)
except (OSError, ValueError) as _e:
    print("ceny.json не прочитан (%s) — таблицы цен на страницах услуг скрыты" % _e)
    CENY_STRANIC = {}

# ── TELEGRAM СНЯТ 15.08.2026 ─────────────────────────────────────────────
# Решение владелицы, её словами: «Телеграм как трафик для заявок снимаем.
# У меня телеграм не работает — я вижу, когда приходит информация, но
# открыть не могу».
#
# Канал, до которого нельзя дотянуться, хуже отсутствующего: заявка
# считается доставленной, счётчик недоставленных молчит, а прочитать её
# нельзя. Поэтому Telegram убран из доставки целиком, а не «отключён
# на время».
#
# Что осталось: ВКонтакте и почта — два независимых канала. Плюс журнал
# на диске, он пишется ДО всякой отправки, поэтому заявка не теряется,
# даже когда молчат оба.
#
# Что убрано: отправка в Telegram, кнопка «Продолжить в Telegram» на
# экране «заявка принята», приглашение Джарвиса и доклад сторожа
# тишины в Telegram. Сторож теперь пишет туда же, куда заявки.

# Разбор мошеннических текстов общий с ботом. Здесь он нужен не для отказа, а
# для пометки в заявке: решение по клиенту всегда принимает человек.
try:
    import fraud_check
except Exception as e:  # noqa: BLE001
    fraud_check = None
    print(f"[init] проверка на мошенников не подключилась: {e}", flush=True)

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

# TELEGRAM_BOT_TOKEN и ADMIN_CHAT_ID больше не читаются: сайт в Telegram
# не пишет. Переменные в Amvera можно оставить — они нужны приложению
# Джарвиса, оно живёт отдельно.

# Постоянное хранилище Amvera: заявка ложится сюда, даже если Telegram молчит.
ORDERS_FILE = "/data/orders.jsonl"

# Макеты, приложенные к заявке из секретаря. Лежат на диске рядом с журналом
# заявок: письмо может не уйти, а файл клиента терять нельзя ни при каких
# обстоятельствах — он единственный экземпляр.
MAKETY_DIR = "/data/makety"

# Предел на весь запрос. Больше 20 МБ через форму на сайте не принимаем:
# такие файлы и почтой не уходят, а Flask без этого предела читает тело
# целиком в память и кладёт контейнер.
MAX_MAKET = 20 * 1024 * 1024

# Ставим предел ЗДЕСЬ, а не рядом с созданием app: Python читает файл сверху
# вниз, и там MAX_MAKET ещё не объявлен. 17.08.2026 сайт из-за этого не
# поднимался двадцать минут — NameError на 74-й строке, gunicorn падал
# в цикле. Ошибка не ловится ни глазами, ни `python -c "import ast"`:
# синтаксис верный, порядок неверный.
app.config["MAX_CONTENT_LENGTH"] = MAX_MAKET + 1024 * 1024  # запас на поля формы

# Расширения, которые принимаем от клиента. Список белый, а не чёрный:
# запрещать по одному бесполезно, разрешать по одному — надёжно.
# .html и .svg сюда НЕ входят намеренно: они исполняются в браузере,
# а файлы лежат на том же домене.
MAKET_RASSHIRENIYA = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic",
    ".ai", ".eps", ".psd", ".cdr", ".zip", ".rar", ".doc", ".docx",
}

# Контейнер живёт по Гринвичу, а смотреть на заявки нам по-московски.
TZ = ZoneInfo("Europe/Moscow")


def now_msk():
    """Московское время без пометки о зоне — чтобы в файле было понятно
    и сравнение со старыми записями не ломалось."""
    return datetime.now(TZ).replace(tzinfo=None)

OLD_HOST = "granat-site-granatgold999.amvera.io"
NEW_DOMAIN = "https://granat-kmv.ru"


def mask(s):
    """Осталась от телеграмного токена: раньше прятала его из логов.
    Сейчас прятать нечего, но вызовы по коду оставлены — если однажды
    появится новый секрет, прятать его будут здесь, в одном месте."""
    return s


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

# Куда уводить клиента после заявки. Ссылки
# ведут в переписку с нами, а не на страницу сообщества: цель — чтобы
# человек написал, а не полистал ленту.
VK_WRITE_LINK = os.getenv("VK_WRITE_LINK", "https://vk.me/club238836731").strip()
WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "https://wa.me/79992449999").strip()

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


def auth_reason(err):
    """Человеческая причина отказа на входе в почту + дословный ответ сервера.

    Раньше здесь стояла одна фраза «нужен пароль приложения». Она верна для
    самого частого случая, но 09.08.2026 пароль приложения уже был заведён,
    а вход всё равно отклонялся — и по нашей же фразе понять это было
    нельзя. Ответ Яндекса различает причины, поэтому кладём его целиком.
    """
    detail = getattr(err, "smtp_error", b"") or b""
    if isinstance(detail, bytes):
        detail = detail.decode("utf-8", "replace")
    detail = " ".join(str(detail).split())[:200]

    return mask(
        "вход отклонён. Проверьте: 1) в MAIL_PASSWORD лежит пароль приложения "
        "из Яндекс ID, а не пароль от почты; 2) в MAIL_LOGIN — полный адрес "
        "ящика; 3) в настройках почты разрешён доступ почтовым программам. "
        f"Ответ сервера: {detail}"
    )


def send_to_mail(subject, text, vlozhenie=None):
    """Дубль заявки письмом. Возвращает (ok, причина).

    `vlozhenie` — кортеж (имя_файла, байты) с макетом клиента, если он его
    приложил. Заведено 17.08.2026: до этого человек доходил до конца
    диалога, оставлял телефон — и упирался в вопрос «а куда макет».
    Файл уходил отдельным письмом без параметров заказа, и связать их
    было нечем. Ровно так потерялся заказ 16.08.

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

    if vlozhenie:
        imya, bajty = vlozhenie
        # Тип не разбираем: почтовым клиентам хватает octet-stream, а угадывать
        # по расширению — лишний повод ошибиться на .cdr и .psd.
        msg.add_attachment(bajty, maintype="application", subtype="octet-stream",
                           filename=imya)

    try:
        with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT,
                              context=ssl.create_default_context(),
                              timeout=15) as s:
            s.login(MAIL_LOGIN, MAIL_PASSWORD)
            s.send_message(msg)
        return True, ""
    except smtplib.SMTPAuthenticationError as e:
        reason = auth_reason(e)
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
    except smtplib.SMTPAuthenticationError as e:
        return auth_reason(e)
    except Exception as e:
        return mask(f"{type(e).__name__}: {e}")


# Рассылка живёт в фоне, поэтому пул общий и создаётся один раз. Заводить
# его на каждую заявку — значит платить за создание потоков ровно в тот
# момент, когда клиент ждёт ответа.
NOTIFY_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="notify")

# Сколько секунд держим клиента, пока каналы отвечают. Уложились — скажем
# правду: дошло или не дошло. Не уложились — отпускаем с «заявка принята»,
# она к этому моменту уже лежит на диске, а рассылка доедет без него.
NOTIFY_WAIT = 6


def deliver(subject, text, vlozhenie=None):
    """Разослать заявку по обоим каналам сразу. Возвращает две пары (ok, причина).

    Каналы независимы, поэтому ждать их по очереди незачем: одновременно
    ждём самый медленный, а не сумму. Ответы забираем полностью — заявка
    должна попасть в журнал с честными отметками по каждому каналу,
    иначе счётчик недоставленных снова начнёт врать.

    Каналов было три, Telegram снят 15.08.2026 — см. заметку в начале файла.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        vk = pool.submit(send_to_vk, text)
        # ВКонтакте вложение не отправляем: там для этого нужна отдельная
        # загрузка на их сервер, а канал этот запасной. Про файл в тексте
        # сказано, и он лежит на диске — не потеряется.
        mail = pool.submit(send_to_mail, subject, text, vlozhenie)
        return vk.result(), mail.result()


@app.before_request
def redirect_old_domain():
    if request.host.lower() == OLD_HOST:
        return redirect(NEW_DOMAIN + request.full_path.rstrip("?"), code=301)


@app.before_request
def tolko_https():
    """Незащищённый заход переводим на https.

    Сертификат у домена есть с самого начала, но сайт открывался и по
    http — и человек, набравший «granat-kmv.ru» без приставки, видел
    в браузере «Не защищено». 16.08.2026 на это наткнулись при проверке
    в режиме инкогнито, и это на сайте, который просит телефон: форма
    заявки и секретарь передавали бы его открытым текстом.

    Протокол смотрим в заголовке от прокси Amvera: до приложения запрос
    доходит уже расшифрованным, поэтому request.scheme здесь всегда
    «http» и доверять ему нельзя.

    Локальный запуск (127.0.0.1, localhost) не трогаем — там сертификата
    нет и редирект сделал бы сайт недоступным для разработки.
    """
    proto = request.headers.get("X-Forwarded-Proto", "")
    host = request.host.split(":")[0].lower()
    mestnyj = host in ("127.0.0.1", "localhost") or host.startswith("192.168.")
    if proto == "http" and not mestnyj:
        return redirect("https://" + request.host + request.full_path.rstrip("?"),
                        code=301)


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


@app.route("/pechat/<slug>")
def stranica_uslugi(slug):
    """Страница одной услуги.

    Заведено 21.08.2026. До этого пятнадцать услуг прайса жили на одной
    странице /pechat, и она не могла ранжироваться ни по одному запросу
    как следует: у человека с фото на паспорт и у человека с чертежом А0
    разные запросы и разные ожидания.

    Маршрут один на все услуги, описания лежат в uslugi.py. Новая
    услуга — это запись в словаре, а не правка этого файла.
    """
    dannye = uslugi.usluga(slug)
    if dannye is None:
        return render_template("404.html"), 404
    return render_template(
        "usluga.html",
        u=dannye,
        slug=slug,
        ceny=CENY_STRANIC,
        drugie=[x for x in uslugi.spisok() if x["slug"] != slug],
    )


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
    """Карта сайта СОБИРАЕТСЯ, а не лежит файлом.

    До 21.08.2026 здесь стояла отдача файла с диска. Файла этого
    в репозитории не было вовсе — то есть либо он жил только в Amvera
    и терялся при любой чистой выкатке, либо адрес отдавал 404
    и поисковик не получал карту сайта совсем.

    Собранная карта не может устареть: добавили страницу услуги
    в uslugi.py — она появилась в карте сама.
    """
    adresa = ["/", "/pechat", "/cifra", "/raboty", "/kak-rabotaem", "/kontakty"]
    adresa += ["/pechat/" + u["slug"] for u in uslugi.spisok()]
    segodnya = datetime.now().strftime("%Y-%m-%d")
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for a in adresa:
        xml.append("  <url><loc>https://granat-kmv.ru%s</loc>"
                   "<lastmod>%s</lastmod></url>" % (a, segodnya))
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    """robots.txt собирается тут же и по той же причине, что и карта сайта:
    файла на диске не было, а отсутствующий robots.txt — это 404 на адресе,
    который робот запрашивает первым делом.

    ИИ-краулеры намеренно НЕ закрыты: страницы студии должны попадать
    в ответы нейропоиска, а закрытый доступ обнуляет эту возможность."""
    return Response(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://granat-kmv.ru/sitemap.xml\n",
        mimetype="text/plain",
    )


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
    """Самопроверка: жив ли сайт и принимают ли нас ВКонтакте и почта.

    Никому ничего не отправляет — дёргать можно хоть каждые пять минут.

    ГЛАВНОЕ ПОЛЕ — `ok`. Оно означает: есть ли хотя бы один живой канал,
    по которому заявка до Гульнары дойдёт. Каналов теперь два, и если
    оба молчат, заявка ляжет только на диск, а знать об этом будет
    некому. Поэтому `ok` считается по ним обоим, а не по одному.
    """
    # Проверки не зависят друг от друга, поэтому идут одновременно —
    # иначе на медленной почте вся страница проверки ждала бы её одну.
    with ThreadPoolExecutor(max_workers=3) as pool:
        vk_state = pool.submit(vk_health)
        mail_state = pool.submit(mail_health)
        bots_state = pool.submit(bots.health)

    vk_ok = vk_state.result()
    mail_ok = mail_state.result()

    return jsonify(
        ok=(vk_ok == "ok" or mail_ok == "ok"),
        undelivered=count_undelivered(),
        vk=vk_ok,
        mail=mail_ok,
        # Под каким адресом ходим на почту. Не секрет — он и так на странице
        # контактов, зато опечатка в переменной видна сразу, без похода в
        # панель хостинга.
        mail_login=MAIL_LOGIN or "не задан",
        # Telegram снят с сайта 15.08.2026. Строчка оставлена нарочно:
        # без неё непонятно, снят он осознанно или отвалился.
        telegram="снят с сайта 15.08.2026",
        # Джарвис живёт отдельным приложением и в Telegram остаётся —
        # показываем его состояние справочно.
        bots=bots_state.result(),
    )


def follow_up(channel, lead_id, name):
    """Куда позвать клиента дальше — в тот канал, который он выбрал сам.

    В Telegram не зовём с 15.08.2026: Гульнара его не открывает, и клиент,
    ушедший туда, остался бы без ответа. Остались ВКонтакте и WhatsApp.

    ВКонтакте — основной выход: он работает из России без обхода
    блокировок. WhatsApp даём тем, кто сам его выбрал, и подстраховываем
    ссылкой на ВК: 09.08.2026 сообщение в WhatsApp ушло с одной галочкой
    и не дошло, а сервер об этом не узнает никогда.

    Возвращает словарь для браузера.
    """
    vk_exit = {
        "url": VK_WRITE_LINK,
        "label": "Написать во ВКонтакте →",
        "note": "Напишите нам в сообщения сообщества — ответим там же, "
                f"по заявке №{lead_id}.",
    }

    if channel == "WhatsApp":
        text = (f"Здравствуйте! Я оставил заявку №{lead_id} на сайте "
                f"granat-kmv.ru")
        if name:
            text += f". Меня зовут {name}"
        return {
            "url": f"{WHATSAPP_LINK}?text={quote(text)}",
            "label": "Написать в WhatsApp →",
            "note": "Сообщение уже готово — останется нажать «отправить».",
            "fallback": {
                "url": VK_WRITE_LINK,
                "label": "Не отправляется? Написать во ВКонтакте",
            },
        }

    return vk_exit


@app.route("/api/order", methods=["POST"])
def order():
    data = request.get_json(silent=True) or request.form or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(ok=False, field="name", error="Укажите имя"), 400

    service = (data.get("service") or "").strip()
    notes = (data.get("notes") or "").strip()

    # Канал связи клиент выбирает прямо в форме. Telegram с 15.08.2026
    # не предлагаем — но старая страница может остаться у человека
    # в кэше браузера и прислать его. Тогда считаем, что канал не выбран:
    # обещать ответ там, куда мы не смотрим, нельзя.
    _CHANNELS = {"whatsapp": "WhatsApp", "vk": "VK", "вконтакте": "VK"}
    raw_channel = (data.get("preferred_channel") or "").strip().lower()
    channel = _CHANNELS.get(raw_channel, "")

    # Контакт разбираем до записи заявки. Поле принимает и телефон, и ник в
    # Telegram, и до 10.08.2026 принимало заодно пять цифр и пустые пробелы:
    # заявка ложилась в журнал, а связаться было нечем. Ошибку возвращаем с
    # именем поля — по нему форма покажет подсказку у нужной строки, а не
    # уведёт клиента в запасные кнопки, будто заявка принята.
    raw_phone = (data.get("phone") or "").strip()
    got = contact.parse(raw_phone)
    if got["error"]:
        return jsonify(ok=False, field="phone", error=got["error"]), 400

    # Ник в Telegram больше не принимаем как единственный контакт: с
    # 15.08.2026 мы в Telegram не пишем, и связаться по нику будет нечем.
    # Заявка с одним ником — это заявка, на которую нельзя ответить.
    if got["kind"] == "username":
        return jsonify(ok=False, field="phone",
                       error="Оставьте, пожалуйста, номер телефона: "
                             "мы отвечаем звонком, в WhatsApp или "
                             "во ВКонтакте. " + contact.HINT_PHONE), 400

    phone = got["value"]
    payload = {"name": name, "phone": phone, "service": service, "notes": notes,
               "preferred_channel": channel, "contact_kind": got["kind"]}
    if raw_channel == "telegram":
        # Видно в заявке: человек просил Telegram, а мы туда не пишем.
        # Значит звоним или пишем в WhatsApp по номеру.
        payload["prosil_telegram"] = True
    # Что человек напечатал на самом деле — оставляем, если привели к другому
    # виду: пригодится, когда номер вдруг окажется неверным.
    if raw_phone != phone:
        payload["phone_raw"] = raw_phone

    # Оценка риска — строчка для Гульнары, а не приговор заявке. Заявка уходит
    # в любом случае: у типографии с предоплатой подставная заявка ничего не
    # крадёт, а отклонённый по ошибке живой клиент — прямой убыток. Ловим
    # ровно одно: схемы, обращённые к самой студии, — «переплатил, верните
    # разницу» и ссылки-подделки «для получения оплаты».
    risk = fraud_check.analyze(f"{service} {notes}") if fraud_check else None
    if risk and risk["flags"]:
        payload["risk_level"] = risk["level"]
        payload["risk_flags"] = [title for title, _why in risk["flags"]]

    # Номер нужен, чтобы Джарвис узнал клиента, когда тот придёт в бота,
    # и чтобы Генерал мог сказать «заявка №47 висит без ответа».
    lead_id = leads.next_id()
    payload["lead"] = lead_id
    leads.log(lead_id, "created", source="site_form", **payload)

    lines = [f"🔔 НОВАЯ ЗАЯВКА С САЙТА №{lead_id}", "", f"👤 Имя: {name}"]
    if phone:
        label = "Ник в Telegram" if got["kind"] == "username" else "Телефон"
        lines.append(f"📞 {label}: {contact.pretty(phone)}")
    if channel:
        icon = {"Telegram": "✈️", "WhatsApp": "🟢", "VK": "🔵"}.get(channel, "💬")
        lines.append(f"{icon} Писать в: {channel}")
    if service:
        lines.append(f"🛍 Услуга: {service}")
    if notes:
        lines.append(f"📝 Пожелания: {notes}")

    if risk and risk["flags"]:
        lines.append("")
        lines.append("⚠️ В тексте заявки есть тревожные признаки:")
        lines += [f"  • {title}" for title, _why in risk["flags"][:3]]
        if risk["level"] == "danger":
            lines.append("  Деньги вперёд не отправлять, по ссылкам не ходить.")

    lines.append("")
    lines.append("Ждём клиента в боте для сбора ТЗ.")

    # ── 1. ГЕНЕРАЛ докладывает Гульнаре ──────────────────────────────────
    # Три канала одновременно. Заявка считается доставленной, если её принял
    # хотя бы один: отказ одного канала больше не теряет клиента.
    #
    # Рассылка идёт в фоне, и это главное. Раньше браузер ждал, пока все три
    # мессенджера ответят, — а если один тормозил, кнопка «Отправляем...»
    # висела до минуты, и клиент уходил, не увидев ни номера заявки, ни
    # ссылки в бота. При этом заявка уже лежала на диске: leads.log выше
    # записывает её до всякой отправки, так что потерять её нельзя.
    text = "\n".join(lines)

    def notify():
        """Разослать заявку по каналам и записать результат. Возвращает,
        дошла ли она хоть куда-нибудь."""
        (vk_ok, vk_reason), (mail_ok, mail_reason) = deliver(
            f"Заявка с сайта №{lead_id} — {name}", text
        )
        delivered = vk_ok or mail_ok
        save_order(payload, delivered=delivered,
                   reason="" if delivered else
                          f"вк: {vk_reason}; почта: {mail_reason}")
        leads.log(lead_id, "notified", delivered=delivered,
                  vk=vk_ok, mail=mail_ok)
        if not delivered:
            print(f"[order] заявка №{lead_id} сохранена, но не доставлена: "
                  f"вк: {vk_reason}; почта: {mail_reason}", flush=True)
        return delivered

    # ── 2. ДЖАРВИС ───────────────────────────────────────────────────────
    # Приглашение в Джарвиса убрано 15.08.2026 вместе с Telegram: бот живёт
    # только там, а собранное им ТЗ приходило Гульнаре тоже в Telegram —
    # то есть туда, куда она не смотрит. Клиента ведём в ВК или WhatsApp,
    # а вопросы по задаче задаёт человек.
    #
    # Сам бот при этом жив и стоит отдельным приложением: если Telegram
    # у Гульнары заработает, вернуть приглашение — это вернуть вызов
    # bots.send_client сюда же.

    job = NOTIFY_POOL.submit(notify)

    try:
        delivered = job.result(timeout=NOTIFY_WAIT)
    except FuturesTimeout:
        # Каналы ещё думают. Не держим клиента: заявка у нас, а результат
        # рассылки допишется в журнал, когда придёт.
        delivered = None

    if delivered is False:
        # Оба канала молчат — делать вид, что всё хорошо, нельзя.
        # Браузер покажет кнопки, чтобы клиент отправил заявку сам.
        return jsonify(ok=False, saved=True, error="not_delivered"), 200

    # Заявка у нас — дальше зовём клиента туда, где мы отвечаем.
    # Поле `tg` из ответа убрано вместе с Telegram: страницы, которые
    # его читали, поправлены в шаблонах.
    answer = {"ok": True, "lead": lead_id, "next": follow_up(channel, lead_id, name)}
    return jsonify(**answer)


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
        return jsonify(ok=False, error="Укажите номер телефона"), 400

    path = data.get("path") or []
    # Из формы с файлом путь приходит строкой JSON: FormData массивы не умеет.
    if isinstance(path, str):
        try:
            razobrano = json.loads(path)
            path = razobrano if isinstance(razobrano, list) else [path]
        except (ValueError, TypeError):
            path = [path]
    route_text = " → ".join(str(p) for p in path if str(p).strip())

    # ── Макет, если клиент его приложил ──────────────────────────────────
    #
    # Сохраняем на диск ДО всякой отправки — тем же правилом, что и заявку:
    # почта может молчать, а файл клиента единственный, второй раз он его
    # не пришлёт.
    maket_imya, maket_bajty, maket_zametka = "", None, ""
    fajl = request.files.get("maket")
    if fajl and fajl.filename:
        # Браузеры на Windows иногда шлют полный путь с обратными слешами,
        # а os.path.basename на Linux их за разделитель не считает — имя
        # выходило вроде «CUsersАняграмота.jpg».
        ish = os.path.basename(fajl.filename.replace("\\", "/"))
        rasshirenie = os.path.splitext(ish)[1].lower()
        if rasshirenie not in MAKET_RASSHIRENIYA:
            maket_zametka = f"файл {ish} не принят: расширение {rasshirenie or 'без расширения'}"
        else:
            bajty = fajl.read(MAX_MAKET + 1)
            if len(bajty) > MAX_MAKET:
                maket_zametka = f"файл {ish} не принят: больше {MAX_MAKET // 1024 // 1024} МБ"
            else:
                # Имя клиента в имя файла на диске не берём: там бывает что
                # угодно, вплоть до путей. Своё имя, а клиентское — в письме.
                bezopasnoe = "".join(c for c in ish if c.isalnum() or c in " .-_()").strip()
                maket_imya = bezopasnoe or ("maket" + rasshirenie)
                maket_bajty = bajty
                try:
                    os.makedirs(MAKETY_DIR, exist_ok=True)
                except OSError as e:
                    print(f"[maket] не создать папку: {e}", flush=True)

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

    # Кладём файл на диск под номером заявки: так его находят по заявке,
    # не разбирая, кто из клиентов какой «scan1.pdf» прислал.
    if maket_bajty is not None:
        put_na_diske = os.path.join(MAKETY_DIR, f"{lead_id}_{maket_imya}")
        try:
            with open(put_na_diske, "wb") as f:
                f.write(maket_bajty)
            payload["maket"] = put_na_diske
        except OSError as e:
            maket_zametka = f"файл {maket_imya} не сохранён на диск: {e}"
            print(f"[maket] {maket_zametka}", flush=True)
    if maket_zametka:
        payload["maket_zametka"] = maket_zametka

    leads.log(lead_id, "created", **payload)

    # ── ГЕНЕРАЛ докладывает ──────────────────────────────────────────────
    lines = [f"🤖 ЗАЯВКА ИЗ СИМУЛЯТОРА №{lead_id}", "", f"📞 Контакт: {contact}"]
    if route_text:
        lines.append(f"🧭 Собрал: {route_text}")
    if total:
        lines.append("💰 На сумму: {:,} ₽".format(total).replace(",", " "))
    if maket_bajty is not None:
        lines.append(f"📎 Макет приложен к письму: {maket_imya}")
    elif maket_zametka:
        lines.append(f"⚠️ {maket_zametka} — попросите прислать другим способом")
    lines.append("")
    lines.append("Ждём клиента в боте для сбора ТЗ.")

    # Все каналы сразу и в фоне — как и в заявке с формы выше. Симулятор
    # ждал ответа всех трёх наравне с формой, значит и висел так же.
    text = "\n".join(lines)

    def notify():
        (vk_ok, vk_reason), (mail_ok, mail_reason) = deliver(
            f"Заявка из симулятора №{lead_id}", text,
            vlozhenie=(maket_imya, maket_bajty) if maket_bajty is not None else None
        )
        delivered = vk_ok or mail_ok
        save_order(payload, delivered=delivered,
                   reason="" if delivered else
                          f"вк: {vk_reason}; почта: {mail_reason}")
        leads.log(lead_id, "notified", delivered=delivered,
                  vk=vk_ok, mail=mail_ok)
        if not delivered:
            print(f"[bot-lead] заявка №{lead_id} сохранена, но не доставлена: "
                  f"вк: {vk_reason}; почта: {mail_reason}", flush=True)
        return delivered

    # Приглашение Джарвиса убрано 15.08.2026 вместе с Telegram — причина
    # та же, что и в заявке с формы выше.

    job = NOTIFY_POOL.submit(notify)

    try:
        delivered = job.result(timeout=NOTIFY_WAIT)
    except FuturesTimeout:
        delivered = None

    if delivered is False:
        return jsonify(ok=False, saved=True, error="not_delivered",
                       lead=lead_id, next=follow_up("", lead_id, "")), 200

    return jsonify(ok=True, lead=lead_id, next=follow_up("", lead_id, ""))


@app.route("/api/watch")
def watch():
    """Сторож тишины. Дёргается по расписанию — Amvera → Cron Jobs.

    Находит заявки, на которые никто не ответил, и шлёт Гульнаре
    напоминание с телефоном: перехватить вручную, пока человек тёплый.
    Про каждую заявку говорит один раз — сторож, повторяющий одно и то же,
    перестаёт читаться.

    С 15.08.2026 докладывает туда же, куда уходят заявки — во ВКонтакте
    и на почту. Раньше он писал в Telegram, а значит с этого дня кричал
    бы в пустоту: заявка без ответа висела бы молча.

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
            f"⏳ ЗАЯВКА №{it['id']} — без ответа",
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
        lines.append("Позвоните сами — клиент ждёт.")

        (vk_ok, _vk_why), (mail_ok, _mail_why) = deliver(
            f"Заявка №{it['id']} без ответа", "\n".join(lines)
        )
        if vk_ok or mail_ok:
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


# ── Мостик к Джарвису ───────────────────────────────────────────────────
# Джарвис — отдельное приложение Amvera со своим диском. Журнал заявок
# лежит на диске сайта, и заглянуть в него бот не может: у каждого
# приложения своё /data. Поэтому заявка ходит между ними по сети.
#
# Без этого ссылка «Продолжить в Telegram» несла номер заявки, который
# боту было негде посмотреть, — и он спрашивал всё заново у человека,
# только что заполнившего форму.
#
# Защищено тем же WATCH_TOKEN, что и /api/pending: в заявке лежат имя и
# телефон клиента, отдавать их кому попало нельзя.
# В переменных Джарвиса задай SITE_URL и SITE_TOKEN.

def _token_ok():
    token = os.getenv("WATCH_TOKEN", "").strip()
    return bool(token) and request.args.get("token", "") == token


@app.route("/api/lead/<int:lead_id>")
def lead_read(lead_id):
    """Отдать Джарвису заявку по номеру."""
    if not _token_ok():
        return jsonify(ok=False, error="forbidden"), 403
    lead = leads.find(lead_id)
    if not lead:
        return jsonify(ok=False, error="not_found"), 404
    return jsonify(ok=True, lead=lead)


@app.route("/api/lead/<int:lead_id>/event", methods=["POST"])
def lead_event(lead_id):
    """Принять от Джарвиса отметку о ходе заявки.

    entered_bot — клиент дошёл до бота, запоминаем его chat_id: со
    следующего раза Джарвис напишет ему первым.
    postponed   — нажал «Позже».
    brief_ready — ТЗ собрано, сторож тишины может о заявке забыть.
    """
    if not _token_ok():
        return jsonify(ok=False, error="forbidden"), 403

    data = request.get_json(silent=True) or {}
    event = (data.get("event") or "").strip()

    if event == "entered_bot":
        leads.link_client(
            lead_id,
            data.get("chat_id"),
            phone=(data.get("phone") or ""),
            username=(data.get("username") or ""),
        )
    elif event == "postponed":
        leads.log(lead_id, "postponed")
    elif event == "brief_ready":
        leads.log(lead_id, "brief_ready", brief=(data.get("brief") or "")[:2000])
    else:
        # Чужие события в журнал не пускаем: он читается сторожем и
        # счётчиками, и мусор в нём стоит дороже отказа.
        return jsonify(ok=False, error="unknown_event"), 400

    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
