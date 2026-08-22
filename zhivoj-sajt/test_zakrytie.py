# -*- coding: utf-8 -*-
"""Что сайт отдаёт из корня, а что нет. Проверка после утечки 21.08.2026."""
import os
os.environ["LEADS_DIR"]="/tmp/leads-zakr"
os.environ["YANDEX_REVIEWS"]="237257245054"
import app

# Кладём рядом файлы, которые должны быть закрыты и открыты.
# Запоминаем, что создали САМИ: чужое (настоящий robots.txt, если он
# появится в репозитории) удалять нельзя, а свои заглушки убрать
# обязаны. 22.08.2026 они остались лежать после прогона, попали
# в неотслеживаемые и сбили соседнюю самопроверку test_qr.py:
# первый её прогон падал, второй проходил — на том же коде.
NASHI = []
for imya, soderzhimoe in [("robots.txt","User-agent: *"), ("sitemap.xml","<urlset/>"),
                          ("privacy.html","политика"), ("requirements.txt","flask"),
                          ("secret.md","тайна"), ("logo.png","PNG")]:
    if not os.path.exists(imya):
        open(imya,"w").write(soderzhimoe)
        NASHI.append(imya)


def ubrat():
    for imya in NASHI:
        try:
            os.remove(imya)
        except OSError:
            pass


import atexit
atexit.register(ubrat)

c = app.app.test_client()
ZAKRYT = ["app.py","leads.py","bots.py","contact.py","fraud_check.py","amvera.yaml",
          "requirements.txt",".env.example","TASKS.md","secret.md",".git/config",
          ".git/HEAD",".git/index","app.py.do-15-08-2026","README.md",
          ".env","test_otzyvy.py","templates/base.html"]
OTKRYT  = ["robots.txt","sitemap.xml","privacy.html","logo.png",
           "static/css/tailwind.css","static/js/metrika-goals.js"]
STRANICY = ["/","/kontakty","/pechat","/cifra","/api/health","/raboty","/dokumenty"]

ploho = []
print("ДОЛЖНЫ БЫТЬ ЗАКРЫТЫ:")
for p in ZAKRYT:
    k = c.get("/"+p, base_url="https://granat-kmv.ru").status_code
    ok = k == 404
    print(f"  [{'ok ' if ok else 'ПЛОХО'}] /{p} → {k}")
    if not ok: ploho.append(f"/{p} отдаётся с кодом {k}")

print("ДОЛЖНЫ ОТКРЫВАТЬСЯ:")
for p in OTKRYT:
    k = c.get("/"+p, base_url="https://granat-kmv.ru").status_code
    ok = k == 200
    print(f"  [{'ok ' if ok else 'ПЛОХО'}] /{p} → {k}")
    if not ok: ploho.append(f"/{p} закрылся, код {k}")

print("СТРАНИЦЫ САЙТА:")
for p in STRANICY:
    k = c.get(p, base_url="https://granat-kmv.ru").status_code
    ok = k == 200
    print(f"  [{'ok ' if ok else 'ПЛОХО'}] {p} → {k}")
    if not ok: ploho.append(f"{p} сломалась, код {k}")

print()
if ploho:
    print("НЕ СОШЛОСЬ:"); [print(" -", x) for x in ploho]; raise SystemExit(1)
print("Всё сошлось.")
