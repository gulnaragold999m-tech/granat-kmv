import os
import hashlib
import hmac
import json
import re
import smtplib
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo

import requests
from flask import (Flask, send_from_directory, request, jsonify, redirect,
                   render_template)

import bots
import contact
import leads

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

# Адрес с косой чертой на конце и без неё — одна и та же страница.
# Без этой строки Flask отдаёт 404 на `/sertifikaty/`, хотя `/sertifikaty`
# открывается. 19.08.2026 на это налетел проверяльщик ссылок Яндекс
# Бизнеса: адрес страницы товара он не принял со словами «добавьте
# корректную ссылку». Люди тоже дописывают слеш по привычке, и терять
# на этом посетителя из Карт — дорогое удовольствие.
app.url_map.strict_slashes = False

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
#
# Сколько файлов берём за одну заявку. Четыре — это лицо и оборот
# листовки, три панели буклета или обложка с разворотом. Предел нужен
# не для порядка, а чтобы папка со свадебными фотографиями не приехала
# к нам целиком: контейнер читает тело в память.
MAX_MAKETOV = 4

app.config["MAX_CONTENT_LENGTH"] = MAX_MAKET * MAX_MAKETOV + 1024 * 1024  # запас на поля формы

# Расширения, которые принимаем от клиента. Список белый, а не чёрный:
# запрещать по одному бесполезно, разрешать по одному — надёжно.
# .html и .svg сюда НЕ входят намеренно: они исполняются в браузере,
# а файлы лежат на том же домене.
MAKET_RASSHIRENIYA = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic",
    ".ai", ".eps", ".psd", ".cdr", ".zip", ".rar", ".doc", ".docx",
}

# ── Свой номер в заявке — это проверка, а не клиент ──────────────────────
#
# 18.08.2026 владелица сказала: «у нас уже 27-я заявка, а по сути только
# одна». Каждая проверка секретаря забирала номер, и по номеру заявки
# нельзя было понять, сколько людей на самом деле обратилось.
#
# Обнулять счётчик нельзя: номера уже стоят в журнале и в именах файлов
# с макетами на диске, повтор номера склеит два разных заказа. Поэтому
# не обнуляем, а перестаём тратить: заявка со СВОЕГО телефона номера
# не получает и в журнал заявок не ложится. Письмо приходит с пометкой,
# чтобы проверку было видно сразу.
TEST_PHONES = {"79992449999"}
_dop_test = os.getenv("TEST_PHONES", "")
for _t in _dop_test.split(","):
    _cifry = "".join(c for c in _t if c.isdigit())
    if _cifry:
        TEST_PHONES.add(_cifry)


def eto_proverka(stroka) -> bool:
    """Заявка со своего номера. Восьмёрку приводим к семёрке: в форму
    вводят и так, и так, а телефон это один и тот же."""
    cifry = "".join(c for c in str(stroka or "") if c.isdigit())
    if len(cifry) == 11 and cifry.startswith("8"):
        cifry = "7" + cifry[1:]
    return cifry in TEST_PHONES


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

    `vlozhenie` — СПИСОК кортежей (имя_файла, байты) с макетами клиента.
    Одиночный кортеж тоже принимается: так вызывали раньше, и ломать
    старые вызовы ради красоты незачем.

    Список, а не один файл, — с 18.08.2026. Поле принимало ровно один
    макет, а у листовки две стороны, и клиентка написала прямо: «там
    загружается только одна картинка, а мне нужно отправить две
    стороны». Она прислала лицо, была уверена, что отправила обе, —
    и печатать было нечего. Форма молчала об этом, а выяснилось через
    сутки.

    Заведено 17.08.2026: до этого человек доходил до конца
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
        # Одиночный кортеж приводим к списку: старые вызовы передавали
        # именно его, и падать на них нельзя.
        spisok = vlozhenie if isinstance(vlozhenie, list) else [vlozhenie]
        for imya, bajty in spisok:
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


# ── Что можно отдавать из корня ─────────────────────────────────────────
# ЗАЧЕМ. Flask поднят с static_folder="." (см. начало файла), поэтому из
# корня наружу уходит ВСЁ, что там лежит, — а лежит там сама программа.
# 21.08.2026 проверкой с чужого компьютера скачались app.py, leads.py,
# bots.py, contact.py, fraud_check.py, amvera.yaml, .env.example, журнал
# работ и папка .git целиком. Ключей в файлах нет, они читаются из
# переменных Amvera, — но наружу ушло устройство сайта и все 45 КБ
# правил проверки мошенников. Правила, которые видно, обходятся.
#
# Разрешаем по списку, а не запрещаем по списку: новый служебный файл
# в корне появится рано или поздно, и он не должен открыться сам собой.
# Адреса страниц (/pechat, /api/health) сюда не попадают — у них нет
# расширения, и они уходят дальше, в маршруты.
MOZHNO_OTDAVAT = (
    ".html", ".htm", ".css", ".js", ".map",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico", ".avif",
    ".xml", ".webmanifest", ".pdf", ".mp4", ".woff", ".woff2", ".ttf",
)
# Из .txt наружу нужен ровно один файл — его просит поисковик.
MOZHNO_TXT = {"robots.txt"}


