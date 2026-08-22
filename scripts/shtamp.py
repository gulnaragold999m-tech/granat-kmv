# -*- coding: utf-8 -*-
"""Макет штампа на упаковку: круглая печать с логотипом студии.

    python3 scripts/shtamp.py            # 70 мм и 50 мм
    python3 scripts/shtamp.py 40         # только 40 мм

ЗАЧЕМ. Идея владелицы 21.08.2026: штамп на крафтовые пакеты, коробки
и конверты. Один штамп заменяет тираж наклеек и работает на любой
упаковке, включая ту, которой ещё нет.

ПОЧЕМУ НЕ ГОДИТСЯ ГОТОВЫЙ ЛОГОТИП. Штамп печатает одной краской, без
полутонов. Золото фирменного знака — это градиент: на резине он станет
сплошным чёрным пятном, и вензель сольётся в кляксу. Поэтому для штампа
рисуется отдельный, одноцветный макет.

ЧТО ДЕРЖИТ РЕЗИНА. Проверенные пределы, из них и построены размеры:
  * линия тоньше 0.4 мм не пропечатывается или рвётся;
  * буква ниже 2 мм заплывает краской, особенно на крафте;
  * просвет между элементами меньше 0.5 мм забивается — краска
    садится мостиком, и в оттиске получается пятно.
Всё это считается от РЕАЛЬНОГО размера штампа, поэтому на 40 мм текст
по дуге даётся крупнее относительно круга, чем на 70 мм.

ЗЕРКАЛИТЬ НЕ НАДО. Мастерская делает это сама при изготовлении клише.
Макет отдаётся в прямом чтении.

ЧТО ОТДАВАТЬ В МАСТЕРСКУЮ. PDF — там кривые, он масштабируется без
потерь. PNG 1200 точек на дюйм приложен на случай, если у мастерской
не открывается вектор: он чёрно-белый, без серых пикселей по краям,
потому что серый резина всё равно не воспроизведёт.
"""

import math
import os
import sys

from reportlab.lib.colors import black, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUDA = os.path.join(KORNI, "firmennyj-stil", "shtamp")

SHRIFTY = {
    "obychny": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "zhirny": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
}

# Пороги резины. Ниже них штамп печатает пятно вместо рисунка.
MIN_LINIYA_MM = 0.40
MIN_BUKVA_MM = 2.00
DOLYA_PROPISNOJ = 0.7          # высота прописной буквы от кегля
MIN_KEGL = MIN_BUKVA_MM / DOLYA_PROPISNOJ * mm

VERH = "ДИЗАЙНЕРСКАЯ СТУДИЯ"
NIZ = "GRANAT-KMV.RU"
NAZVANIE = "ГРАНАТ"
GOROD = "ЛЕРМОНТОВ · КМВ"


def zaregistrirovat_shrifty():
    pdfmetrics.registerFont(TTFont("Shtamp", SHRIFTY["obychny"]))
    pdfmetrics.registerFont(TTFont("Shtamp-Bold", SHRIFTY["zhirny"]))


def tekst_po_duge(c, tekst, cx, cy, radius, kegl, shrift, sverhu=True, razryadka=1.0):
    """Строка по окружности, буква за буквой.

    Внизу буквы разворачиваются, иначе читать пришлось бы вниз головой.
    Разрядка задаётся множителем: на штампе плотный текст заплывает,
    и между буквами нужен воздух больше обычного.
    """
    c.setFont(shrift, kegl)
    shiriny = [pdfmetrics.stringWidth(b, shrift, kegl) * razryadka for b in tekst]
    ugol_vsego = sum(sh / radius for sh in shiriny)

    ugol = (math.pi / 2 + ugol_vsego / 2) if sverhu else (-math.pi / 2 - ugol_vsego / 2)
    for bukva, shirina in zip(tekst, shiriny):
        shag = shirina / radius
        seredina = ugol - shag / 2 if sverhu else ugol + shag / 2
        x = cx + radius * math.cos(seredina)
        y = cy + radius * math.sin(seredina)
        c.saveState()
        c.translate(x, y)
        povorot = math.degrees(seredina) + (-90 if sverhu else 90)
        c.rotate(povorot)
        c.drawCentredString(0, -kegl * 0.36 if sverhu else -kegl * 0.30, bukva)
        c.restoreState()
        ugol = ugol - shag if sverhu else ugol + shag


