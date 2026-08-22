# -*- coding: utf-8 -*-
"""
Распознавание голосовых сообщений — общее для Telegram и ВКонтакте.

ЗАЧЕМ. До 10.08.2026 голосовое в Telegram проваливалось в пустоту: среди
обработчиков бота не было ни одного, который ловит `voice`. Клиент наговаривал
задачу и не получал ничего в ответ. Человек, которому бот не ответил, второй
раз обычно не пишет — это самая дорогая из найденных дыр.

ПОЧЕМУ ЯНДЕКС, А НЕ WHISPER. Whisper от OpenAI лучше слышит, но из России ему
нельзя ни заплатить, ни достучаться. SpeechKit — та же экосистема, где у
студии уже почта и пароль приложения, оплата обычной картой, и русская речь
для него родная. Ключ кладём в переменную `SPEECHKIT_API_KEY`; без неё модуль
молча выключен, а боты работают как раньше.

ГРАНИЦА, ПРО КОТОРУЮ НАДО ЗНАТЬ. Быстрое распознавание принимает запись не
длиннее 30 секунд и не тяжелее мегабайта. Клиенты наговаривают и по две
минуты. Такие записи мы НЕ теряем: их пересылает Гульнаре тот код, что зовёт
этот модуль, а клиенту честно говорим, что длинную запись слушает человек.
Длинные записи умеет асинхронный режим SpeechKit, но он требует объектного
хранилища — отдельная история, не сегодня.

ФОРМАТ. Telegram отдаёт голосовые в OGG/Opus, ВКонтакте тоже — это ровно то,
что SpeechKit принимает как `oggopus`. Перекодировать ничего не нужно, ffmpeg
не нужен.

── ПЕРЕМЕННЫЕ ПРИЛОЖЕНИЯ ────────────────────────────────────────────────
    SPEECHKIT_API_KEY   — ключ сервисного аккаунта Яндекс Облака.
    SPEECHKIT_FOLDER_ID — идентификатор каталога облака.
────────────────────────────────────────────────────────────────────────
"""

import logging
import os

import requests

logger = logging.getLogger("speech")

ENDPOINT = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

API_KEY = os.getenv("SPEECHKIT_API_KEY", "").strip()
FOLDER_ID = os.getenv("SPEECHKIT_FOLDER_ID", "").strip()

# Ограничения быстрого распознавания. Проверяем их ДО скачивания файла:
# длительность и размер Telegram и ВК сообщают заранее, и незачем тянуть
# мегабайты, чтобы потом получить отказ.
MAX_SECONDS = 30
MAX_BYTES = 1_000_000

TIMEOUT = 20

# Что говорим клиенту, когда текста не будет. Формулировки разные: человек
# должен понимать, его ли это проблема и что делать дальше.
TOO_LONG = (
    "Запись длинная — такую я не разбираю, её послушает Гульнара, я уже "
    "передал. Если хотите продолжить со мной прямо сейчас, напишите пару "
    "слов текстом: что нужно и в каком количестве."
)
CANT_HEAR = (
    "Голосовое получил и передал Гульнаре — она послушает. Разобрать его "
    "текстом у меня сейчас не вышло. Напишите, пожалуйста, коротко: что "
    "нужно и в каком количестве?"
)


def enabled() -> bool:
    """Настроено ли распознавание. Без ключа модуль не работает — и это
    нормальное состояние, а не ошибка."""
    return bool(API_KEY)


def too_long(duration=None, size=None) -> bool:
    """Заведомо не пройдёт быстрое распознавание. Любой из параметров может
    быть неизвестен — тогда он просто не участвует в проверке."""
    if duration and duration > MAX_SECONDS:
        return True
    if size and size > MAX_BYTES:
        return True
    return False