@app.before_request
def ne_otdavat_sluzhebnoe():
    """Служебные файлы и папку .git наружу не отдаём."""
    put = request.path.lstrip("/")
    if not put:
        return None

    # .git, .env, .htaccess — любой файл или папка, начинающиеся с точки.
    if any(chast.startswith(".") for chast in put.split("/")):
        return "Not Found", 404

    nizhnij = put.lower()
    if nizhnij.endswith(".txt"):
        return None if nizhnij in MOZHNO_TXT else ("Not Found", 404)

    # Расширения нет — это адрес страницы, а не файл: пропускаем дальше.
    imya = nizhnij.rsplit("/", 1)[-1]
    if "." not in imya:
        return None

    if not nizhnij.endswith(MOZHNO_OTDAVAT):
        return "Not Found", 404


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


# ── Отзывы с Яндекс Карт ────────────────────────────────────────────────
# ЗАЧЕМ. Отзывы клиенты уже написали, но видит их только тот, кто дошёл до
# Яндекс Карт. На сайте они работают как доказательство: человек читает их
# там же, где решает, заказывать или нет.
#
# Показываем официальным виджетом Яндекса, а не своим списком. Свой список
# — это слова студии о самой себе: написать в нём можно что угодно, и цена
# такому ноль. Виджет рисует Яндекс из своей базы: и оценка, и число
# отзывов там те же, что в справочнике, подделать их нельзя.
#
# ЧТО СЮДА КЛАСТЬ. Годится любое из трёх:
#   1. Код виджета из кабинета Яндекс Бизнеса: Отзывы → Виджет отзывов →
#      «Скопировать код». Лучший вариант: отзывы видны прямо на странице.
#   2. Один номер карточки из этого кода.
#   3. Ссылка на карточку в Яндекс Картах, в том числе короткая вида
#      yandex.ru/maps/-/XXXXXXXX. Номера в ней нет, поэтому виджет
#      не собрать — блок покажет заголовок и кнопку на карточку.
#
# ГДЕ ЗАДАТЬ. Проще всего переменной приложения в Amvera: granat-site →
# Переменные окружения → YANDEX_REVIEWS. Тогда файл заново загружать
# не нужно, хватит перезапуска. Переменная главнее строки ниже.
YANDEX_REVIEWS_CODE = "https://yandex.ru/maps/-/CTFBZ4kK"
YANDEX_REVIEWS = os.getenv("YANDEX_REVIEWS", "").strip() or YANDEX_REVIEWS_CODE.strip()


def yandex_reviews():
    """Адреса виджета и ссылок на карточку. None — если ничего не задано.

    Возвращает `frame` (адрес рамки с отзывами; None, если номер карточки
    неизвестен), `page` — куда идти читать, `add` — куда идти писать.

    Пока не задано ничего, блок отзывов на страницах не рисуется вовсе:
    пустая рамка посреди страницы — дырка в вёрстке и лишний запрос
    к чужому домену.

    Чужой код в страницу как есть не вставляем: вместе с ним приезжают
    чужие размеры, от которых вёрстка разъезжается на телефоне. Берём
    из него только номер карточки, остальное собираем сами.
    """
    raw = YANDEX_REVIEWS
    if not raw:
        return None

    found_src = re.search(r"""src\s*=\s*["']([^"']+)["']""", raw)
    src = (found_src.group(1) if found_src else raw).strip()

    if src.isdigit():
        return reviews_by_org(src)

    if src.startswith("//"):
        src = "https:" + src
    try:
        parts = urlparse(src)
    except ValueError:
        return None

    # Только https и только Яндекс: в рамке посреди страницы не должно
    # оказаться неизвестно что, если код скопировали не оттуда.
    host = (parts.hostname or "").lower()
    if parts.scheme != "https":
        return None
    if host != "yandex.ru" and not host.endswith(".yandex.ru"):
        return None

    # Номер ищем только там, где он действительно номер карточки. Просто
    # «первые цифры в адресе» брать нельзя: в ссылке на карту сначала идёт
    # номер региона, и по нему открылась бы чужая организация.
    found_id = (
        re.search(r"\bid=(\d+)", parts.query)
        or re.search(r"/org/[^/]+/(\d+)", parts.path)
        or re.search(r"/rating-badge/(\d+)", parts.path)
    )
    if found_id:
        return reviews_by_org(found_id.group(1))

    # Номера нет — дали короткую ссылку вида yandex.ru/maps/-/XXXXXXXX.
    # Разворачиваем её сами, в фоне: сервер в интернете, а хозяйка сайта
    # с телефона адресную строку посмотреть не может.
    org = short_link_org(src)
    if org:
        return reviews_by_org(org)

    # Пока не развернулась (или Яндекс не дал развернуть) — отправляем
    # человека на карточку кнопкой. Это честнее, чем показать пустоту.
    return {"frame": None, "page": src, "add": src}


