# -*- coding: utf-8 -*-
"""Проверка блока отзывов: что показывается и куда ведут кнопки.

Запуск: python3 test_otzyvy.py из папки zhivoj-sajt.

В Яндекс отсюда не сходить — из среды разработки yandex.ru закрыт
прокси. Поэтому ответ Яндекса подменяем и проверяем разбор адресов.
"""
import os, sys, types, importlib

os.environ["LEADS_DIR"] = "/tmp/leads-test"

def zagruzit(znachenie):
    """Перезагрузить app.py с заданным YANDEX_REVIEWS."""
    os.environ["YANDEX_REVIEWS"] = znachenie
    for m in list(sys.modules):
        if m == "app":
            del sys.modules[m]
    import app
    return app

oshibki = []
def proverit(chto, ozhidaem, poluchili):
    znak = "ok " if ozhidaem == poluchili else "ПЛОХО"
    if ozhidaem != poluchili:
        oshibki.append(f"{chto}: ждали {ozhidaem!r}, вышло {poluchili!r}")
    print(f"  [{znak}] {chto}: {poluchili!r}")

print("1. Голый номер карточки")
app = zagruzit("1234567890")
r = app.yandex_reviews()
proverit("рамка", "https://yandex.ru/maps-reviews-widget/?id=1234567890", r["frame"])
proverit("читать", "https://yandex.ru/maps/org/1234567890/reviews/", r["page"])
proverit("написать", "https://yandex.ru/maps/org/1234567890/reviews/?add-review=true", r["add"])

print("2. Код виджета целиком из кабинета")
kod = '<iframe style="border:1px solid #e6e6e6;border-radius:8px;box-sizing:border-box" src="https://yandex.ru/maps-reviews-widget/?id=9876543210" width="560"></iframe>'
app = zagruzit(kod)
proverit("номер вынут из кода", "https://yandex.ru/maps-reviews-widget/?id=9876543210", app.yandex_reviews()["frame"])

print("3. Полная ссылка на карточку")
app = zagruzit("https://yandex.ru/maps/org/granat/111222333/reviews/")
proverit("номер из /org/", "https://yandex.ru/maps-reviews-widget/?id=111222333", app.yandex_reviews()["frame"])

print("4. Чужой домен — отклоняем")
app = zagruzit("https://example.com/maps-reviews-widget/?id=1")
proverit("блока нет", None, app.yandex_reviews())

print("5. Не https — отклоняем")
app = zagruzit("http://yandex.ru/maps-reviews-widget/?id=1")
proverit("блока нет", None, app.yandex_reviews())

print("6. Ссылка на поиск по городу: номер региона брать нельзя")
app = zagruzit("https://yandex.ru/maps/11079/lermontov/")
r = app.yandex_reviews()
proverit("рамки нет", None, r["frame"])
proverit("кнопка ведёт на ту же ссылку", "https://yandex.ru/maps/11079/lermontov/", r["page"])

print("7. Короткая ссылка: сначала кнопка, потом рамка")
app = zagruzit("https://yandex.ru/maps/-/CTFBZ4kK")

class Otvet:
    url = "https://yandex.ru/maps/org/granat/44556677/"
    text = ""
app.requests = types.SimpleNamespace(get=lambda *a, **k: Otvet())

r = app.yandex_reviews()           # первый посетитель — рамки ещё нет
proverit("первый заход: рамки нет", None, r["frame"])
proverit("первый заход: кнопка на карточку", "https://yandex.ru/maps/-/CTFBZ4kK", r["page"])

app.NOTIFY_POOL.shutdown(wait=True)  # дождаться фонового похода в Яндекс
proverit("после разворота: рамка", "https://yandex.ru/maps-reviews-widget/?id=44556677",
         app.yandex_reviews()["frame"])

print("8. Яндекс не ответил — остаёмся на кнопке")
app = zagruzit("https://yandex.ru/maps/-/CTFBZ4kK")
def upalo(*a, **k):
    raise OSError("сеть недоступна")
app.requests = types.SimpleNamespace(get=upalo)
r = app.yandex_reviews()
proverit("рамки нет", None, r["frame"])
app.NOTIFY_POOL.shutdown(wait=True)
proverit("и после отказа рамки нет", None, app.yandex_reviews()["frame"])

print("9. Страницы рисуются, блок на месте")
app = zagruzit("1234567890")
c = app.app.test_client()
for adres in ("/", "/kontakty"):
    otvet = c.get(adres, base_url="https://granat-kmv.ru")
    html = otvet.get_data(as_text=True)
    proverit(f"{adres} отдаётся", 200, otvet.status_code)
    proverit(f"{adres}: заголовок отзывов", True, "Что о нас пишут на Яндекс Картах" in html)
    proverit(f"{adres}: рамка виджета", True, 'src="https://yandex.ru/maps-reviews-widget/?id=1234567890"' in html)
    proverit(f"{adres}: ленивая загрузка", True, 'loading="lazy"' in html)

for adres in ("/pechat", "/cifra"):
    html = c.get(adres, base_url="https://granat-kmv.ru").get_data(as_text=True)
    proverit(f"{adres}: отзывов быть не должно", False, "Что о нас пишут" in html)

print("10. Второй этаж в контактах")
html = c.get("/kontakty", base_url="https://granat-kmv.ru").get_data(as_text=True)
proverit("этаж", True, "второй этаж" in html)
proverit("адрес как в карточке Яндекса", True, "г. Лермонтов, Нагорная улица, 2/1" in html)
proverit("старого написания не осталось", 0, html.count("ул. Нагорная"))

print("11. /api/health говорит про отзывы")
proverit("строка otzyvy", "виджет с отзывами, карточка 1234567890", app.reviews_state())

print("12. Секретарь на месте — блок отзывов его не вытеснил")
glavnaya = c.get("/", base_url="https://granat-kmv.ru").get_data(as_text=True)
proverit("секретарь на главной", True, "sekretar" in glavnaya)

print()
if oshibki:
    print("НЕ СОШЛОСЬ:")
    for o in oshibki:
        print(" -", o)
    sys.exit(1)
print("Все проверки прошли.")
