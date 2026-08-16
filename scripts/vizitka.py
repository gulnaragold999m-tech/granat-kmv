# -*- coding: utf-8 -*-
"""Макет визитки в PDF — сразу пригодный для печати.

    python3 scripts/vizitka.py scripts/vizitki/ambaryan.json

ЗАЧЕМ. 16.08.2026 владелица показала визитку клиента, сделанную в PNG
и пересохранённую в JPG: «не влезла и размытая, это нельзя продать,
а это уже B2B-партнёры». Так и есть — PNG и JPG экранные форматы:
буквы в них состоят из точек, и на бумаге текст мылит. В PDF текст
остаётся вектором и печатается острым при любом размере.

ЧТО ДЕЛАЕТ СКРИПТ. Берёт данные из JSON и рисует две стороны визитки:
обрезной размер 90×50 мм плюс припуск 2 мм с каждой стороны (94×54 мм),
метки реза по углам и безопасное поле, за которое не заходит текст.
Ничего не растрируется: фон — заливка, текст — шрифт, логотип — если
дадут вектор, вставится вектором.

ПОЧЕМУ ПРИПУСК ОБЯЗАТЕЛЕН. Резак всегда уходит на доли миллиметра.
Без припуска по краю вылезет белая полоска, и партия уйдёт в брак.
Поэтому фон рисуется на 2 мм больше во все стороны, а режется по меткам.

ШРИФТ. Взят DejaVu Sans: он есть в системе и знает кириллицу. Для
фирменного стиля клиента шрифт меняется в FONTS ниже — файл .ttf
положить рядом и указать путь.
"""

import json
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# ── Размеры. Меняются только здесь ──────────────────────────────────────
SHIRINA = 90 * mm          # обрезной размер визитки
VYSOTA = 50 * mm
VYLET = 2 * mm             # припуск на подрезку с каждой стороны
BEZOPASNO = 4 * mm         # ближе этого к краю текст не ставим

POLNAYA_SHIRINA = SHIRINA + 2 * VYLET
POLNAYA_VYSOTA = VYSOTA + 2 * VYLET

FONTS = {
    "obychny": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "zhirny": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}


def zaregistrirovat_shrifty():
    pdfmetrics.registerFont(TTFont("Osnovnoy", FONTS["obychny"]))
    pdfmetrics.registerFont(TTFont("Osnovnoy-Bold", FONTS["zhirny"]))


def metki_reza(c):
    """Тонкие линии по углам — по ним режут. За обрезной размер не заходят."""
    c.setStrokeColor(HexColor("#000000"))
    c.setLineWidth(0.25)
    dlina = 3 * mm
    uglov = [
        (VYLET, VYLET), (VYLET + SHIRINA, VYLET),
        (VYLET, VYLET + VYSOTA), (VYLET + SHIRINA, VYLET + VYSOTA),
    ]
    for x, y in uglov:
        znak_x = -1 if x < POLNAYA_SHIRINA / 2 else 1
        znak_y = -1 if y < POLNAYA_VYSOTA / 2 else 1
        c.line(x + znak_x * 0.5 * mm, y, x + znak_x * dlina, y)
        c.line(x, y + znak_y * 0.5 * mm, x, y + znak_y * dlina)


def tekst(c, x, y, stroka, razmer, cvet, zhirny=False, vpravo=False):
    c.setFont("Osnovnoy-Bold" if zhirny else "Osnovnoy", razmer)
    c.setFillColor(HexColor(cvet))
    if vpravo:
        c.drawRightString(x, y, stroka)
    else:
        c.drawString(x, y, stroka)


def storona_licevaya(c, d):
    """Лицо: имя, должность, слоган. Крупно и без мелочи."""
    c.setFillColor(HexColor(d["fon"]))
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    levo = VYLET + BEZOPASNO
    verh = VYLET + VYSOTA - BEZOPASNO

    if d.get("nadpis_sverhu"):
        tekst(c, levo, verh - 3 * mm, d["nadpis_sverhu"].upper(), 6.5,
              d["cvet_dopolnitelny"])

    y = verh - 13 * mm
    for stroka in d["imya"]:
        tekst(c, levo, y, stroka.upper(), 15, d["cvet_glavny"], zhirny=True)
        y -= 6.5 * mm

    if d.get("dolzhnost"):
        tekst(c, levo, y - 1 * mm, d["dolzhnost"], 8, d["cvet_akcent"], zhirny=True)
        y -= 5.5 * mm

    if d.get("slogan"):
        tekst(c, levo, VYLET + BEZOPASNO + 1 * mm, d["slogan"], 6.5,
              d["cvet_dopolnitelny"])


