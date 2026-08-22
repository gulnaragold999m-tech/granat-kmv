# -*- coding: utf-8 -*-
"""Полоса-пломба на клапан упаковки: «Спасибо, что выбрали нас».

    python3 scripts/plomba.py

ЗАЧЕМ ИМЕННО ПЛОМБА. Владелица 21.08.2026 попросила, чтобы на упаковке
было «спасибо, что выбрали нас». Снаружи эту фразу читают посторонние,
которым она ничего не говорит; на открытке внутри её читают уже после
того, как увидели заказ, — и там она конкурирует с «Спасибо за заказ».

Место, где фразу нельзя не прочитать, — секунда вскрытия: полоса идёт
через клапан, и её рвут руками. Работает она там не словами, а жестом.
Заодно держит клапан закрытым и не даёт содержимому выпасть.

ПОЧЕМУ НЕ ПОЯСОК ВОКРУГ УПАКОВКИ. У конверта А4+ 353×250 обхват около
510 мм, у коробки 230×170×20 — около 380 мм, а лист А4 даёт 297.
Поясок целиком печатается только с плоттера и другой бумагой. Пломба
через клапан даёт то же впечатление за меньшие деньги.

ВОСЕМЬ ШТУК С ЛИСТА А4, около 2 ₽ за штуку по бумаге. Клеится
двусторонним скотчем или каплей клея-карандаша.
"""

import os

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUDA = os.path.join(KORNI, "firmennyj-stil", "qr", "plomba-spasibo-a4.pdf")

SHIRINA, VYSOTA = 140 * mm, 40 * mm
VYLET = 1.5 * mm
POLE = 8 * mm
PROMEZHUTOK = 4 * mm

# Цвета сняты с логотипа, как и на открытке.
GRANAT = HexColor("#5A1020")
ZOLOTO = HexColor("#C79A34")
LINIYA_REZA = HexColor("#C9B79B")

SHRIFTY = {
    "obychny": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "zhirny": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

FRAZA = "СПАСИБО, ЧТО ВЫБРАЛИ НАС"
SAJT = "granat-kmv.ru"


def zaregistrirovat_shrifty():
    pdfmetrics.registerFont(TTFont("Plomba", SHRIFTY["obychny"]))
    pdfmetrics.registerFont(TTFont("Plomba-Bold", SHRIFTY["zhirny"]))


def odna(c, x, y):
    """Одна полоса: фон с вылетом, рез по номиналу."""
    c.setFillColor(GRANAT)
    c.rect(x - VYLET, y - VYLET, SHIRINA + 2 * VYLET, VYSOTA + 2 * VYLET,
           stroke=0, fill=1)

    # Тонкая золотая рамка внутри — та же, что на открытке: полоса
    # должна читаться как часть комплекта, а не как отдельная затея.
    c.setStrokeColor(ZOLOTO)
    c.setLineWidth(0.5)
    c.rect(x + 4 * mm, y + 4 * mm, SHIRINA - 8 * mm, VYSOTA - 8 * mm,
           stroke=1, fill=0)

    # Фраза с разрядкой: на узкой полосе плотный текст читается хуже,
    # а разряженный выглядит как надпись, а не как строка из абзаца.
    c.setFont("Plomba-Bold", 11)
    c.setFillColor(ZOLOTO)
    razryazhennaya = " ".join(FRAZA.replace(" ", " "))
    c.drawCentredString(x + SHIRINA / 2, y + VYSOTA / 2 + 1 * mm, razryazhennaya)

    c.setFont("Plomba", 7)
    c.setFillColor(HexColor("#E8D9BD"))
    c.drawCentredString(x + SHIRINA / 2, y + VYSOTA / 2 - 6 * mm, SAJT)

    # Линия реза по номиналу, поверх фона.
    c.setStrokeColor(LINIYA_REZA)
    c.setLineWidth(0.3)
    c.rect(x, y, SHIRINA, VYSOTA, stroke=1, fill=0)


def sobrat():
    zaregistrirovat_shrifty()
    shirina_lista, vysota_lista = A4
    shag_y = VYSOTA + PROMEZHUTOK
    ryadov = int((vysota_lista - 2 * POLE + PROMEZHUTOK) // shag_y)
    x = (shirina_lista - SHIRINA) / 2
    nachalo_y = (vysota_lista - (ryadov * shag_y - PROMEZHUTOK)) / 2

    c = canvas.Canvas(KUDA, pagesize=A4)
    for r in range(ryadov):
        odna(c, x, nachalo_y + r * shag_y)

    c.setFont("Plomba", 6.5)
    c.setFillColor(HexColor("#9A8A78"))
    c.drawString(POLE, 5 * mm,
                 f"granat-kmv.ru  ·  пломба 140×40 мм, {ryadov} шт.")
    c.showPage()
    c.save()
    print(f"{os.path.basename(KUDA)}: {ryadov} шт. на листе, "
          f"{os.path.getsize(KUDA)} байт")
    print("Клеить через клапан конверта или коробки — её рвут при вскрытии.")


if __name__ == "__main__":
    sobrat()
