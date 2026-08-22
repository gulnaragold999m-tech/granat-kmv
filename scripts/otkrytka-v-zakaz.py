# -*- coding: utf-8 -*-
"""Открытка-вкладыш в заказ: спасибо, что мы ещё умеем и просьба об отзыве.

    python3 scripts/otkrytka-v-zakaz.py

ЗАЧЕМ. Идея владелицы 21.08.2026: «при выдаче заказа в упаковку
вкладывать как открытку». Табличку на стойке человек видит десять
секунд, открытку забирает домой и достаёт вечером, когда есть минута.

ЧТО РЕШАЕТ ОТКРЫТКА, кроме благодарности. Клиент, забравший визитки,
обычно не знает, что здесь же делают сайты и ботов, и что грамоту
печатают от одной штуки. Он уходит и заказывает это в другом месте —
не потому что дешевле, а потому что не знал. Поэтому оборот — не рассказ
о студии, а три факта, которые ему пригодятся.

ЧЕГО ЗДЕСЬ НЕТ НАМЕРЕННО:
  * «Спасибо, что выбрали нас», «команда профессионалов», «на рынке
    с такого-то года» — штампы, читатель проскакивает их глазами;
  * сколько лет студия работает — этого факта в проекте нет, а выдумывать
    цифру на печатной продукции нельзя. Владелица назовёт год — впишем;
  * ни слова про подарок или скидку за отзыв: это оплата отзыва,
    за неё Яндекс снимает отзывы и понижает карточку. Разбор —
    в docs/otzyvy-yandex-karty.md.

ВСЕ ЦИФРЫ — ИЗ ПРАЙСА `data/prices.ts`: грамота от одной штуки
от 150 ₽ (SHTUCHNAYA_A4.roznicaSertifikat), лид-бот от 15 000 ₽
(SAJTY_I_BOTY). Поменяется прайс — поменять и здесь.
"""

import os

from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QR = os.path.join(KORNI, "firmennyj-stil", "qr", "qr-otzyv.png")
KUDA = os.path.join(KORNI, "firmennyj-stil", "qr", "otkrytka-v-zakaz.pdf")
ZNAK = os.path.join(KORNI, "firmennyj-stil", "granat-logo-dlya-pechati-1500.png")

SHIRINA, VYSOTA = 105 * mm, 148 * mm      # А6
VYLET = 2 * mm
POLNAYA_SHIRINA = SHIRINA + 2 * VYLET
POLNAYA_VYSOTA = VYSOTA + 2 * VYLET

# Цвета сняты с логотипа (firmennyj-stil/sobrat.mjs), а не подобраны
# на глаз: плоский #4A0E17 рядом со знаком читается почти чёрным,
# а золото #C9A227 заметно желтее и зеленее фирменного.
GRANAT = HexColor("#5A1020")
ZOLOTO = HexColor("#C79A34")
PESOK = HexColor("#F9F3EB")

