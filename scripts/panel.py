# -*- coding: utf-8 -*-
"""Панель студии: один экран на тридцать секунд.

  npm run panel   →   panel.html

ЗАЧЕМ. Идея из гайда «SEO-машина»: витрина, которая ничего не меняет,
а только показывает — и рядом с каждой проблемой даёт готовое действие.
Гайд собирает её вокруг статей: сколько написали, хватает ли тем.
У студии статей нет, и такая панель показала бы шесть «не подключено»
из семи блоков.

Поэтому переделано под то, что у студии ЕСТЬ:
  · замечания проверки сайта — единственная живая автопроверка;
  · чего мы не знаем — незаполненные строки прайса, каждая из них
    делает какой-то расчёт прикидкой;
  · открытые хвосты из журнала;
  · последний замер Метрики;
  · сезон: сколько дней до ближайшего пика спроса.

ЧЕСТНОСТЬ ДАННЫХ — главное правило, взято из гайда дословно.
Нет источника — блок пишет «не подключено» и подсказывает, как
подключить. НОЛЬ ВМЕСТО ОТСУТСТВУЮЩИХ ДАННЫХ ЗАПРЕЩЁН: ноль заявок
и «мы не умеем считать заявки» — разные вещи, и путать их нельзя.

Панель открывается двойным кликом с диска. Ни сервера, ни интернета,
ни внешних библиотек.
"""
import io
import json
import os
import re
import subprocess
import sys
from datetime import date

KOREN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGODNYA = date.today()


def chitat(put):
    try:
        return io.open(os.path.join(KOREN, put), encoding="utf-8").read()
    except OSError:
        return ""


# ── 1. Проверка сайта ────────────────────────────────────────────────
def proverka_sajta():
    try:
        vyvod = subprocess.run(
            [sys.executable, os.path.join(KOREN, "scripts", "proverka-sajta.py"), "--json"],
            capture_output=True, text=True, timeout=120)
        return json.loads(vyvod.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"oshibka": str(e)}


# ── 2. Чего мы не знаем: незаполненные строки прайса ────────────────
def probely_prajsa():
    """Каждое `null` в прайсе — это расчёт, который остался прикидкой."""
    prajs = chitat("data/prices.ts")
    imena = {
        "iiModeli": "подписки на ИИ в месяц",
        "prochee": "прочие расходы в месяц",
        "zakazovVMesyac": "сколько заказов в месяц",
        "stavkaChasa": "ставка часа работы",
        "oplachivaemyhChasovVMesyac": "сколько часов в месяц оплачивается",
        "obsluzhivanieNaIzdelie": "обслуживание принтера на изделие",
        "rezkaUpakovkaNaIzdelie": "резка и упаковка на изделие",
        "ispolzuetsyaFaktom": "какая доля тонера реально расходуется",
        "resursM2": "ресурс картриджа плоттера, м²",
    }
    probely = []
    for klyuch, opisanie in imena.items():
        if re.search(r"\b%s:\s*null\b" % klyuch, prajs):
            probely.append(opisanie)
    return probely


# ── 3. Открытые хвосты из журнала ────────────────────────────────────
def hvosty():
    zhurnal = chitat("TASKS.md")
    # Берём только последние записи: старые хвосты часто уже неактуальны,
    # а панель должна показывать сегодняшнее, а не всю историю.
    hvost = zhurnal[-30000:]
    otkrytye = re.findall(r"^- \[ \] (.+)$", hvost, re.M)
    # Схлопываем многострочные и режем длинные
    chistye = []
    for h in otkrytye:
        h = re.sub(r"\*\*|`", "", h).strip()
        chistye.append(h[:150])
    # Панель должна отвечать за пять секунд. Сорок строк — это уже
    # список дел, а не панель: его перестают читать. Показываем
    # последние, число остальных выносим в заголовок.
    return chistye


# ── 4. Последний замер Метрики ───────────────────────────────────────
def zamer():
    st = chitat("STATISTIKA.md")
    zag = re.search(r"^## (Замер [^\n]+)", st, re.M)
    if not zag:
        return None
    kusok = st[zag.start():zag.start() + 3000]
    pokazateli = {}
    for nazvanie, obrazec in (
        ("Визиты", r"\|\s*Визиты\s*\|\s*\*\*([\d\s]+)\*\*"),
        ("Отказы", r"\|\s*Отказы\s*\|\s*\*\*([\d,]+%)\*\*"),
        ("Время на сайте", r"\|\s*Время на сайте\s*\|\s*([^|]+)\|"),
    ):
        m = re.search(obrazec, kusok)
        if m:
            pokazateli[nazvanie] = m.group(1).strip()
    return {"zagolovok": zag.group(1), "pokazateli": pokazateli}


