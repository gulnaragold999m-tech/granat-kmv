# -*- coding: utf-8 -*-
"""Самопроверка сайта: то, что надо смотреть регулярно, — одной командой.

  npm run proverka-sajta

ЗАЧЕМ ЭТО ЕСТЬ. Гайды по SEO предлагают собрать «машину» из десяти
систем с расписаниями и доступами к API. Половина её модулей нам сейчас
не нужна — нечего мониторить, — но одна вещь нужна прямо сегодня:
регулярная проверка того, что мы сами не сломали.

Проверка работает ПО ИСХОДНИКАМ, без интернета: рендерит шаблоны Flask
и смотрит получившийся HTML. Значит её можно гонять до выкатки,
а не узнавать о поломке из просевшего трафика через месяц.

ЧЕМ ОНА ОТЛИЧАЕТСЯ ОТ ЧУЖИХ ЧЕК-ЛИСТОВ. Три проверки здесь придуманы
не по гайду, а по собственным граблям, и в чужих аудитах их нет:

  · ОБЕЩАНИЯ НЕСУЩЕСТВУЮЩЕГО — сверка текста страниц со списком
    NET_V_PRAJSE. 21.08.2026 нашлось, что страница /pechat полгода
    обещала ажурную резку, конгрев, разработку логотипа и наклейки
    Oracal. Ни один SEO-аудит этого не поймает: технически страница
    безупречна, просто она врёт.
  · ЦЕНЫ ПРОТИВ ПРАЙСА — цифра на странице обязана быть в data/prices.ts.
    Сертификаты «от 300 ₽» при рознице от 150 ₽ прожили на сайте
    две недели.
  · СТРАНИЦЫ-СИРОТЫ — на страницу никто не ссылается, значит её
    не найдут ни человек, ни робот.

Выход: список замечаний по трём уровням. КРИТИЧНО блокирует рост,
ВАЖНО заметно влияет, ПОТОМ — мелочи. Пусто — так и пишем.
"""
import io
import json
import os
import re
import sys

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAJT = os.path.join(KOREN, "zhivoj-sajt")
sys.path.insert(0, SAJT)

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    sys.exit("Нужен jinja2: pip install jinja2")

import uslugi  # noqa: E402

KRITICHNO, VAZHNO, POTOM = [], [], []


def zamechanie(uroven, stranica, tekst):
    uroven.append((stranica, tekst))


def bez_sluzhebnogo(html):
    """Видимый текст: без скриптов, стилей и комментариев."""
    t = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def sobrat_stranicy(env, ceny):
    """Все страницы сайта, отрисованные в HTML."""
    stranicy = {}
    prostye = {
        "/": "index.html", "/pechat": "pechat.html", "/cifra": "cifra.html",
        "/raboty": "raboty.html", "/kak-rabotaem": "kak-rabotaem.html",
        "/kontakty": "kontakty.html",
    }
    for put, shablon in prostye.items():
        try:
            stranicy[put] = env.get_template(shablon).render(ceny=ceny)
        except Exception as e:
            zamechanie(KRITICHNO, put, "страница не собирается: %s" % e)
    for u in uslugi.spisok():
        put = "/pechat/" + u["slug"]
        try:
            stranicy[put] = env.get_template("usluga.html").render(
                u=uslugi.usluga(u["slug"]), slug=u["slug"], ceny=ceny,
                drugie=[x for x in uslugi.spisok() if x["slug"] != u["slug"]])
        except Exception as e:
            zamechanie(KRITICHNO, put, "страница не собирается: %s" % e)
    return stranicy


def proverit_mety(stranicy):
    tituly, opisaniya = {}, {}
    for put, html in stranicy.items():
        t = re.search(r"<title>(.*?)</title>", html, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', html, re.S)
        h1 = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.S)

        if not t or not t.group(1).strip():
            zamechanie(KRITICHNO, put, "нет заголовка title")
        else:
            zag = t.group(1).strip()
            tituly.setdefault(zag, []).append(put)

        if not d or not d.group(1).strip():
            zamechanie(KRITICHNO, put, "нет описания description")
        else:
            op = d.group(1).strip()
            opisaniya.setdefault(op, []).append(put)
            if len(op) > 250:
                zamechanie(POTOM, put, "описание длиннее 250 знаков (%d)" % len(op))

        if len(h1) == 0:
            zamechanie(KRITICHNO, put, "нет H1")
        elif len(h1) > 1:
            zamechanie(VAZHNO, put, "H1 больше одного (%d) — рвётся иерархия" % len(h1))

    for zag, puti in tituly.items():
        if len(puti) > 1:
            zamechanie(VAZHNO, ", ".join(puti), "одинаковый title на разных страницах")
    for op, puti in opisaniya.items():
        if len(puti) > 1:
            zamechanie(VAZHNO, ", ".join(puti), "одинаковое описание на разных страницах")