def recognize(audio: bytes, lang: str = "ru-RU"):
    """Аудио в текст. Возвращает (текст, причина_отказа).

    Наружу не падает никогда: голосовое клиента не должно ронять разговор.
    Пустой текст при пустой причине означает, что человек промолчал в
    микрофон — такое тоже бывает.
    """
    if not enabled():
        return "", "распознавание не настроено"
    if not audio:
        return "", "пустой файл"
    if len(audio) > MAX_BYTES:
        return "", "запись длиннее 30 секунд"

    params = {"lang": lang, "format": "oggopus"}
    if FOLDER_ID:
        params["folderId"] = FOLDER_ID

    try:
        r = requests.post(
            ENDPOINT,
            params=params,
            headers={"Authorization": f"Api-Key {API_KEY}"},
            data=audio,
            timeout=TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("SpeechKit: сеть: %s: %s", type(e).__name__, e)
        return "", "сеть"

    if r.status_code != 200:
        # Ключ в лог не пишем ни при каких условиях: 09.08.2026 токен бота
        # утёк в /api/health именно через текст сетевой ошибки.
        logger.warning("SpeechKit: отказ %s", r.status_code)
        return "", f"сервис ответил {r.status_code}"

    try:
        text = (r.json() or {}).get("result", "")
    except Exception as e:  # noqa: BLE001
        logger.warning("SpeechKit: непонятный ответ: %s", e)
        return "", "непонятный ответ сервиса"

    return (text or "").strip(), ""


def heard(text: str) -> str:
    """Как показать клиенту распознанное.

    Показываем ВСЕГДА и до того, как пустим текст в работу. Распознавание
    ошибается на именах, адресах и числах — а число здесь это тираж, то есть
    деньги. Клиент должен успеть поправить до того, как ошибка уедет в заявку.
    """
    return f"📝 Я услышал: «{text}»\n\nЕсли не так — просто напишите правильно."


# ── Самопроверка ────────────────────────────────────────────────────────
#
# Запуск: python speech.py. Сеть не трогает — подменяет requests.post и
# проверяет разбор ответов и границы. Реальный ключ для этого не нужен.

if __name__ == "__main__":
    import types

    ok = True

    def check(title, got, want):
        global ok
        good = got == want
        ok = ok and good
        print(f"[{'OK ' if good else 'FAIL'}] {title:<44} {got!r}")

    # Границы считаются без всякой сети.
    check("15 секунд проходит", too_long(15, 90_000), False)
    check("31 секунда не проходит", too_long(31, 90_000), True)
    check("файл на 2 МБ не проходит", too_long(5, 2_000_000), True)
    check("длительность неизвестна", too_long(None, None), False)

    # Без ключа модуль выключен и говорит об этом честно.
    globals()["API_KEY"] = ""
    check("без ключа выключен", enabled(), False)
    check("без ключа не распознаёт", recognize(b"x")[1], "распознавание не настроено")

    # Дальше — с ключом и подменённой сетью.
    globals()["API_KEY"] = "test-key"
    check("с ключом включён", enabled(), True)

    def fake(status, payload):
        def _post(*a, **k):
            r = types.SimpleNamespace()
            r.status_code = status
            r.json = lambda: payload
            return r
        return _post

    real_post = requests.post
    try:
        requests.post = fake(200, {"result": "нужно сто визиток срочно"})
        check("успешный разбор", recognize(b"audio"), ("нужно сто визиток срочно", ""))

        requests.post = fake(200, {"result": ""})
        check("человек промолчал", recognize(b"audio"), ("", ""))

        requests.post = fake(401, {})
        check("неверный ключ", recognize(b"audio")[1], "сервис ответил 401")

        def boom(*a, **k):
            raise requests.exceptions.ConnectTimeout("нет сети")
        requests.post = boom
        check("сеть отвалилась", recognize(b"audio")[1], "сеть")

        check("слишком большой файл", recognize(b"x" * 1_000_001)[1],
              "запись длиннее 30 секунд")
    finally:
        requests.post = real_post

    print("\nВсе случаи разобраны верно." if ok else "\nЕсть расхождения!")