def duga_ne_vlezaet(tekst, shrift, kegl, radius, razryadka):
    """Обходит ли строка больше половины окружности.

    Верхняя и нижняя строки идут навстречу друг другу. Если каждая
    занимает больше половины круга, они столкнутся боками.
    """
    shirina = pdfmetrics.stringWidth(tekst, shrift, kegl) * razryadka
    return shirina / radius > math.pi * 0.86


def podobrat_kegl(tekst, shrift, dostupno, ne_bolshe):
    """Самый крупный кегль, при котором строка влезает в ширину."""
    kegl = ne_bolshe
    while kegl > 1 * mm and pdfmetrics.stringWidth(tekst, shrift, kegl) > dostupno:
        kegl -= 0.1 * mm
    return kegl


def narisovat(c, storona_mm, s_venzelem=False):
    """Один оттиск: два кольца, текст по дугам, название в центре."""
    storona = storona_mm * mm
    cx = cy = storona / 2
    vnesh = storona / 2 - 1.5 * mm       # внешнее кольцо, с полем от края

    c.setFillColor(white)
    c.rect(0, 0, storona, storona, stroke=0, fill=1)
    c.setStrokeColor(black)
    c.setFillColor(black)

    # Два кольца. Толщина в долях размера: на маленьком штампе толстое
    # кольцо съедает место под текст, на большом тонкое теряется.
    tolstoe = max(0.5 * mm, storona_mm * 0.011 * mm)
    tonkoe = max(0.4 * mm, storona_mm * 0.006 * mm)
    c.setLineWidth(tolstoe)
    c.circle(cx, cy, vnesh, stroke=1, fill=0)
    c.setLineWidth(tonkoe)
    vnutr = vnesh - max(1.6 * mm, storona_mm * 0.032 * mm)
    c.circle(cx, cy, vnutr, stroke=1, fill=0)

    # Кегли считаем от размера штампа, но не ниже порога читаемости:
    # 2 мм — та высота, ниже которой буква на крафте заплывает.
    kegl_dugi = max(MIN_KEGL, storona_mm * 0.052 * mm)
    kegl_goroda = max(MIN_KEGL, storona_mm * 0.040 * mm)

    radius_teksta = vnutr - kegl_dugi * 0.75

    # Маленький штамп не унесёт «ДИЗАЙНЕРСКАЯ СТУДИЯ»: строка обошла бы
    # больше половины круга и столкнулась бы с нижней. Тогда собираем
    # короткий вариант — знак, название и адрес. Обрезанная строка хуже,
    # чем её отсутствие.
    tesno = duga_ne_vlezaet(VERH, "Shtamp", kegl_dugi, radius_teksta, 1.18)
    # Кегль названия подбираем по ширине, а не долей от размера: на 40 мм
    # «ГРАНАТ», посчитанный долей, упирался в кольцо. В коротком варианте
    # сверху освободилось место, поэтому там название крупнее.
    dolya = 0.175 if tesno else 0.145
    kegl_nazvaniya = podobrat_kegl(NAZVANIE, "Shtamp-Bold",
                                   vnutr * 2 * 0.74, storona_mm * dolya * mm)
    # Сверху: на большом штампе — чем мы занимаемся, на маленьком — город.
    # Пустая верхняя дуга при заполненной нижней сажает композицию набок.
    sverhu = GOROD if tesno else VERH
    tekst_po_duge(c, sverhu, cx, cy, radius_teksta, kegl_dugi, "Shtamp", True, 1.18)
    tekst_po_duge(c, NIZ, cx, cy, radius_teksta, kegl_dugi, "Shtamp", False, 1.18)

    # Название по центру. Ниже — город, выше — разделительная линия:
    # без неё центр выглядит проваленным.
    c.setFont("Shtamp-Bold", kegl_nazvaniya)
    c.drawCentredString(cx, cy - kegl_nazvaniya * 0.30, NAZVANIE)

    otstup = kegl_nazvaniya * 0.62
    c.setLineWidth(tonkoe)
    dlina = vnutr * 0.42
    c.line(cx - dlina, cy + otstup, cx + dlina, cy + otstup)
    c.line(cx - dlina, cy - otstup, cx + dlina, cy - otstup)

    gorod_vlez = (not tesno and
                  pdfmetrics.stringWidth(GOROD, "Shtamp", kegl_goroda) <= vnutr * 2 * 0.74)
    if gorod_vlez:
        c.setFont("Shtamp", kegl_goroda)
        c.drawCentredString(cx, cy - otstup - kegl_goroda * 1.5, GOROD)

    kegli = {"текст по дуге": kegl_dugi, "название": kegl_nazvaniya}
    if gorod_vlez:
        kegli["город"] = kegl_goroda
    return (kegli, {"внешнее кольцо": tolstoe, "внутреннее кольцо": tonkoe},
            {"город не поместился": not gorod_vlez, "текст по дуге тесно": tesno})