def proverit_razmetku(stranicy):
    for put, html in stranicy.items():
        bloki = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if not bloki:
            zamechanie(VAZHNO, put, "нет микроразметки JSON-LD")
            continue
        tipy = []
        for i, b in enumerate(bloki, 1):
            try:
                d = json.loads(b)
                tipy.append(d.get("@type"))
            except ValueError as e:
                zamechanie(KRITICHNO, put, "разметка JSON-LD блок %d сломана: %s" % (i, e))
        if put.startswith("/pechat/") and "Service" not in tipy:
            zamechanie(VAZHNO, put, "у страницы услуги нет разметки Service")
        if put.startswith("/pechat/") and "FAQPage" not in tipy:
            zamechanie(POTOM, put, "нет разметки FAQPage — блок вопросов не попадёт в выдачу")


def proverit_obeshchaniya(stranicy, net_v_prajse):
    """ГЛАВНАЯ НАША ПРОВЕРКА. Сайт не должен обещать того, чего нет.

    ПЕРВАЯ ВЕРСИЯ ИСКАЛА КОРНИ СЛОВ И ДАЛА ПЯТЬ ЛОЖНЫХ СРАБАТЫВАНИЙ
    ИЗ ПЯТИ. «Тиснени» ловилось на тиснении фольгой, которое у студии
    ЕСТЬ (запрещены слепое и конгрев); «логотип» — на логотипе студии
    в шапке; «календа» — на Google-календаре в демонстрации бота.

    Мораль важнее самой функции: проверка, которая кричит впустую,
    хуже отсутствующей — её перестают читать и вместе с ложными
    пропускают настоящие. Поэтому ищем ТОЧНЫЕ ФРАЗЫ, а рядом держим
    список разрешённого."""

    ZAPRESHCHENO = [
        "ажурная резка", "ажурной резки", "контурная резка", "контурной резки",
        "фигурная резка", "фигурной резки", "плоттерная резка", "плоттерной резки",
        "режущий плоттер",
        "конгрев", "блинтовое тиснение", "слепое тиснение", "уф-лак",
        "разработка логотипа", "разработку логотипа", "создание логотипа",
        "фирменный стиль", "фирменного стиля",
        "наклейки oracal", "оракал",
        "офсетная печать",
        "квартальный календарь", "квартальные календари", "перекидной календарь",
        "съёмка на документы", "фотосъёмка", "сфотографируем",
    ]
    RAZRESHENO = [
        "тиснение фольгой", "тиснением фольгой", "горячее тиснение",
        "логотип студии", "логотипа студии",
        "google-календар", "настенный календарь",
    ]

    for put, html in stranicy.items():
        tekst = bez_sluzhebnogo(html).lower()
        for r in RAZRESHENO:
            tekst = tekst.replace(r, " ")
        najdeno = sorted({z for z in ZAPRESHCHENO if z in tekst})
        if najdeno:
            zamechanie(KRITICHNO, put,
                       "обещает то, чего у студии нет: %s" % ", ".join(najdeno))


def proverit_ceny(stranicy, prajs_ceny):
    """Каждая сумма на странице обязана быть в прайсе.

    РЕГУЛЯРКА НАМЕРЕННО СТРОГАЯ. Первая версия хватала «А6 60 ₽»
    как «660 ₽»: цифра формата приклеивалась к цене."""
    for put, html in stranicy.items():
        tekst = bez_sluzhebnogo(html)
        chuzhie = set()
        for m in re.finditer(r"(?<![\w\d])(\d{1,3}(?:[\s\u00a0]?\d{3})*)\s*₽", tekst):
            n = int(re.sub(r"[\s\u00a0]", "", m.group(1)))
            if n not in prajs_ceny:
                chuzhie.add(n)
        if not chuzhie:
            continue
        if put in ("/cifra", "/pechat") and all(n >= 10000 for n in chuzhie):
            zamechanie(VAZHNO, put,
                       "цены цифрового направления вписаны в вёрстку руками "
                       "и не имеют источника: %s"
                       % ", ".join(str(n) for n in sorted(chuzhie)))
        else:
            zamechanie(VAZHNO, put, "цены не из прайса: %s"
                       % ", ".join(str(n) for n in sorted(chuzhie)))