def storona_oborot(c, d):
    """Оборот: контакты. Их читают, поэтому не мельчим."""
    c.setFillColor(HexColor(d["fon"]))
    c.rect(0, 0, POLNAYA_SHIRINA, POLNAYA_VYSOTA, stroke=0, fill=1)

    levo = VYLET + BEZOPASNO
    y = VYLET + VYSOTA - BEZOPASNO - 5 * mm

    if d.get("organizaciya"):
        tekst(c, levo, y, d["organizaciya"].upper(), 9, d["cvet_akcent"], zhirny=True)
        y -= 9 * mm

    for stroka in d["kontakty"]:
        tekst(c, levo, y, stroka, 9, d["cvet_glavny"])
        y -= 6 * mm

    if d.get("sajt"):
        tekst(c, POLNAYA_SHIRINA - VYLET - BEZOPASNO, VYLET + BEZOPASNO + 1 * mm,
              d["sajt"], 7, d["cvet_dopolnitelny"], vpravo=True)


def raskladka_a4(d, vyhod: Path):
    """Лист А4 с визитками встык — столько, сколько влезает.

    90×50 мм при листе 210×297 дают 2 колонки на 5 рядов, то есть
    10 штук. Визитки ставятся вплотную друг к другу нарочно: так режут
    одним проходом по сплошной линии, а не выцеливают каждую отдельно.

    Оборот печатается ЗЕРКАЛЬНО по колонкам. Лист переворачивают через
    длинную сторону, и без зеркала контакты окажутся не на своей визитке —
    брак всей партии, который видно только после резки.
    """
    A4_SH, A4_VY = 210 * mm, 297 * mm
    kolonok, ryadov = 2, 5
    blok_sh, blok_vy = SHIRINA * kolonok, VYSOTA * ryadov
    otstup_x = (A4_SH - blok_sh) / 2
    otstup_y = (A4_VY - blok_vy) / 2

    c = canvas.Canvas(str(vyhod), pagesize=(A4_SH, A4_VY))
    c.setTitle(f"Визитки на А4 — {' '.join(d['imya'])}")

    def linii_reza():
        """Сплошные линии на полях — по ним режут насквозь через лист."""
        c.setStrokeColor(HexColor("#000000"))
        c.setLineWidth(0.25)
        for i in range(kolonok + 1):
            x = otstup_x + i * SHIRINA
            c.line(x, otstup_y - 5 * mm, x, otstup_y - 1 * mm)
            c.line(x, otstup_y + blok_vy + 1 * mm, x, otstup_y + blok_vy + 5 * mm)
        for j in range(ryadov + 1):
            y = otstup_y + j * VYSOTA
            c.line(otstup_x - 5 * mm, y, otstup_x - 1 * mm, y)
            c.line(otstup_x + blok_sh + 1 * mm, y, otstup_x + blok_sh + 5 * mm, y)

    def list_storony(risovat, zerkalo=False):
        for ryad in range(ryadov):
            for kol in range(kolonok):
                mesto = (kolonok - 1 - kol) if zerkalo else kol
                x = otstup_x + mesto * SHIRINA
                y = otstup_y + ryad * VYSOTA
                c.saveState()
                # Внутри каждой ячейки рисуем ту же визитку, но без
                # припусков: соседи стоят встык, вылезать некуда.
                c.translate(x - VYLET, y - VYLET)
                risovat(c, d)
                c.restoreState()
        linii_reza()
        c.showPage()

    list_storony(storona_licevaya)
    list_storony(storona_oborot, zerkalo=True)
    c.save()

    print(f"Готово: {vyhod}")
    print(f"На листе А4: {kolonok * ryadov} визиток ({kolonok}×{ryadov}), встык.")
    print("Страница 1 — лицо, страница 2 — оборот зеркально по колонкам.")


def sobrat(put_k_dannym: Path):
    d = json.loads(put_k_dannym.read_text(encoding="utf-8"))
    zaregistrirovat_shrifty()

    vyhod = put_k_dannym.with_suffix(".pdf")
    c = canvas.Canvas(str(vyhod), pagesize=(POLNAYA_SHIRINA, POLNAYA_VYSOTA))
    c.setTitle(f"Визитка — {' '.join(d['imya'])}")

    storona_licevaya(c, d)
    metki_reza(c)
    c.showPage()

    storona_oborot(c, d)
    metki_reza(c)
    c.showPage()
    c.save()

    print(f"Готово: {vyhod}")
    print(f"Размер листа: {POLNAYA_SHIRINA/mm:.0f}×{POLNAYA_VYSOTA/mm:.0f} мм "
          f"(обрезной {SHIRINA/mm:.0f}×{VYSOTA/mm:.0f} мм, припуск {VYLET/mm:.0f} мм)")
    print("Две страницы: лицо и оборот. Текст вектором, метки реза по углам.")

    # Лист А4 — то, что реально уходит в принтер: печатать по одной
    # визитке на листе расточительно и неудобно резать.
    raskladka_a4(d, put_k_dannym.with_name(put_k_dannym.stem + "-a4.pdf"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Укажите файл с данными: python3 scripts/vizitka.py файл.json")
        raise SystemExit(1)
    sobrat(Path(sys.argv[1]))