# Что вернула короткая ссылка: номер карточки или пусто. Держим в памяти,
# чтобы не ходить в Яндекс на каждый показ страницы.
_SHORT_LINK = {"url": "", "org": "", "asked": False}


def short_link_org(url):
    """Номер карточки из короткой ссылки. Пусто — пока не развернулась.

    Первый посетитель ждать не должен, поэтому в Яндекс идём в фоновом
    потоке, а страницу отдаём сразу — с кнопкой вместо рамки. Развернётся
    — рамка появится у следующего посетителя.
    """
    if _SHORT_LINK["url"] != url:
        _SHORT_LINK.update({"url": url, "org": "", "asked": False})

    if _SHORT_LINK["org"]:
        return _SHORT_LINK["org"]

    if not _SHORT_LINK["asked"]:
        _SHORT_LINK["asked"] = True
        NOTIFY_POOL.submit(_expand_short_link, url)

    return ""


def _expand_short_link(url):
    """Сходить по короткой ссылке и запомнить номер карточки из адреса."""
    try:
        resp = requests.get(url, timeout=8, allow_redirects=True,
                            headers={"User-Agent": "Mozilla/5.0 (granat-kmv.ru)"})
        where = resp.url or ""
        found = re.search(r"/org/[^/]+/(\d+)", where) or re.search(r"/org/[^/]+/(\d+)", resp.text[:200000])
        if found:
            _SHORT_LINK["org"] = found.group(1)
            print(f"[отзывы] короткая ссылка развернулась, карточка {found.group(1)}", flush=True)
        else:
            print(f"[отзывы] в адресе {where[:120]} номера карточки нет — "
                  f"оставляем кнопку на карточку", flush=True)
    except Exception as e:
        print(f"[отзывы] короткую ссылку развернуть не вышло: {e}", flush=True)


def reviews_by_org(org):
    """Три адреса по номеру карточки: рамка, чтение, написать отзыв.

    Рамку отдаём, только если Яндекс разрешает вставить её к нам. Он
    разрешает не всегда: 21.08.2026 на живом сайте виджет ответил
    ERR_BLOCKED_BY_RESPONSE — то есть страница пришла, но с запретом
    показывать её внутри чужого сайта. На странице получалась белая
    дыра в 560 пикселей под заголовком «Что о нас пишут».

    Не разрешает — вместо рамки кнопка на карточку. Отправить человека
    в Яндекс честнее, чем показать ему пустое место.
    """
    frame = f"https://yandex.ru/maps-reviews-widget/?id={org}"
    return {
        "frame": frame if vidzhet_pustyat(frame) else None,
        "page": f"https://yandex.ru/maps/org/{org}/reviews/",
        "add": f"https://yandex.ru/maps/org/{org}/reviews/?add-review=true",
    }


# Пустит ли Яндекс виджет к нам на страницу. Спрашиваем один раз
# и держим ответ в памяти: на каждый показ страницы в Яндекс не ходим.
_VIDZHET = {"url": "", "mozhno": False, "sprosili": False, "pochemu": "ещё не спрашивали"}


def vidzhet_pustyat(url):
    """True — рамку можно рисовать. Первому посетителю отвечаем «нет».

    Спрашиваем в фоновом потоке: посетитель не должен ждать чужой сервер.
    Пока ответа нет, показываем кнопку — это верный ответ по умолчанию,
    потому что пустая рамка хуже кнопки.
    """
    if _VIDZHET["url"] != url:
        _VIDZHET.update({"url": url, "mozhno": False, "sprosili": False,
                         "pochemu": "ещё не спрашивали"})

    if not _VIDZHET["sprosili"]:
        _VIDZHET["sprosili"] = True
        NOTIFY_POOL.submit(_proverit_vidzhet, url)

    return _VIDZHET["mozhno"]


def _proverit_vidzhet(url):
    """Сходить за виджетом и посмотреть, разрешено ли встраивание."""
    try:
        resp = requests.get(url, timeout=8,
                            headers={"User-Agent": "Mozilla/5.0 (granat-kmv.ru)",
                                     "Referer": NEW_DOMAIN + "/"})
        if resp.status_code != 200:
            _zapisat_vidzhet(False, f"Яндекс ответил {resp.status_code}")
            return

        # X-Frame-Options: DENY или SAMEORIGIN — это и есть запрет,
        # который браузер показывает как ERR_BLOCKED_BY_RESPONSE.
        xfo = resp.headers.get("X-Frame-Options", "").strip().upper()
        if xfo in ("DENY", "SAMEORIGIN"):
            _zapisat_vidzhet(False, f"Яндекс запрещает вставку: X-Frame-Options {xfo}")
            return

        # То же самое, но новым способом: frame-ancestors в CSP.
        csp = resp.headers.get("Content-Security-Policy", "")
        found = re.search(r"frame-ancestors([^;]*)", csp, re.I)
        if found:
            komu = found.group(1).lower()
            if "granat-kmv.ru" not in komu and "*" not in komu:
                _zapisat_vidzhet(False, "Яндекс запрещает вставку: frame-ancestors")
                return

        _zapisat_vidzhet(True, "Яндекс пускает виджет")
    except Exception as e:
        _zapisat_vidzhet(False, f"виджет не проверить: {type(e).__name__}")


