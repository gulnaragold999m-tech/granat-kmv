# -*- coding: utf-8 -*-
"""Брендированные наклейки на упаковку — лист А4 для печати и резки.

    python3 scripts/naklejki.py            # всё сразу: круглые 50 и 40 мм, квадратные 60
    python3 scripts/naklejki.py 40         # только круглые 40 мм

ЗАЧЕМ. Идея владелицы 21.08.2026: «напечатали, положили в упаковку,
наклеили наклейку». Наклейка заклеивает пакет и подписывает работу:
человек несёт заказ через город, и знак студии видят посторонние.

ПОЧЕМУ БЕРЁМ ГОТОВЫЙ ЛОГОТИП, А НЕ РИСУЕМ НОВЫЙ. `granat-logo-dlya-pechati`
уже круглый: кольцо, «ДИЗАЙНЕРСКАЯ СТУДИЯ» по верхней дуге, вензель,
«ГРАНАТ» и адрес сайта по нижней. Это и есть наклейка — второй знак
рядом с первым только размыл бы узнавание.

ПОЧЕМУ БЕЗ QR. На круге 50 мм QR читается только в ущерб знаку —
проверено на открытке: код меньше 36 мм на струйнике замыливается.
Адрес сайта в знаке уже есть, а просьба об отзыве живёт на открытке,
которая лежит внутри упаковки.

ЧТО НА ЛИСТЕ. Наклейки в сетке плюс тонкая линия реза. Линия светлая:
если нож чуть уйдёт, на наклейке не останется тёмного следа.

ДВА ВИДА, И ЭТО НЕ ПРИХОТЬ. Круглые режутся вручную и долго — по прайсу
это отдельная позиция. Квадратные 60×60 режет резак прямыми линиями,
то есть быстро и без брака. Начинать стоит с квадратных, круглые —
когда захочется вида.

Фон у логотипа квадратный, поэтому для круглых наклеек он обрезается
по кругу маской: иначе на листе получаются квадраты с кругом внутри,
и резать не по чему.

По прайсу это `NAKLEJKI`: круглые 40–50 мм, 50 шт. — 600 ₽, 100 шт. —
950 ₽. Один лист А4 даёт 15 штук по 50 мм или 24 по 40 мм.
"""

import os
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGOTIP = os.path.join(KORNI, "firmennyj-stil", "granat-logo-dlya-pechati-1500.png")
KUDA_SHABLON = os.path.join(KORNI, "firmennyj-stil", "qr", "naklejki-{}mm-a4.pdf")

POLE = 10 * mm          # отступ от края листа: принтер не печатает впритык
PROMEZHUTOK = 3 * mm    # между наклейками, чтобы было куда вести нож
LINIYA_REZA = HexColor("#C9B79B")


def obrezat_v_krug(put):
    """Логотип в круге, всё за кругом прозрачно.

    Файл логотипа квадратный, с гранатовой заливкой до самых углов.
    Разложенный как есть, он даёт лист квадратов, а не кругов.
    """
    img = Image.open(put).convert("RGBA")
    maska = Image.new("L", img.size, 0)
    ImageDraw.Draw(maska).ellipse((0, 0, img.size[0] - 1, img.size[1] - 1), fill=255)
    img.putalpha(maska)
    return img


def razlozhit(diametr_mm, kruglaya=True):
    diametr = diametr_mm * mm
    shirina, vysota = A4
    shag = diametr + PROMEZHUTOK

    stolbcov = int((shirina - 2 * POLE + PROMEZHUTOK) // shag)
    ryadov = int((vysota - 2 * POLE + PROMEZHUTOK) // shag)
    if stolbcov < 1 or ryadov < 1:
        raise SystemExit(f"наклейка {diametr_mm} мм на А4 не помещается")

    # Сетку центрируем: поля сверху и снизу равные, лист режется ровнее.
    zanyato_x = stolbcov * shag - PROMEZHUTOK
    zanyato_y = ryadov * shag - PROMEZHUTOK
    nachalo_x = (shirina - zanyato_x) / 2
    nachalo_y = (vysota - zanyato_y) / 2

    kuda = KUDA_SHABLON.format(f"{diametr_mm}" if kruglaya else f"kv{diametr_mm}")
    c = canvas.Canvas(kuda, pagesize=A4)
    logo = ImageReader(obrezat_v_krug(LOGOTIP) if kruglaya else LOGOTIP)

    for ryad in range(ryadov):
        for stolbec in range(stolbcov):
            x = nachalo_x + stolbec * shag
            y = nachalo_y + ryad * shag
            c.drawImage(logo, x, y, diametr, diametr, mask="auto")
            # Линия реза поверх картинки: режут по видимой линии,
            # а не на глаз.
            c.setStrokeColor(LINIYA_REZA)
            c.setLineWidth(0.3)
            if kruglaya:
                c.circle(x + diametr / 2, y + diametr / 2, diametr / 2, stroke=1, fill=0)
            else:
                c.rect(x, y, diametr, diametr, stroke=1, fill=0)

    c.setFont("Helvetica", 6)
    c.setFillColor(HexColor("#9A8A78"))
    forma = "round" if kruglaya else "square"
    c.drawString(POLE, 5 * mm,
                 f"granat-kmv.ru  ·  {diametr_mm} mm {forma}  ·  {stolbcov * ryadov} pcs")
    c.showPage()
    c.save()
    print(f"{os.path.basename(kuda)}: {stolbcov}×{ryadov} = {stolbcov * ryadov} шт., "
          f"{os.path.getsize(kuda)} байт")
    return kuda


if __name__ == "__main__":
    if not os.path.exists(LOGOTIP):
        raise SystemExit(f"нет логотипа: {LOGOTIP}")
    if len(sys.argv) > 1:
        razlozhit(int(sys.argv[1]))
    else:
        razlozhit(50)
        razlozhit(40)
        razlozhit(60, kruglaya=False)
    print("Печатать на самоклеящейся бумаге А4, резать по светлым линиям.")
    print("Квадратные режутся резаком за минуту, круглые — вручную.")