def proverit_sirot(stranicy):
    """Страница, на которую никто не ссылается, не будет найдена."""
    vhodyashchie = {p: 0 for p in stranicy}
    for put, html in stranicy.items():
        for ssylka in set(re.findall(r'href="(/[^"#?]*)"', html)):
            ssylka = ssylka.rstrip("/") or "/"
            if ssylka in vhodyashchie and ssylka != put:
                vhodyashchie[ssylka] += 1
    for put, skolko in vhodyashchie.items():
        if skolko == 0 and put != "/":
            zamechanie(VAZHNO, put, "страница-сирота: на неё никто не ссылается")


def proverit_geo(stranicy):
    for put, html in stranicy.items():
        tekst = bez_sluzhebnogo(html)
        if "Лермонтов" not in tekst:
            zamechanie(VAZHNO, put, "в тексте нет города — робот не свяжет страницу с Лермонтовом")


def proverit_slagi():
    for u in uslugi.spisok():
        s = u["slug"]
        if not re.fullmatch(r"[a-z0-9-]+", s):
            zamechanie(KRITICHNO, "/pechat/" + s,
                       "в адресе кириллица или заглавные — ловит 404 и дубли")


def proverit_kartu(stranicy):
    src = io.open(os.path.join(SAJT, "app.py"), encoding="utf-8").read()
    v_karte = set(re.findall(r'\("(/[^"]*)",\s*"\d{4}-', src))
    v_karte |= {"/pechat/" + u["slug"] for u in uslugi.spisok()}
    for put in stranicy:
        if put not in v_karte:
            zamechanie(VAZHNO, put, "страницы нет в карте сайта — робот о ней не узнает")


def main():
    env = Environment(loader=FileSystemLoader(os.path.join(SAJT, "templates")))
    try:
        ceny = json.load(io.open(os.path.join(SAJT, "ceny.json"), encoding="utf-8"))
    except (OSError, ValueError):
        ceny = {}
        zamechanie(VAZHNO, "весь сайт", "нет ceny.json — таблицы цен не соберутся, "
                                        "прогоните npm run sajt-ceny")

    prajs = io.open(os.path.join(KOREN, "data", "prices.ts"), encoding="utf-8").read()
    prajs_ceny = {int(x) for x in re.findall(r"\b(\d{1,6})\b", prajs)}
    net_v_prajse = re.findall(r"'([^']*)',", prajs[prajs.index("NET_V_PRAJSE = ["):
                                                  prajs.index("NET_V_PRAJSE = [") + 2500])

    stranicy = sobrat_stranicy(env, ceny)
    proverit_mety(stranicy)
    proverit_razmetku(stranicy)
    proverit_obeshchaniya(stranicy, net_v_prajse)
    proverit_ceny(stranicy, prajs_ceny)
    proverit_sirot(stranicy)
    proverit_geo(stranicy)
    proverit_slagi()
    proverit_kartu(stranicy)

    # Машинный вывод для панели: та же проверка, только в JSON.
    if "--json" in sys.argv:
        print(json.dumps({
            "stranic": len(stranicy),
            "kritichno": [{"stranica": a, "tekst": b} for a, b in KRITICHNO],
            "vazhno": [{"stranica": a, "tekst": b} for a, b in VAZHNO],
            "potom": [{"stranica": a, "tekst": b} for a, b in POTOM],
        }, ensure_ascii=False))
        return 1 if KRITICHNO else 0

    print()
    print("ПРОВЕРКА САЙТА · страниц собрано: %d" % len(stranicy))
    print("=" * 66)
    vsego = 0
    for nazvanie, spisok_z in (("КРИТИЧНО", KRITICHNO), ("ВАЖНО", VAZHNO), ("ПОТОМ", POTOM)):
        if not spisok_z:
            continue
        vsego += len(spisok_z)
        print("\n%s — %d:" % (nazvanie, len(spisok_z)))
        for stranica, tekst in spisok_z:
            print("  · %-26s %s" % (stranica, tekst))
    if vsego == 0:
        print("\nЗамечаний нет. Это и есть нужный результат.")
    else:
        print("\nВсего замечаний: %d. Критичные чиним первыми." % vsego)
    print()
    return 1 if KRITICHNO else 0


if __name__ == "__main__":
    sys.exit(main())
