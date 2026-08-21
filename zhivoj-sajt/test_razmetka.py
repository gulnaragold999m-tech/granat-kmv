# -*- coding: utf-8 -*-
"""Разметка: связка с карточкой, адрес как в Яндексе, крошки, 404."""
import os, json, re
os.environ["LEADS_DIR"]="/tmp/leads-r"; os.environ["YANDEX_REVIEWS"]="237257245054"
import app
c=app.app.test_client()
ploho=[]
def p(chto, ozh, est):
    ok = ozh==est
    print(f"  [{'ok ' if ok else 'ПЛОХО'}] {chto}: {est!r}")
    if not ok: ploho.append(f"{chto}: ждали {ozh!r}, вышло {est!r}")

def bloki(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]

html = c.get("/", base_url="https://granat-kmv.ru").get_data(as_text=True)
org = [b for b in bloki(html) if b.get("@type")=="ProfessionalService"][0]
print("Разметка организации:")
p("адрес как в карточке Яндекса", "Нагорная улица, 2/1", org["address"]["streetAddress"])
p("город", "Лермонтов", org["address"]["addressLocality"])
p("hasMap ведёт на карточку", "https://yandex.ru/maps/org/237257245054/", org["hasMap"])
p("карточка в sameAs", True, "https://yandex.ru/maps/org/237257245054/" in org["sameAs"])
p("ВКонтакте на месте", True, "https://vk.com/club238836731" in org["sameAs"])

print("Крошки:")
h2 = c.get("/pechat", base_url="https://granat-kmv.ru").get_data(as_text=True)
kroshki = [b for b in bloki(h2) if b.get("@type")=="BreadcrumbList"][0]
p("название раздела", "Печать и полиграфия", kroshki["itemListElement"][1]["name"])

print("Страница 404:")
o404 = c.get("/net-takoj-stranicy-12345", base_url="https://granat-kmv.ru")
p("код ответа", 404, o404.status_code)
h404 = o404.get_data(as_text=True)
kanon = re.search(r'<link rel="canonical" href="([^"]+)"', h404).group(1)
p("canonical не главная", "https://granat-kmv.ru/404", kanon)

print("Адрес на страницах — одно написание:")
for adres in ["/", "/kontakty", "/sertifikaty", "/dokumenty", "/otkrytki"]:
    h = c.get(adres, base_url="https://granat-kmv.ru").get_data(as_text=True)
    staryh = h.count("ул. Нагорная")
    p(f"{adres}: старых написаний", 0, staryh)

print("Разметка всех страниц разбирается:")
for adres in ["/","/pechat","/cifra","/kontakty","/raboty","/dokumenty","/sertifikaty","/otkrytki","/kak-rabotaem"]:
    try:
        n=len(bloki(c.get(adres, base_url="https://granat-kmv.ru").get_data(as_text=True)))
        p(f"{adres}: блоков", n>0, True)
    except Exception as e:
        ploho.append(f"{adres}: разметка не разобралась — {e}")
        print(f"  [ПЛОХО] {adres}: {e}")
print()
if ploho:
    print("НЕ СОШЛОСЬ:"); [print(" -", x) for x in ploho]; raise SystemExit(1)
print("Всё сошлось.")