# ── 5. Заявки ────────────────────────────────────────────────────────
def zayavki():
    """Журнал заявок лежит на диске Amvera, у нас его нет.

    Если владелица положит выгрузку рядом с проектом, панель её
    прочитает. До тех пор — честное «не подключено», а не ноль."""
    for imya in ("leads.jsonl", "data/leads.jsonl", "zhivoj-sajt/leads.jsonl"):
        tekst = chitat(imya)
        if tekst.strip():
            stroki = [json.loads(s) for s in tekst.splitlines() if s.strip()]
            return {"est": True, "vsego": len(stroki)}
    return {"est": False}


# ── 6. Сезон ─────────────────────────────────────────────────────────
def sezon():
    piki = [
        (date(SEGODNYA.year, 9, 1), "1 сентября — грамоты, дипломы, благодарности"),
        (date(SEGODNYA.year, 12, 1), "декабрь — календари, корпоративные открытки"),
        (date(SEGODNYA.year, 12, 25), "Новый год — поздравления, сертификаты в подарок"),
    ]
    blizhajshie = [(d, n) for d, n in piki if d >= SEGODNYA]
    if not blizhajshie:
        return None
    d, n = blizhajshie[0]
    return {"dnej": (d - SEGODNYA).days, "chto": n}


# ── Вердикт ──────────────────────────────────────────────────────────
def verdikt(pr, hv, pb):
    """Первое сработавшее правило. Порядок — по цене ошибки."""
    if pr.get("oshibka"):
        return ("krasnyj", "Проверка сайта не запускается",
                ["Это значит, что мы не видим поломок вообще"])
    if pr.get("kritichno"):
        return ("krasnyj", "На сайте критичные замечания",
                [z["stranica"] + " — " + z["tekst"] for z in pr["kritichno"][:3]])
    if len(pb) >= 5:
        return ("zheltyj", "Половина расчётов держится на прикидках",
                ["Не заполнено строк прайса: %d" % len(pb)])
    if pr.get("vazhno"):
        return ("zheltyj", "Есть важные замечания по сайту",
                [z["stranica"] + " — " + z["tekst"] for z in pr["vazhno"][:3]])
    return ("zelenyj", "Критичного нет", [])


def sobrat():
    pr = proverka_sajta()
    pb = probely_prajsa()
    hv = hvosty()
    zm = zamer()
    zv = zayavki()
    sz = sezon()
    cvet, fraza, prichiny = verdikt(pr, hv, pb)

    def blok_zayavki():
        if zv["est"]:
            return ('<div class="chislo">%d</div><div class="podpis">заявок в журнале</div>'
                    % zv["vsego"])
        return ('<div class="net">не подключено</div>'
                '<div class="podpis">Журнал заявок лежит на диске Amvera. '
                'Выгрузите <b>leads.jsonl</b> и положите в папку проекта — '
                'панель прочитает его сама.</div>')

    def spisok(elementy, pusto):
        if not elementy:
            return '<div class="pusto">%s</div>' % pusto
        return "<ul>" + "".join("<li>%s</li>" % e for e in elementy) + "</ul>"

    zamechaniya = []
    for uroven, klyuch in (("критично", "kritichno"), ("важно", "vazhno"), ("потом", "potom")):
        for z in pr.get(klyuch, []):
            zamechaniya.append('<b class="%s">%s</b> %s — %s'
                               % (klyuch, uroven, z["stranica"], z["tekst"]))

    html = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Панель студии «Гранат»</title>