def _zapisat_vidzhet(mozhno, pochemu):
    _VIDZHET.update({"mozhno": mozhno, "pochemu": pochemu})
    print(f"[отзывы] {pochemu}", flush=True)


@app.context_processor
def inject_reviews():
    """Отзывы нужны и на главной, и в контактах — разбираем номер один раз."""
    return {"reviews": yandex_reviews()}


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


# Отдельная страница под запросы вроде «сделать копию миграционной
# карты» и «копия патента Лермонтов». Общая страница печати по таким
# словам не находится: их там просто нет. Цена та же, что у копирования.
@app.route("/dokumenty")
def dokumenty():
    return render_template("dokumenty.html")


# Ещё две страницы под запросы, а не под товар. Владелица 19.08.2026:
# «про сертификаты и открытки тоже есть». Человек ищет «напечатать
# грамоту» и «приглашения на свадьбу», а этих слов на общей странице
# печати нет — они спрятаны в примечании к таблице. Цены те же, что
# в прайсе: страницы разные, прайс один.
@app.route("/sertifikaty")
def sertifikaty():
    return render_template("sertifikaty.html")


@app.route("/otkrytki")
def otkrytki():
    return render_template("otkrytki.html")


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


# ── Короткие адреса для карточек и рекламы ───────────────────────────────
#
# 19.08.2026 владелица: «с рекламы звонят и говорят: я не знаю о вашем
# сайте ничего». В карточках стоит телефон, ссылки на сайт нет — человек
# звонит, чтобы спросить цену, вместо того чтобы посчитать её сам.
#
# Длинный адрес с метками в карточку вписывать неудобно и легко
# ошибиться. Поэтому короткий адрес живёт у нас, а метку он подставляет
# сам. В карточку вписывается granat-kmv.ru/2gis — и всё.
#
# Метки нужны не для красоты: без них в Метрике все эти люди
# сливаются в «переходы по рекламе», и непонятно, какая карточка
# работает, а какая просто стоит.
# Адреса объявляем ПОИМЁННО, а не одним правилом «/что-угодно».
# Общее правило перехватило бы и /logo.png, и /robots.txt: статика
# раздаётся из корня, и одиночный сегмент адреса Werkzeug считает
# более точным совпадением, чем путь к файлу. Картинки на сайте
# просто пропали бы, и искать причину пришлось бы долго.
KOROTKIE_ADRESA = {
    "2gis": "2gis",
    "ya": "yandex_business",
    "karty": "yandex_maps",
    "vizitka": "vizitka",       # печатная визитка и листовки
}


def _korotkij(istochnik):
    # Ведём сразу к секретарю: человек пришёл из карточки за ценой,
    # а не читать про студию.
    return redirect(
        "/?utm_source={}&utm_medium=referral&utm_campaign=kartochka#sekretar"
        .format(istochnik), code=302)


@app.route("/2gis")
def kor_2gis():
    return _korotkij(KOROTKIE_ADRESA["2gis"])


@app.route("/ya")
def kor_ya():
    return _korotkij(KOROTKIE_ADRESA["ya"])


@app.route("/karty")
def kor_karty():
    return _korotkij(KOROTKIE_ADRESA["karty"])


@app.route("/vizitka")
def kor_vizitka():
    return _korotkij(KOROTKIE_ADRESA["vizitka"])


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
        # В каком виде на страницах стоят отзывы. Проверять по этой строке
        # удобнее, чем искать в логах: она открывается с телефона.
        otzyvy=reviews_state(),
    )


