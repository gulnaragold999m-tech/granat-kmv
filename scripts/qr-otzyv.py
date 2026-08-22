# -*- coding: utf-8 -*-
"""QR-код на отзыв: granat-kmv.ru/otzyv.

Запуск: python3 scripts/qr-otzyv.py

ПОЧЕМУ АДРЕС НАШ, А НЕ ЯНДЕКСА. QR печатается на бумаге — тейбл-тент
на стойке, вкладыш в заказ, наклейка на пакет. Ссылка на карточку
однажды поменяется, и тираж придётся печатать заново. Наш короткий
адрес не меняется никогда, а куда он ведёт, решает `kor_otzyv` в app.py.

ПОЧЕМУ КОРРЕКЦИЯ H. Это самый высокий уровень восстановления: код
читается, даже если четверть площади залита, затёрта или закрыта
логотипом. Тейбл-тент на стойке в типографии пачкается краской —
проверено жизнью, а не теорией.

Файлы кладутся в firmennyj-stil/qr/: PNG для макета, SVG для печати
в любом размере без потери качества.
"""
import os

import qrcode
import qrcode.image.svg
from qrcode.constants import ERROR_CORRECT_H

ADRES = "https://granat-kmv.ru/otzyv"
KUDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "firmennyj-stil", "qr")


def sobrat():
    os.makedirs(KUDA, exist_ok=True)

    # box_size=20 даёт около 800 пикселей по стороне — этого хватает
    # и на тейбл-тент А5, и на наклейку 50×50 мм.
    kod = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H,
                        box_size=20, border=4)
    kod.add_data(ADRES)
    kod.make(fit=True)

    png = os.path.join(KUDA, "qr-otzyv.png")
    # Цвета фирменные: гранатовый на белом. Светлее гранатового брать
    # нельзя — сканеру нужен контраст, а не оттенок.
    kod.make_image(fill_color="#4A0E17", back_color="white").save(png)

    svg = os.path.join(KUDA, "qr-otzyv.svg")
    kod_svg = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=20, border=4)
    kod_svg.add_data(ADRES)
    kod_svg.make(fit=True)
    kod_svg.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(svg)

    for f in (png, svg):
        print(f"{os.path.basename(f)}: {os.path.getsize(f)} байт")
    print(f"ведёт на {ADRES}")


if __name__ == "__main__":
    sobrat()
