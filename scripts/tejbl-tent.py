# -*- coding: utf-8 -*-
"""Тейбл-тент на стойку: просьба оставить отзыв с QR-кодом.

    python3 scripts/tejbl-tent.py

ЗАЧЕМ. Отзывы на Яндекс Картах приводят новых клиентов, но человек
пишет их, только пока держит заказ в руках и доволен. Табличка
на стойке — единственный способ попросить каждого, ничего не говоря.

ЧТО ДЕЛАЕТ. Рисует две стороны А5 в PDF: лицо с QR-кодом и оборот
с примером отзыва. Обрезной размер 148×210 мм плюс припуск 2 мм
с каждой стороны, метки реза по углам, безопасное поле для текста.
Текст остаётся вектором и печатается острым — PNG на бумаге мылит.

ПРАВИЛА, КОТОРЫЕ ЗАШИТЫ В ТЕКСТ. Разбор в docs/otzyvy-yandex-karty.md:
  * ни слова про подарок, скидку или бонус за отзыв — это оплата
    отзыва, за неё Яндекс снимает отзывы и понижает карточку;
  * просим ВСЕХ одинаково, без вопроса «понравилось ли вам» и без
    развилки для недовольных: фильтрация по настроению запрещена;
  * пример отзыва ПОКАЗЫВАЕМ, но не диктуем — одинаковые отзывы
    площадка вычисляет и снимает.

QR ведёт на granat-kmv.ru/otzyv — наш постоянный адрес. Ссылка
на карточку однажды поменяется, и тираж пришлось бы печатать заново.
"""

import os

from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QR = os.path.join(KORNI, "firmennyj-stil", "qr", "qr-otzyv.png")
KUDA = os.path.join(KORNI, "firmennyj-stil", "qr", "tejbl-tent-otzyv.pdf")

SHIRINA, VYSOTA = 148 * mm, 210 * mm     # А5
VYLET = 2 * mm                            # припуск на подрезку
BEZOPASNO = 10 * mm                       # ближе к краю текст не ставим
POLNAYA_SHIRINA = SHIRINA + 2 * VYLET
POLNAYA_VYSOTA = VYSOTA + 2 * VYLET

GRANAT = HexColor("#4A0E17")              # фирменный гранатовый
ZOLOTO = HexColor("#C9A227")

SHRIFTY = {
    "obychny": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "zhirny": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}


def zaregistrirovat_shrifty():
    pdfmetrics.registerFont(TTFont("Osnovnoy", SHRIFTY["obychny"]))
    pdfmetrics.registerFont(TTFont("Osnovnoy-Bold", SHRIFTY["zhirny"]))


def metki_reza(c):
    """Линии по углам, по ним режут. За обрезной размер не заходят."""
    c.setStrokeColor(HexColor("#808080"))
    c.setLineWidth(0.25)
    dlina = 4 * mm
    for x in (VYLET, VYLET + SHIRINA):
        for y in (VYLET, VYLET + VYSOTA):
            c.line(x, y - dlina if y == VYLET else y + dlina, x, y)
            c.line(x - dlina if x == VYLET else x + dlina, y, x, y)


def po_centru(c, tekst, y, razmer, shrift="Osnovnoy", cvet=white, mezhstrochny=None):
    """Строка по центру. Возвращает следующую координату по вертикали."""
    c.setFont(shrift, razmer)
    c.setFillColor(cvet)
    c.drawCentredString(POLNAYA_SHIRINA / 2, y, tekst)
    return y - (mezhstrochny or razmer * 1.45)