def reviews_state():
    """Одной строкой: что сейчас показывает блок отзывов и почему."""
    got = yandex_reviews()
    if not got:
        return "выключены: не задан YANDEX_REVIEWS"
    if got["frame"]:
        return f"виджет с отзывами, карточка {got['frame'].rsplit('=', 1)[-1]}"
    if _SHORT_LINK["org"] or _VIDZHET["url"]:
        # Номер карточки есть, а рамки нет — значит виджет не пустили.
        # Пишем прямо почему: иначе непонятно, поломка это или так задумано.
        return f"кнопка на карточку: {_VIDZHET['pochemu']}"
    return "кнопка на карточку: номер карточки ещё не известен"




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
        # Номера может не быть: у проверки со своего телефона его нет,
        # и писать «по заявке №0» бессмысленно.
        "note": "Напишите нам в сообщения сообщества — ответим там же"
                + (f", по заявке №{lead_id}." if lead_id else "."),
    }

    if channel == "WhatsApp":
        nomer = f" №{lead_id}" if lead_id else ""
        text = (f"Здравствуйте! Я оставил заявку{nomer} на сайте "
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
    proverka = eto_proverka(phone)
    lead_id = 0 if proverka else leads.next_id()
    payload["lead"] = lead_id
    if proverka:
        payload["proverka"] = True
    else:
        leads.log(lead_id, "created", source="site_form", **payload)

    lines = ["🧪 ПРОВЕРКА, НЕ КЛИЕНТ — заявка со своего номера, "
             "номер не потрачен"] if proverka else []
    lines += [f"🔔 НОВАЯ ЗАЯВКА С САЙТА №{lead_id}", "", f"👤 Имя: {name}"]
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
            (f"🧪 Проверка с сайта — {name}" if proverka
             else f"Заявка с сайта №{lead_id} — {name}"), text
        )
        delivered = vk_ok or mail_ok
        save_order(payload, delivered=delivered,
                   reason="" if delivered else
                          f"вк: {vk_reason}; почта: {mail_reason}")
        if not proverka:
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
    # Файлов может быть несколько: у листовки две стороны, у буклета три
    # панели. До 18.08.2026 бралcя ровно один, и клиент об этом не знал —
    # он видел, что файл прикрепился, и был уверен, что отправил всё.
    makety, maket_zametki = [], []
    for fajl in request.files.getlist("maket")[:MAX_MAKETOV]:
        if not (fajl and fajl.filename):
            continue
        # Браузеры на Windows иногда шлют полный путь с обратными слешами,
        # а os.path.basename на Linux их за разделитель не считает — имя
        # выходило вроде «CUsersАняграмота.jpg».
        ish = os.path.basename(fajl.filename.replace("\\", "/"))
        rasshirenie = os.path.splitext(ish)[1].lower()
        if rasshirenie not in MAKET_RASSHIRENIYA:
            maket_zametki.append(
                f"файл {ish} не принят: расширение {rasshirenie or 'без расширения'}")
            continue
        bajty = fajl.read(MAX_MAKET + 1)
        if len(bajty) > MAX_MAKET:
            maket_zametki.append(
                f"файл {ish} не принят: больше {MAX_MAKET // 1024 // 1024} МБ")
            continue
        # Имя клиента в имя файла на диске не берём: там бывает что
        # угодно, вплоть до путей. Своё имя, а клиентское — в письме.
        bezopasnoe = "".join(c for c in ish if c.isalnum() or c in " .-_()").strip()
        makety.append((bezopasnoe or ("maket" + rasshirenie), bajty))

    if makety:
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

    proverka = eto_proverka(contact)
    lead_id = 0 if proverka else leads.next_id()
    payload["lead"] = lead_id
    if proverka:
        payload["proverka"] = True

    # Кладём файл на диск под номером заявки: так его находят по заявке,
    # не разбирая, кто из клиентов какой «scan1.pdf» прислал.
    puti = []
    for nomer, (imya, bajty) in enumerate(makety, 1):
        # Номер в имени сохраняет ПОРЯДОК сторон: лицо и оборот приходят
        # двумя файлами, и какой из них какой — видно только по очереди,
        # в которой их выбрал клиент.
        put_na_diske = os.path.join(MAKETY_DIR, f"{lead_id}_{nomer}_{imya}")
        try:
            with open(put_na_diske, "wb") as f:
                f.write(bajty)
            puti.append(put_na_diske)
        except OSError as e:
            maket_zametki.append(f"файл {imya} не сохранён на диск: {e}")
            print(f"[maket] файл {imya} не сохранён на диск: {e}", flush=True)
    if puti:
        payload["makety"] = puti
        payload["maket"] = puti[0]   # старое поле — чтобы не сломать читателей
    if maket_zametki:
        payload["maket_zametka"] = "; ".join(maket_zametki)

    if not proverka:
        leads.log(lead_id, "created", **payload)

    # ── ГЕНЕРАЛ докладывает ──────────────────────────────────────────────
    lines = ["🧪 ПРОВЕРКА, НЕ КЛИЕНТ — заявка со своего номера, "
             "номер не потрачен"] if proverka else []
    lines += [f"🤖 ЗАЯВКА С САЙТА №{lead_id}", "", f"📞 Контакт: {contact}"]
    if route_text:
        lines.append(f"🧭 Собрал: {route_text}")
    if total:
        lines.append("💰 На сумму: {:,} ₽".format(total).replace(",", " "))
    if makety:
        imena = ", ".join(imya for imya, _ in makety)
        skolko = "Файл приложен" if len(makety) == 1 else f"Файлов приложено {len(makety)}"
        lines.append(f"📎 {skolko} к письму: {imena}")
    if maket_zametki:
        lines.append("⚠️ " + "; ".join(maket_zametki) +
                     " — попросите прислать другим способом")
    if total:
        # НПД: чек обязателен и формируется вручную в «Мой налог».
        # Забытый чек — это и штраф, и невозможность для клиента-юрлица
        # поставить заказ в расходы. Напоминание стоит одной строкой.
        lines.append("🧾 После оплаты — чек в «Мой налог» и клиенту")
    lines.append("")
    # Раньше здесь стояло «Ждём клиента в боте для сбора ТЗ». Это
    # осталось от времён, когда сайт только принимал телефон, а задачу
    # выяснял бот. Теперь секретарь собирает всё сам — ждать нечего,
    # заказ можно ставить в работу.
    lines.append("Заказ собран секретарём — уточнять нечего, можно печатать.")

    # Все каналы сразу и в фоне — как и в заявке с формы выше. Симулятор
    # ждал ответа всех трёх наравне с формой, значит и висел так же.
    text = "\n".join(lines)

    def notify():
        (vk_ok, vk_reason), (mail_ok, mail_reason) = deliver(
            ("🧪 Проверка с сайта" if proverka
             else f"Заявка с сайта №{lead_id}"), text,
            vlozhenie=makety or None
        )
        delivered = vk_ok or mail_ok
        save_order(payload, delivered=delivered,
                   reason="" if delivered else
                          f"вк: {vk_reason}; почта: {mail_reason}")
        if not proverka:
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

    # Ссылка на счёт — только когда есть что оплачивать и это не проверка.
    # Подпись в ссылке обязательна: без неё чужой счёт открывается
    # подстановкой номера.
    schet_url = ""
    if total > 0 and not proverka:
        schet_url = "/schet/{}?k={}".format(lead_id, klyuch_scheta(lead_id))

    # Памятка клиенту. Даётся всегда, когда заявка настоящая: человек
    # закроет вкладку и останется без номера и без состава заказа.
    pamyatka_url = ""
    if not proverka:
        pamyatka_url = "/zayavka/{}?k={}".format(lead_id, klyuch_scheta(lead_id))

    return jsonify(ok=True, lead=lead_id, schet=schet_url,
                   pamyatka=pamyatka_url,
                   next=follow_up("", lead_id, ""))