<style>
  :root { --fon:#12100f; --karta:#1c1917; --tekst:#f5efe8; --tusklo:#a8a29e;
          --zelenyj:#4ade80; --zheltyj:#fbbf24; --krasnyj:#f87171; --zoloto:#D4AF37; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--fon); color:var(--tekst); padding:16px 14px 40px;
         font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
  .obertka { max-width:820px; margin:0 auto; }
  h1 { font-size:15px; font-weight:600; color:var(--tusklo); letter-spacing:.08em;
       text-transform:uppercase; margin-bottom:14px; }
  .verdikt { border-radius:16px; padding:20px; margin-bottom:14px; border:1px solid; }
  .verdikt.zelenyj { background:rgba(74,222,128,.08); border-color:rgba(74,222,128,.35); }
  .verdikt.zheltyj { background:rgba(251,191,36,.08); border-color:rgba(251,191,36,.35); }
  .verdikt.krasnyj { background:rgba(248,113,113,.08); border-color:rgba(248,113,113,.35); }
  .verdikt .fraza { font-size:22px; font-weight:700; line-height:1.25; }
  .verdikt.zelenyj .fraza { color:var(--zelenyj); }
  .verdikt.zheltyj .fraza { color:var(--zheltyj); }
  .verdikt.krasnyj .fraza { color:var(--krasnyj); }
  .verdikt ul { margin:10px 0 0 18px; color:var(--tusklo); font-size:14px; }
  .karta { background:var(--karta); border-radius:16px; padding:18px; margin-bottom:12px; }
  .karta h2 { font-size:12px; font-weight:700; letter-spacing:.1em; text-transform:uppercase;
              color:var(--tusklo); margin-bottom:12px; }
  .chislo { font-size:40px; font-weight:700; font-variant-numeric:tabular-nums;
            color:var(--zoloto); line-height:1; }
  .podpis { font-size:13px; color:var(--tusklo); margin-top:6px; }
  .net { font-size:17px; font-weight:600; color:var(--zheltyj); }
  ul { margin-left:18px; } li { margin-bottom:7px; font-size:14px; }
  .pusto { color:var(--zelenyj); font-size:14px; }
  b.kritichno { color:var(--krasnyj); } b.vazhno { color:var(--zheltyj); }
  b.potom { color:var(--tusklo); }
  .plitki { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media (max-width:520px) { .plitki { grid-template-columns:1fr; } }
  .nizhe { font-size:12px; color:var(--tusklo); margin-top:18px; line-height:1.6; }
  code { background:rgba(255,255,255,.07); padding:2px 6px; border-radius:5px; font-size:13px; }
</style></head><body><div class="obertka">
<h1>Панель студии «Гранат» · {DATA}</h1>

<div class="verdikt {CVET}">
  <div class="fraza">{FRAZA}</div>
  {PRICHINY}
</div>

<div class="plitki">
  <div class="karta"><h2>Заявки</h2>{ZAYAVKI}</div>
  <div class="karta"><h2>Ближайший сезон</h2>{SEZON}</div>
</div>

<div class="karta">
  <h2>Проверка сайта · страниц {STRANIC}</h2>
  {ZAMECHANIYA}
  <div class="podpis">Перепроверить: <code>npm run proverka-sajta</code></div>
</div>

<div class="karta">
  <h2>Чего мы не знаем · {PROBELOV}</h2>
  <div class="podpis" style="margin:0 0 10px">Каждая строка ниже делает какой-то расчёт прикидкой, а не расчётом.</div>
  {PROBELY}
</div>

<div class="karta">
  <h2>Последний замер Метрики</h2>
  {ZAMER}
</div>

<div class="karta">
  <h2>Открытые хвосты из журнала · {HVOSTOV}</h2>
  {HVOSTY}
</div>

<div class="nizhe">
  Панель ничего не меняет — только читает то, что уже есть в проекте.<br>
  Обновить: <code>npm run panel</code>, потом обновить страницу.<br>
  Пустой блок значит «нет источника», а не «ноль».
</div>
</div></body></html>"""

    zamena = {
        "{DATA}": SEGODNYA.strftime("%d.%m.%Y"),
        "{CVET}": cvet,
        "{FRAZA}": fraza,
        "{PRICHINY}": ("<ul>" + "".join("<li>%s</li>" % p for p in prichiny) + "</ul>") if prichiny else "",
        "{ZAYAVKI}": blok_zayavki(),
        "{SEZON}": ('<div class="chislo">%d</div><div class="podpis">дней до: %s</div>'
                    % (sz["dnej"], sz["chto"])) if sz else '<div class="net">—</div>',
        "{STRANIC}": str(pr.get("stranic", "?")),
        "{ZAMECHANIYA}": spisok(zamechaniya, "Замечаний нет. Это и есть нужный результат."),
        "{PROBELOV}": str(len(pb)),
        "{PROBELY}": spisok(pb, "Все строки прайса заполнены."),
        "{ZAMER}": (('<div class="podpis" style="margin:0 0 8px"><b>%s</b></div>' % zm["zagolovok"])
                    + "".join('<div class="podpis">%s — <b style="color:var(--tekst)">%s</b></div>'
                              % (k, v) for k, v in zm["pokazateli"].items())) if zm
                   else '<div class="net">не подключено</div>',
        "{HVOSTOV}": str(len(hv)),
        "{HVOSTY}": (spisok(hv[-12:], "Открытых хвостов нет.")
                     + ('<div class="podpis">Показаны последние 12. Всего %d — '
                        'весь список в <code>TASKS.md</code>.</div>' % len(hv)
                        if len(hv) > 12 else "")),
    }
    for k, v in zamena.items():
        html = html.replace(k, v)

    io.open(os.path.join(KOREN, "panel.html"), "w", encoding="utf-8").write(html)
    print("Готово: panel.html — откройте двойным кликом.")
    print("  вердикт: %s — %s" % (cvet, fraza))
    print("  замечаний проверки: %d · пробелов в прайсе: %d · хвостов: %d"
          % (len(zamechaniya), len(pb), len(hv)))


if __name__ == "__main__":
    sobrat()