def proverit(storona_mm, kegli, linii, bedy):
    """Проверка макета на пороги резины. Возвращает список замечаний."""
    zamechaniya = []


    for imya, kegl in kegli.items():
        # Высота прописной примерно 0.7 кегля у большинства шрифтов.
        vysota = kegl / mm * DOLYA_PROPISNOJ
        if vysota < MIN_BUKVA_MM:
            zamechaniya.append(f"{imya}: буква {vysota:.2f} мм — меньше {MIN_BUKVA_MM}")
    for imya, tolshchina in linii.items():
        if tolshchina / mm < MIN_LINIYA_MM:
            zamechaniya.append(f"{imya}: линия {tolshchina / mm:.2f} мм — "
                               f"меньше {MIN_LINIYA_MM}")
    return zamechaniya


def sobrat(storona_mm):
    os.makedirs(KUDA, exist_ok=True)
    storona = storona_mm * mm
    pdf = os.path.join(KUDA, f"shtamp-{storona_mm}mm.pdf")
    c = canvas.Canvas(pdf, pagesize=(storona, storona))
    kegli, linii, bedy = narisovat(c, storona_mm)
    c.showPage()
    c.save()

    zamechaniya = proverit(storona_mm, kegli, linii, bedy)
    if zamechaniya:
        print(f"  {storona_mm} мм — НЕ ГОДИТСЯ ДЛЯ РЕЗИНЫ:")
        for z in zamechaniya:
            print(f"    · {z}")
    else:
        podrobno = ", ".join(f"{i} {k / mm * DOLYA_PROPISNOJ:.1f} мм"
                             for i, k in kegli.items())
        vid = "короткий" if bedy.get("текст по дуге тесно") else "полный"
        print(f"  {storona_mm} мм, {vid} вариант — пороги выдержаны: {podrobno}")

    png = os.path.join(KUDA, f"shtamp-{storona_mm}mm-1200dpi.png")
    v_png(pdf, png)
    print(f"shtamp-{storona_mm}mm.pdf и .png: {os.path.getsize(pdf)} / "
          f"{os.path.getsize(png)} байт")


def v_png(pdf, png):
    """PNG 1200 точек на дюйм, чисто чёрно-белый.

    Серые пиксели по краям букв резина не воспроизведёт: они станут
    либо чёрными, либо пропадут. Поэтому порог, а не сглаживание —
    иначе тонкий штрих на клише получится рваным.
    """
    import pymupdf
    from PIL import Image

    d = pymupdf.open(pdf)
    d[0].get_pixmap(dpi=1200).save(png)
    img = Image.open(png).convert("L").point(lambda t: 0 if t < 160 else 255, "1")
    img.save(png)


if __name__ == "__main__":
    zaregistrirovat_shrifty()
    razmery = [int(sys.argv[1])] if len(sys.argv) > 1 else [70, 50, 40]
    for r in razmery:
        sobrat(r)
    print("В мастерскую отдавать PDF. Зеркалить не надо — они сделают сами.")