# ── Реквизиты для счёта ──────────────────────────────────────────────────
#
# Лежат в коде, а не в секретах, и это осознанно: расчётный счёт, БИК
# и ИНН печатаются на каждом счёте и уходят каждому клиенту — секретом
# они не являются. Через переменные Amvera их можно переопределить,
# не трогая код: сменился банк — поменяли переменную и перезапустили.
REKVIZITY = {
    "nazvanie": os.getenv("REKV_NAZVANIE",
                          "Индивидуальный предприниматель "
                          "Мелконян Гульнара Рифкатовна"),
    "familiya": os.getenv("REKV_FAMILIYA", "Мелконян Г. Р."),
    "inn": os.getenv("REKV_INN", "490600091128"),
    "schet": os.getenv("REKV_SCHET", "40802810000009815176"),
    "bank": os.getenv("REKV_BANK", "АО «ТБанк»"),
    "bik": os.getenv("REKV_BIK", "044525974"),
    "korschet": os.getenv("REKV_KORSCHET", "30101810145250000974"),
    # ОГРНИП законом в счёте не требуется, но бухгалтерии его часто
    # просят. Пусто — строка в счёте просто не печатается.
    "ogrnip": os.getenv("REKV_OGRNIP", ""),
    "adres": os.getenv("REKV_ADRES", "г. Лермонтов, ул. Нагорная 2/1, этаж 2"),
    "telefon": os.getenv("REKV_TELEFON", "+7 (999) 244-99-99"),
}

# Строка про НДС. У ИП на НПД и на УСН её текст одинаков по смыслу —
# налога на добавленную стоимость нет, — поэтому пишем нейтрально.
# Появится другой режим — правится переменной, а не кодом.
# Мелкий заказ оплачивается целиком и сразу — та же цифра, что в прайсе
# секретаря (OPLATA.melkijZakazDo). Держим копией, потому что сервер
# прайс не читает: он собирается в разметку на этапе сборки.
MELKIJ_ZAKAZ_DO = int(os.getenv("MELKIJ_ZAKAZ_DO", "1000"))

NDS_STROKA = os.getenv(
    "REKV_NDS",
    "Без НДС. Продавец применяет налог на профессиональный доход "
    "(НПД), плательщиком НДС не является. Чек формируется "
    "в приложении «Мой налог» и передаётся покупателю после оплаты.")


def klyuch_scheta(lead_id: int) -> str:
    """Короткая подпись ссылки на счёт.

    Счёт лежит по адресу вида /schet/28, и без подписи любой человек
    подставил бы чужой номер и увидел чужой заказ. Подпись считается
    от номера и секрета студии, подобрать её нельзя.
    """
    sekret = (os.getenv("WATCH_TOKEN", "") or MAIL_PASSWORD or "granat").encode()
    return hmac.new(sekret, str(lead_id).encode(), hashlib.sha256).hexdigest()[:12]


