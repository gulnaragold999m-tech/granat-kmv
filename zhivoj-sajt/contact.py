# -*- coding: utf-8 -*-
"""
Разбор контакта из формы заявки: телефон или ник в Telegram.

ЗАЧЕМ. Поле в форме называется «Телефон или Telegram» и до сих пор принимало
что угодно — включая пустую строку из пробелов и номер из пяти цифр. Заявка
записывалась, Гульнара её видела, а позвонить было некуда. Для студии, у
которой заявок единицы, потерянный контакт стоит дороже всего остального.

ЧТО ЭТОТ МОДУЛЬ ДЕЛАЕТ И ЧЕГО НЕ ДЕЛАЕТ. Он ловит опечатки и мусор —
пропущенную цифру, случайный набор, ник, записанный как попало. Он НЕ решает,
мошенник перед нами или нет, и не отсеивает «подозрительных»: у типографии,
которая печатает по предоплате, подставная заявка ничего не крадёт, а
отклонённый по ошибке живой клиент — это минус живой клиент.

Отсюда правило: сомнение трактуем в пользу клиента. Отклоняем только то, чем
физически нельзя воспользоваться.
"""

import re

# Ник в Telegram: 5–32 знака, начинается с буквы, дальше буквы, цифры и
# подчёркивания. Регистр не важен — Telegram его не различает.
USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")

# Российский номер без кода страны — десять цифр. Первая цифра кода региона
# или мобильного оператора никогда не бывает 0, 1 или 2: такие коды в плане
# нумерации не выдаются. Это ловит и «сползшую» первую цифру, и явный мусор.
BAD_FIRST = "012"

HINT_PHONE = "Например: +7 928 123-45-67"
HINT_ANY = "Телефон в виде +7 928 123-45-67 или ник в Telegram через @"


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw or "")


def _looks_like_username(raw: str) -> bool:
    """Похоже ли на ник, а не на телефон.

    Решаем по количеству цифр: в любом телефоне их минимум десять. Если цифр
    меньше, а буквы есть — это ник, даже когда человек забыл собачку.
    """
    body = (raw or "").strip()
    if not body:
        return False
    if len(_digits(body)) >= 10:
        return False
    return "@" in body or "t.me/" in body.lower() or any(c.isalpha() for c in body)


def _clean_username(raw: str) -> str:
    """Ник из того, что написал человек: @ivan, t.me/ivan, ivan — всё сюда."""
    body = (raw or "").strip()
    for prefix in ("https://", "http://", "t.me/", "telegram.me/", "@"):
        if body.lower().startswith(prefix):
            body = body[len(prefix):]
    # Ссылку могли прислать целиком, с хвостом после ника.
    return body.split("/")[0].split("?")[0].strip()


def parse(raw: str) -> dict:
    """Разобрать контакт. Возвращает словарь:

        kind  — 'phone' | 'username' | ''  (пусто, если не разобрали)
        value — как показывать: '+79281234567' или '@ivan'
        key   — последние 10 цифр телефона, для узнавания клиента.
                У ника ключа нет: leads ищет человека именно по цифрам.
        error — текст для клиента; пусто, если всё в порядке.
    """
    body = (raw or "").strip()
    if not body:
        return {"kind": "", "value": "", "key": "",
                "error": "Оставьте телефон или ник в Telegram — "
                         "иначе мы не сможем вам ответить."}

    if _looks_like_username(body):
        nick = _clean_username(body)
        if USERNAME_RE.match(nick):
            return {"kind": "username", "value": "@" + nick, "key": "",
                    "error": ""}
        return {"kind": "", "value": "", "key": "",
                "error": "Не разобрали контакт. " + HINT_ANY}

    digits = _digits(body)
    plus = body.startswith("+")

    # Российский номер: 11 цифр с 7 или 8 впереди, либо сразу 10.
    national = ""
    if len(digits) == 11 and digits[0] in "78":
        national = digits[1:]
    elif len(digits) == 10:
        national = digits

    if national:
        if national[0] in BAD_FIRST or len(set(national)) == 1:
            return {"kind": "", "value": "", "key": "",
                    "error": f"Проверьте номер — кажется, в нём опечатка. "
                             f"{HINT_PHONE}"}
        return {"kind": "phone", "value": "+7" + national, "key": national,
                "error": ""}

    # Иностранный номер принимаем, только если человек сам поставил плюс:
    # без него восемь цифр — это почти всегда потерянная цифра в российском.
    if plus and 8 <= len(digits) <= 15:
        return {"kind": "phone", "value": "+" + digits, "key": digits[-10:],
                "error": ""}

    if len(digits) < 10:
        return {"kind": "", "value": "", "key": "",
                "error": f"В номере не хватает цифр. {HINT_PHONE} — "
                         f"или укажите ник в Telegram через @"}

    return {"kind": "", "value": "", "key": "",
            "error": f"Проверьте номер — кажется, в нём лишние цифры. "
                     f"{HINT_PHONE}"}


def pretty(value: str) -> str:
    """Российский номер в читаемом виде для заявки: +7 928 123-45-67."""
    if not value.startswith("+7") or len(value) != 12:
        return value
    d = value[2:]
    return f"+7 {d[0:3]} {d[3:6]}-{d[6:8]}-{d[8:10]}"


# ── Самопроверка ────────────────────────────────────────────────────────
#
# Запуск: python contact.py. Слева — то, что люди реально пишут в форму.
# Половина случаев здесь — про то, что принять НАДО: слишком строгая
# проверка теряет живых клиентов, и это дороже пропущенного мусора.

if __name__ == "__main__":
    CASES = [
        # (что ввели, ожидаемый kind, ожидаемое value)
        ("+7 928 123-45-67", "phone", "+79281234567"),
        ("89281234567", "phone", "+79281234567"),
        ("9281234567", "phone", "+79281234567"),
        ("8 (928) 123 45 67", "phone", "+79281234567"),
        ("+7 999 244 99 99", "phone", "+79992449999"),
        ("87932 5 12 34", "phone", "+78793251234"),   # городской КМВ
        ("+380 67 123 4567", "phone", "+380671234567"),  # с плюсом — иностранный
        ("@ivan_petrov", "username", "@ivan_petrov"),
        ("ivan_petrov", "username", "@ivan_petrov"),
        ("t.me/ivan_petrov", "username", "@ivan_petrov"),
        ("https://t.me/ivan_petrov", "username", "@ivan_petrov"),
        # — а это принимать нельзя —
        ("", "", ""),
        ("   ", "", ""),
        ("12345", "", ""),
        ("0281234567", "", ""),        # не бывает такого кода
        ("9999999999", "", ""),        # одна цифра подряд
        ("@ab", "", ""),               # ник короче пяти знаков
        ("не скажу", "", ""),
    ]
    ok = True
    for raw, kind, value in CASES:
        got = parse(raw)
        good = got["kind"] == kind and got["value"] == value
        ok = ok and good
        mark = "OK " if good else "FAIL"
        shown = got["value"] or got["error"]
        print(f"[{mark}] {raw!r:<26} → {got['kind'] or '—':<9} {shown[:56]}")
    print("\nВсе случаи разобраны верно." if ok else "\nЕсть расхождения!")