def lico(c):
    """Лицевая сторона: просьба и QR."""
    c.setFillColor(GRANAT)
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    y = VYLET + VYSOTA - 24 * mm
    y = po_centru(c, "СТУДИЯ «ГРАНАТ»", y, 9.5, "Osnovnoy-Bold", ZOLOTO, 19 * mm)
    y = po_centru(c, "Понравился заказ?", y, 24, "Osnovnoy-Bold", white, 13 * mm)
    y = po_centru(c, "Расскажите об этом на Яндекс Картах —", y, 11.5, "Osnovnoy", white, 7 * mm)
    y = po_centru(c, "по отзывам нас находят новые клиенты.", y, 11.5, "Osnovnoy", white, 17 * mm)

    # QR крупно: с расстояния вытянутой руки читается от 35 мм, берём
    # с запасом — на стойке телефон держат не вплотную.
    storona = 72 * mm
    x = (POLNAYA_SHIRINA - storona) / 2
    verh = y - storona
    c.setFillColor(white)
    c.roundRect(x - 5 * mm, verh - 5 * mm, storona + 10 * mm, storona + 10 * mm,
                4 * mm, stroke=0, fill=1)
    c.drawImage(ImageReader(QR), x, verh, storona, storona, mask="auto")

    y = verh - 14 * mm
    y = po_centru(c, "Наведите камеру телефона", y, 11.5, "Osnovnoy-Bold", ZOLOTO, 7 * mm)
    po_centru(c, "granat-kmv.ru/otzyv", y, 10.5, "Osnovnoy", white)

    c.setStrokeColor(ZOLOTO)
    c.setLineWidth(0.7)
    c.line(POLNAYA_SHIRINA / 2 - 20 * mm, VYLET + 16 * mm,
           POLNAYA_SHIRINA / 2 + 20 * mm, VYLET + 16 * mm)
    po_centru(c, "Спасибо, что находите минуту", VYLET + 10 * mm, 9, "Osnovnoy",
              HexColor("#E8D9BD"))
    metki_reza(c)


def oborot(c):
    """Оборот: о чём написать. Пример показываем, текст не диктуем."""
    c.setFillColor(HexColor("#F9F3EB"))
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    y = VYLET + VYSOTA - 28 * mm
    y = po_centru(c, "О ЧЁМ НАПИСАТЬ", y, 9.5, "Osnovnoy-Bold", ZOLOTO, 17 * mm)
    y = po_centru(c, "Своими словами —", y, 16, "Osnovnoy-Bold", GRANAT, 9 * mm)
    y = po_centru(c, "и упомяните, что печатали", y, 16, "Osnovnoy-Bold", GRANAT, 15 * mm)

    for stroka in ("Так вас найдут те, кому нужно",
                   "то же самое: приглашения, грамоты,",
                   "визитки, копии документов."):
        y = po_centru(c, stroka, y, 11.5, "Osnovnoy", HexColor("#5A4038"), 7 * mm)

    y -= 12 * mm
    # Пример в рамке: человек видит длину и тон, но списывать неудобно —
    # и правильно, одинаковые отзывы площадка снимает.
    vysota_ramki = 52 * mm
    c.setFillColor(white)
    c.setStrokeColor(HexColor("#D8C7A8"))
    c.setLineWidth(0.7)
    c.roundRect(VYLET + 14 * mm, y - vysota_ramki, SHIRINA - 28 * mm, vysota_ramki,
                3 * mm, stroke=1, fill=1)

    vnutri = y - 12 * mm
    for stroka in ("«Печатали приглашения на свадьбу,",
                   "60 штук. Помогли поправить макет,",
                   "сделали за два дня, бумага плотная.",
                   "Забрали в студии на Нагорной.»"):
        vnutri = po_centru(c, stroka, vnutri, 11, "Osnovnoy", HexColor("#3A2A24"), 9 * mm)

    y = y - vysota_ramki - 18 * mm
    y = po_centru(c, "Это пример, а не образец для списывания:", y, 10, "Osnovnoy",
                  HexColor("#7A6055"), 6.5 * mm)
    po_centru(c, "напишите так, как было у вас.", y, 10, "Osnovnoy", HexColor("#7A6055"))

    po_centru(c, "г. Лермонтов, Нагорная улица, 2/1  ·  +7 999 244-99-99",
              VYLET + 12 * mm, 9, "Osnovnoy", GRANAT)
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
    print("А5, две стороны, припуск 2 мм, метки реза. Печатать на плотной бумаге,")
    print("ламинировать — незаламинированная табличка на стойке живёт неделю.")


if __name__ == "__main__":
    sobrat()