def summa_propisyu(n: int) -> str:
    """Сумма прописью — обязательная строка любого счёта.

    Библиотеку не тянем: ради одной строки ставить зависимость,
    которая может не собраться на Amvera, невыгодно.
    """
    ed = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь",
          "восемь", "девять"]
    ed_zh = ["", "одна", "две", "три", "четыре", "пять", "шесть", "семь",
             "восемь", "девять"]
    do20 = ["десять", "одиннадцать", "двенадцать", "тринадцать",
            "четырнадцать", "пятнадцать", "шестнадцать", "семнадцать",
            "восемнадцать", "девятнадцать"]
    des = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят",
           "шестьдесят", "семьдесят", "восемьдесят", "девяносто"]
    sot = ["", "сто", "двести", "триста", "четыреста", "пятьсот",
           "шестьсот", "семьсот", "восемьсот", "девятьсот"]

    def gruppa(x, zhenskij=False):
        slova = []
        if x >= 100:
            slova.append(sot[x // 100]); x %= 100
        if 10 <= x < 20:
            slova.append(do20[x - 10]); x = 0
        if x >= 20:
            slova.append(des[x // 10]); x %= 10
        if x:
            slova.append((ed_zh if zhenskij else ed)[x])
        return slova

    def okonchanie(x, formy):
        x = x % 100
        if 11 <= x <= 14:
            return formy[2]
        x = x % 10
        if x == 1:
            return formy[0]
        if 2 <= x <= 4:
            return formy[1]
        return formy[2]

    n = int(n)
    if n <= 0:
        return "ноль рублей 00 копеек"
    slova = []
    millionov, ostatok = divmod(n, 1000000)
    tysyach, rublej = divmod(ostatok, 1000)
    if millionov:
        slova += gruppa(millionov) + [okonchanie(millionov, ["миллион", "миллиона", "миллионов"])]
    if tysyach:
        slova += gruppa(tysyach, True) + [okonchanie(tysyach, ["тысяча", "тысячи", "тысяч"])]
    if rublej or not slova:
        slova += gruppa(rublej)
    slova.append(okonchanie(n, ["рубль", "рубля", "рублей"]))
    fraza = " ".join(w for w in slova if w)
    return fraza[0].upper() + fraza[1:] + " 00 копеек"


@app.route("/schet/<int:lead_id>")
def schet(lead_id):
    """Счёт на оплату по заявке — для тех, кому нужен документ.

    Просьба владелицы 18.08.2026: «можно формировать счёт: мне заявка,
    а заказчику счёт с моими реквизитами». Юрлицо без счёта не платит,
    а бухгалтерии нужен документ, а не сообщение в чате.

    Счёт собирается ИЗ ЗАЯВКИ, руками ничего не переписывается: сумма
    и состав заказа берутся оттуда же, откуда их видел клиент. Разойтись
    им негде.
    """
    if request.args.get("k", "") != klyuch_scheta(lead_id):
        return "Счёт не найден", 404

    zayavka = leads.find(lead_id)
    if not zayavka:
        return "Счёт не найден", 404

    try:
        summa = int(zayavka.get("total") or 0)
    except (TypeError, ValueError):
        summa = 0
    if summa <= 0:
        return "По этой заявке сумма ещё не подтверждена", 404

    # Состав заказа — то же, что клиент видел в разговоре. Телефон
    # и служебные строки в счёт не выносим: документ уходит в чужую
    # бухгалтерию.
    sluzhebnye = ("Согласие на обработку", "ТЗ согласовано", "Клиент написал",
                  "Оплата на момент заявки", "Макет к заявке", "Макетов приложено",
                  "Макет приложен", "Замер по файлу")
    sostav = [str(o) for o in (zayavka.get("options") or [])
              if str(o).strip() and not str(o).startswith(sluzhebnye)]

    naimenovanie = (sostav[0] if sostav else "Полиграфические услуги")
    if not naimenovanie.strip():
        naimenovanie = "Полиграфические услуги"

    return render_template(
        "schet.html",
        nomer=lead_id,
        data=now_msk().strftime("%d.%m.%Y"),
        postavshchik=REKVIZITY,
        platelshchik="Физическое лицо — по заявке № {}".format(lead_id),
        naimenovanie="{} (по заявке № {})".format(naimenovanie, lead_id),
        summa_str="{:,}".format(summa).replace(",", " "),
        propisyu=summa_propisyu(summa),
        nds=NDS_STROKA,
        naznachenie=("Оплата по счёту № {} от {}. {}"
                     .format(lead_id, now_msk().strftime("%d.%m.%Y"),
                             NDS_STROKA.rstrip("."))),
        srok_scheta=os.getenv("REKV_SROK_SCHETA",
                              "Счёт действителен для оплаты 3 банковских дня."),
        sostav=" · ".join(sostav[1:]) if len(sostav) > 1 else "",
    )


@app.route("/zayavka/<int:lead_id>")
def zayavka_klientu(lead_id):
    """Памятка клиенту: что он заказал, за сколько и куда прийти.

    Просьба владелицы 19.08.2026: «а этой девушке такая заявка
    не уйдёт? как клиент сохранит свою заявку». Не уходила: человек
    видел экран, закрывал вкладку — и у него не оставалось ни номера,
    ни состава, ни суммы. Приходил через день и спрашивал «а что я
    заказывал».

    Почты мы не спрашиваем и спрашивать не будем — лишнее поле в форме
    стоит заявок. Поэтому памятка живёт по ссылке: её можно сохранить
    в закладки, отправить себе в мессенджер или распечатать.
    """
    if request.args.get("k", "") != klyuch_scheta(lead_id):
        return "Заявка не найдена", 404

    zayavka = leads.find(lead_id)
    if not zayavka:
        return "Заявка не найдена", 404

    # Служебные строки клиенту не нужны: он их и так только что видел
    # в разговоре, а согласия и замеры — наша кухня.
    sluzhebnye = ("Согласие на обработку", "Замер по файлу",
                  "Оплата на момент заявки", "ТЗ согласовано")
    sostav = [str(o) for o in (zayavka.get("options") or [])
              if str(o).strip() and not str(o).startswith(sluzhebnye)]

    try:
        summa = int(zayavka.get("total") or 0)
    except (TypeError, ValueError):
        summa = 0

    # Что дальше — зависит от того, ждёт нас человек сегодня или тираж
    # в работе. Обещать «перезвоним» тому, кто придёт через час, нельзя:
    # ровно на этом 18.08.2026 ушла клиентка из Краснодара.
    srochno = any("Сегодня" in str(o) for o in sostav)
    chto_dalshe = (
        "Приезжайте — заказ будет готов к названному времени. "
        "Назовите номер заявки, этого достаточно."
        if srochno else
        "Мы проверим файл и подтвердим срок. Если что-то в макете "
        "помешает печати, скажем об этом до работы, а не после."
    )

    return render_template(
        "zayavka-klientu.html",
        nomer=lead_id,
        data=now_msk().strftime("%d.%m.%Y"),
        sostav=sostav,
        summa="{:,}".format(summa).replace(",", " ") if summa else "",
        oplata=("Оплата целиком сразу — печатаем, как только придёт"
                if summa and summa < MELKIJ_ZAKAZ_DO
                else "Печать запускаем после предоплаты"),
        chto_dalshe=chto_dalshe,
        studiya={
            "adres": REKVIZITY["adres"],
            "chasy": "Пн–Сб 09:00–20:00, Вс 10:00–19:00",
            "telefon": REKVIZITY["telefon"],
            "tel_ssylka": "+79992449999",
        },
    )


@app.route("/api/sbros-schetchika")
def sbros_schetchika():
    """Начать нумерацию заявок заново — но НИЧЕГО НЕ ПОТЕРЯВ.

    Просьба владелицы 18.08.2026: «у нас уже 27-я заявка, а по сути
    только одна, надо обнулить счётчик». Проверки секретаря сожгли
    двадцать шесть номеров, и по номеру нельзя понять, сколько людей
    обратилось на самом деле.

    ПОЧЕМУ НЕЛЬЗЯ ПРОСТО ЗАПИСАТЬ НОЛЬ В СЧЁТЧИК. Номера уже стоят
    в журнале `/data/leads.jsonl` и в именах файлов с макетами. Начни
    счёт заново — и новая заявка №5 совпадёт со старой: `leads.find(5)`
    вернёт чужую запись, а макет одного клиента ляжет к заказу другого.
    Разобрать это потом будет нечем.

    ПОЭТОМУ СНАЧАЛА УБИРАЕМ СТАРОЕ В АРХИВ, а потом обнуляем. Ничего
    не удаляется: журнал и макеты переименовываются с датой и остаются
    на диске. Старую заявку можно будет найти руками, а новая нумерация
    ни на что не наложится.

    Делается один раз и вручную:
        https://granat-kmv.ru/api/sbros-schetchika?token=ТОКЕН
    Токен — тот же WATCH_TOKEN из переменных Amvera.
    """
    token = os.getenv("WATCH_TOKEN", "").strip()
    if not token or request.args.get("token", "") != token:
        return jsonify(ok=False, error="forbidden"), 403

    metka = now_msk().strftime("%Y-%m-%d-%H%M")
    sdelano, oshibki = [], []

    zhurnal = os.path.join("/data", "leads.jsonl")
    arhiv = os.path.join("/data", f"leads-arhiv-{metka}.jsonl")
    try:
        if os.path.exists(zhurnal):
            os.rename(zhurnal, arhiv)
            sdelano.append(f"журнал заявок убран в {os.path.basename(arhiv)}")
    except OSError as e:
        oshibki.append(f"журнал не переименован: {e}")

    makety_arhiv = f"{MAKETY_DIR}-arhiv-{metka}"
    try:
        if os.path.isdir(MAKETY_DIR):
            os.rename(MAKETY_DIR, makety_arhiv)
            sdelano.append(f"макеты убраны в {os.path.basename(makety_arhiv)}")
    except OSError as e:
        oshibki.append(f"макеты не перенесены: {e}")

    # Счётчик обнуляем ПОСЛЕДНИМ: если архивация не удалась, старые
    # номера остаются в деле, и новая нумерация их не затрёт.
    if oshibki:
        return jsonify(ok=False, sdelano=sdelano, oshibki=oshibki,
                       schetchik="не тронут — сначала разберитесь с архивом"), 500

    try:
        with open(os.path.join("/data", "lead_counter"), "w", encoding="utf-8") as f:
            f.write("0")
        sdelano.append("счётчик обнулён, следующая заявка будет №1")
    except OSError as e:
        return jsonify(ok=False, sdelano=sdelano, oshibki=[f"счётчик: {e}"]), 500

    print(f"[sbros] {'; '.join(sdelano)}", flush=True)
    return jsonify(ok=True, sdelano=sdelano)


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