SHRIFTY = {
    "obychny": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "zhirny": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

# Три факта для оборота. Каждый проверяем по data/prices.ts.
FAKTY = [
    ("Грамоты и сертификаты —", "от одной штуки, от 150 ₽"),
    ("Сайты и Telegram-боты —", "пишем кодом, исходники ваши"),
    ("Макет присылайте почтой —", "мессенджер сжимает картинку"),
]


def znak_v_kruge():
    """Знак с прозрачным фоном за кругом.

    У файла логотипа гранатовая заливка идёт до самых углов. На тёмной
    открытке она даёт видимый квадрат вокруг круга — та же ловушка,
    что была на листе наклеек.
    """
    img = Image.open(ZNAK).convert("RGBA")
    maska = Image.new("L", img.size, 0)
    ImageDraw.Draw(maska).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
    img.putalpha(maska)
    return img


def zaregistrirovat_shrifty():
    pdfmetrics.registerFont(TTFont("Osnovnoy", SHRIFTY["obychny"]))
    pdfmetrics.registerFont(TTFont("Osnovnoy-Bold", SHRIFTY["zhirny"]))


def metki_reza(c):
    c.setStrokeColor(HexColor("#808080"))
    c.setLineWidth(0.25)
    dlina = 3 * mm
    for x in (VYLET, VYLET + SHIRINA):
        for y in (VYLET, VYLET + VYSOTA):
            c.line(x, y - dlina if y == VYLET else y + dlina, x, y)
            c.line(x - dlina if x == VYLET else x + dlina, y, x, y)


def po_centru(c, tekst, y, razmer, shrift="Osnovnoy", cvet=white, shag=None):
    c.setFont(shrift, razmer)
    c.setFillColor(cvet)
    c.drawCentredString(POLNAYA_SHIRINA / 2, y, tekst)
    return y - (shag or razmer * 1.45)


def lico(c):
    """Только благодарность и слоган. Тесная открытка не читается."""
    c.setFillColor(GRANAT)
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    # Тонкая золотая рамка: открытка должна выглядеть как открытка,
    # а не как листовка. Внутрь обрезного размера, с запасом на подрезку.
    c.setStrokeColor(ZOLOTO)
    c.setLineWidth(0.6)
    c.rect(VYLET + 7 * mm, VYLET + 7 * mm, SHIRINA - 14 * mm, VYSOTA - 14 * mm,
           stroke=1, fill=0)

    # Знак вместо набранной строки: он несёт и название, и род занятий,
    # и адрес сайта — всё то, что раньше писалось словами мелким кеглем.
    znak = 36 * mm
    verh_znaka = VYLET + VYSOTA - 30 * mm - znak
    c.drawImage(ImageReader(znak_v_kruge()), (POLNAYA_SHIRINA - znak) / 2,
                verh_znaka, znak, znak, mask="auto")

    y = verh_znaka - 16 * mm
    y = po_centru(c, "Спасибо", y, 24, "Osnovnoy-Bold", white, 11 * mm)
    y = po_centru(c, "за заказ", y, 24, "Osnovnoy-Bold", white, 18 * mm)

    c.setStrokeColor(ZOLOTO)
    c.setLineWidth(0.7)
    c.line(POLNAYA_SHIRINA / 2 - 16 * mm, y + 4 * mm,
           POLNAYA_SHIRINA / 2 + 16 * mm, y + 4 * mm)

    y -= 6 * mm
    po_centru(c, "Ваш бизнес запомнят", y, 10.5, "Osnovnoy", HexColor("#E8D9BD"), 6 * mm)
    po_centru(c, "с первого взгляда", y - 6 * mm, 10.5, "Osnovnoy", HexColor("#E8D9BD"))
    metki_reza(c)


def oborot(c):
    """Три факта, просьба об отзыве и QR."""
    c.setFillColor(PESOK)
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    y = VYLET + VYSOTA - 13 * mm
    y = po_centru(c, "ЧТО МЫ ЕЩЁ УМЕЕМ", y, 8, "Osnovnoy-Bold", ZOLOTO, 8.5 * mm)

    for zagolovok, podrobnost in FAKTY:
        y = po_centru(c, zagolovok, y, 9, "Osnovnoy-Bold", GRANAT, 4.6 * mm)
        y = po_centru(c, podrobnost, y, 9, "Osnovnoy", HexColor("#5A4038"), 6.8 * mm)

    y -= 2 * mm
    c.setStrokeColor(HexColor("#D8C7A8"))
    c.setLineWidth(0.6)
    c.line(VYLET + 18 * mm, y, VYLET + SHIRINA - 18 * mm, y)

    y -= 7 * mm
    y = po_centru(c, "Расскажите, как получилось", y, 11, "Osnovnoy-Bold", GRANAT, 5.2 * mm)
    y = po_centru(c, "Нас находят по отзывам на Яндекс Картах", y, 8.5, "Osnovnoy",
                  HexColor("#7A6055"), 6.5 * mm)

    storona = 36 * mm
    x = (POLNAYA_SHIRINA - storona) / 2
    verh = y - storona
    c.setFillColor(white)
    c.roundRect(x - 3 * mm, verh - 3 * mm, storona + 6 * mm, storona + 6 * mm,
                2 * mm, stroke=0, fill=1)
    c.drawImage(ImageReader(QR), x, verh, storona, storona, mask="auto")

    po_centru(c, "granat-kmv.ru/otzyv", verh - 7 * mm, 8.5, "Osnovnoy", GRANAT)

    po_centru(c, "Лермонтов, Нагорная улица, 2/1, второй этаж", VYLET + 12 * mm, 7.5,
              "Osnovnoy", HexColor("#7A6055"))
    po_centru(c, "+7 999 244-99-99  ·  granat-kmv.ru", VYLET + 7 * mm, 7.5,
              "Osnovnoy", GRANAT)
    metki_reza(c)


def sobrat():
    if not os.path.exists(QR):
        raise SystemExit(f"нет QR-кода: {QR}\nсначала python3 scripts/qr-otzyv.py")
    zaregistrirovat_shrifty()
    c = canvas.Canvas(KUDA, pagesize=(POLNAYA_SHIRINA, POLNAYA_VYSOTA))
    lico(c)
    c.showPage()
    oborot(c)
    c.showPage()
    c.save()
    print(f"{os.path.basename(KUDA)}: {os.path.getsize(KUDA)} байт")
    print("А6, две стороны, припуск 2 мм, метки реза.")
    print("По прайсу это раздел «Открытки, поздравления», строка А6.")


if __name__ == "__main__":
    sobrat()
