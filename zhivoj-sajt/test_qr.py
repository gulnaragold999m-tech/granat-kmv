# -*- coding: utf-8 -*-
"""Постоянный адрес для QR ведёт куда надо в любом состоянии."""
import os, sys, types
os.environ["LEADS_DIR"]="/tmp/leads-qr"
ploho=[]
def p(chto, ozh, est):
    ok = ozh==est
    print(f"  [{'ok ' if ok else 'ПЛОХО'}] {chto}: {est!r}")
    if not ok: ploho.append(chto)

class Otvet:
    def __init__(s, code=200, headers=None, url="", text=""):
        s.status_code, s.headers, s.url, s.text = code, headers or {}, url, text

def zagruzit(znachenie, otvet=None):
    os.environ["YANDEX_REVIEWS"]=znachenie
    sys.modules.pop("app", None)
    import app
    app.requests = types.SimpleNamespace(get=lambda *a, **k: otvet if otvet is not None else Otvet())
    return app

print("Номер карточки известен — ведём прямо в форму отзыва")
app = zagruzit("237257245054")
o = app.app.test_client().get("/otzyv", base_url="https://granat-kmv.ru")
p("код", 302, o.status_code)
p("куда", "https://yandex.ru/maps/org/237257245054/reviews/?add-review=true", o.headers["Location"])

print("Виджет запрещён — адрес всё равно ведёт на форму отзыва")
app = zagruzit("237257245054", otvet=Otvet(headers={"X-Frame-Options":"DENY"}))
o = app.app.test_client().get("/otzyv", base_url="https://granat-kmv.ru")
p("куда", "https://yandex.ru/maps/org/237257245054/reviews/?add-review=true", o.headers["Location"])

print("Ничего не задано — ведём на блок отзывов у нас")
app = zagruzit("https://example.com/chuzhoe")
o = app.app.test_client().get("/otzyv", base_url="https://granat-kmv.ru")
p("куда", "/#otzyvy", o.headers["Location"])

print("Короткая ссылка ещё не развернулась — ведём на карточку")
app = zagruzit("https://yandex.ru/maps/-/CTFBZ4kK", otvet=Otvet(url="https://yandex.ru/maps/-/CTFBZ4kK"))
o = app.app.test_client().get("/otzyv", base_url="https://granat-kmv.ru")
p("куда", "https://yandex.ru/maps/-/CTFBZ4kK", o.headers["Location"])

print("Картинки не перехвачены новым адресом")
app = zagruzit("237252454")
c = app.app.test_client()
for a in ("/robots.txt", "/sitemap.xml", "/"):
    p(f"{a} жив", 200, c.get(a, base_url="https://granat-kmv.ru").status_code)

print()
if ploho: print("НЕ СОШЛОСЬ:", "; ".join(ploho)); sys.exit(1)
print("Всё сошлось.")
