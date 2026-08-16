# -*- coding: utf-8 -*-
"""PDF → JPG в печатном разрешении.

    python3 scripts/pdf-v-jpg.py scripts/vizitki/ambaryan-a4.pdf

ЗАЧЕМ. Приложение принтера у владелицы (Epson Easy Photo Print)
принимает JPG и не открывает PDF. Сам по себе JPG печати не мешает —
мешает экранное разрешение: 72 точки на дюйм вместо 300. Здесь лист
рендерится ровно в 300 dpi, то есть А4 выходит 2480×3508 пикселей,
и текст на бумаге остаётся острым.

Качество JPEG выставлено 95: ниже начинают лезть квадраты вокруг букв,
выше — файл толстеет без видимой разницы.
"""

import sys
from pathlib import Path

import pymupdf

DPI = 300
KACHESTVO = 95


def perevesti(put: Path):
    doc = pymupdf.open(put)
    masshtab = DPI / 72          # PDF считает в точках, 72 на дюйм
    matrica = pymupdf.Matrix(masshtab, masshtab)

    for nomer, stranica in enumerate(doc, start=1):
        pix = stranica.get_pixmap(matrix=matrica, alpha=False)
        imya = put.with_name(f"{put.stem}-{nomer}.jpg")
        pix.pil_save(imya, format="JPEG", quality=KACHESTVO, dpi=(DPI, DPI))
        print(f"{imya.name} — {pix.width}×{pix.height} px, {DPI} dpi")

    print(f"\nСтраница 1 — лицо, страница 2 — оборот (зеркально).")
    print("Печатать с масштабом 100%, «по размеру листа» не ставить.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Укажите PDF: python3 scripts/pdf-v-jpg.py файл.pdf")
        raise SystemExit(1)
    perevesti(Path(sys.argv[1]))
