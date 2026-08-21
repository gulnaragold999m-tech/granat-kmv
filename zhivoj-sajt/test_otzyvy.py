# -*- coding: utf-8 -*-
"""Проверка блока отзывов: что показывается и куда ведут кнопки.

Запуск: python3 test_otzyvy.py из папки zhivoj-sajt.

В Яндекс отсюда не сходить — из среды разработки yandex.ru закрыт
прокси. Поэтому ответы Яндекса подменяем и проверяем два решения:
как разбирается адрес карточки и пускает ли Яндекс виджет к нам.
"""
import os, sys, time, types

os.environ["LEADS_DIR"] = "/tmp/leads-test"

oshibki = []


def proverit(chto, ozhidaem, poluchili):
    znak = "ok " if ozhidaem == poluchili else "ПЛОХО"
    if ozhidaem != poluchili:
        oshibki.append(f"{chto}: ждали {ozhidaem!r}, вышло {poluchili!r}")
    print(f"  [{znak}] {chto}: {poluchili!r}")


class Otvet:
    """Ответ Яндекса, какой нам нужен для проверки."""

    def __init__(self, code=200, headers=None, url="", text=""):
        self.status_code = code
        self.headers = headers or {}
        self.url = url
        self.text = text


def zagruzit(znachenie, otvet=None, oshibka=None):
    """Перезагрузить app.py с заданным YANDEX_REVIEWS и ответом Яндекса.

    otvet — что вернёт запрос к Яндексу; по умолчанию виджет разрешён.
    """
    os.environ["YANDEX_REVIEWS"] = znachenie
    sys.modules.pop("app", None)
    import app

    def get(*a, **k):
        if oshibka:
            raise oshibka
        return otvet if otvet is not None else Otvet()

    app.requests = types.SimpleNamespace(get=get)
    return app


def dozhdatsya(app):
    """Дождаться фоновых походов в Яндекс и спросить ещё раз.

    Пул общий на всё приложение, поэтому его нельзя закрывать — ждём
    по признаку: разворот короткой ссылки и проверка виджета сами
    отмечаются в памяти, когда закончат.
    """
    for _ in range(200):
        app.yandex_reviews()
        gotovo = app._VIDZHET["pochemu"] != "ещё не спрашивали"
        korotkaya = not app._SHORT_LINK["url"] or app._SHORT_LINK["asked"]
        if gotovo and korotkaya:
            break
        time.sleep(0.02)
    time.sleep(0.05)
    return app.yandex_reviews()


print("1. Голый номер карточки: рамка появляется, когда Яндекс её пустил")
app = zagruzit("1234567890")
r = app.yandex_reviews()
proverit("читать", "https://yandex.ru/maps/org/1234567890/reviews/", r["page"])
proverit("написать", "https://yandex.ru/maps/org/1234567890/reviews/?add-review=true", r["add"])
proverit("после проверки: рамка",
         "https://yandex.ru/maps-reviews-widget/?id=1234567890", dozhdatsya(app)["frame"])

print("2. Код виджета целиком из кабинета")
kod = '<iframe src="https://yandex.ru/maps-reviews-widget/?id=9876543210" width="560"></iframe>'
app = zagruzit(kod)
proverit("номер вынут из кода",
         "https://yandex.ru/maps-reviews-widget/?id=9876543210", dozhdatsya(app)["frame"])

print("3. Полная ссылка на карточку")
app = zagruzit("https://yandex.ru/maps/org/granat/111222333/reviews/")
proverit("номер из /org/",
         "https://yandex.ru/maps-reviews-widget/?id=111222333", dozhdatsya(app)["frame"])

print("4. Яндекс запрещает вставку — рамки быть не должно")
for zapret, imya in [
    ({"X-Frame-Options": "DENY"}, "X-Frame-Options: DENY"),
    ({"X-Frame-Options": "sameorigin"}, "X-Frame-Options: SAMEORIGIN"),
    ({"Content-Security-Policy": "frame-ancestors 'self' yandex.ru"}, "frame-ancestors без нас"),
]:
    app = zagruzit("1234567890", otvet=Otvet(headers=zapret))
    proverit(f"{imya}: рамки нет", None, dozhdatsya(app)["frame"])

print("5. Яндекс разрешает вставку явно — рамка нужна")
app = zagruzit("1234567890", otvet=Otvet(headers={"Content-Security-Policy": "frame-ancestors *"}))
proverit("frame-ancestors *", "https://yandex.ru/maps-reviews-widget/?id=1234567890",
         dozhdatsya(app)["frame"])

print("6. Виджет не отдаётся — рамки нет, кнопки остаются")
app = zagruzit("1234567890", otvet=Otvet(code=404))
r = dozhdatsya(app)
proverit("404 от Яндекса: рамки нет", None, r["frame"])
proverit("кнопка «оставить отзыв» на месте",
         "https://yandex.ru/maps/org/1234567890/reviews/?add-review=true", r["add"])

print("7. Сеть молчит — рамки нет")
app = zagruzit("1234567890", oshibka=OSError("сеть недоступна"))
proverit("рамки нет", None, dozhdatsya(app)["frame"])

print("8. Чужой домен и не https — блока нет вовсе")
proverit("чужой домен", None, zagruzit("https://example.com/maps-reviews-widget/?id=1").yandex_reviews())
proverit("http вместо https", None, zagruzit("http://yandex.ru/maps-reviews-widget/?id=1").yandex_reviews())

print("9. Ссылка на поиск по городу: номер региона брать нельзя")
app = zagruzit("https://yandex.ru/maps/11079/lermontov/", otvet=Otvet(url="https://yandex.ru/maps/11079/lermontov/"))
r = app.yandex_reviews()
proverit("рамки нет", None, r["frame"])
proverit("кнопка ведёт на ту же ссылку", "https://yandex.ru/maps/11079/lermontov/", r["page"])

print("10. Короткая ссылка разворачивается сама")
app = zagruzit("https://yandex.ru/maps/-/CTFBZ4kK",
               otvet=Otvet(url="https://yandex.ru/maps/org/granat/44556677/"))
proverit("после разворота: карточка найдена", "https://yandex.ru/maps/org/44556677/reviews/",
         dozhdatsya(app)["page"])

print("11. Страницы: блок отзывов на месте и стоит выше секретаря")
app = zagruzit("1234567890")
dozhdatsya(app)
c = app.app.test_client()
for adres in ("/", "/kontakty"):
    html = c.get(adres, base_url="https://granat-kmv.ru").get_data(as_text=True)
    proverit(f"{adres}: заголовок отзывов", True, "Что о нас пишут на Яндекс Картах" in html)
    proverit(f"{adres}: рамка виджета", True,
             'src="https://yandex.ru/maps-reviews-widget/?id=1234567890"' in html)
    proverit(f"{adres}: ленивая загрузка", True, 'loading="lazy"' in html)
    proverit(f"{adres}: секретарь на месте", True, "sekretar" in html)

glavnaya = c.get("/", base_url="https://granat-kmv.ru").get_data(as_text=True)
proverit("на главной отзывы ВЫШЕ секретаря", True,
         glavnaya.index('id="otzyvy"') < glavnaya.index('id="sekretar"'))
proverit("ссылка на отзывы есть на первом экране", True, 'href="#otzyvy"' in glavnaya)

for adres in ("/pechat", "/cifra"):
    html = c.get(adres, base_url="https://granat-kmv.ru").get_data(as_text=True)
    proverit(f"{adres}: отзывов быть не должно", False, "Что о нас пишут" in html)

print("12. Контакты: адрес как в карточке Яндекса")
html = c.get("/kontakty", base_url="https://granat-kmv.ru").get_data(as_text=True)
proverit("этаж", True, "второй этаж" in html)
proverit("адрес как в карточке Яндекса", True, "г. Лермонтов, Нагорная улица, 2/1" in html)
proverit("старого написания не осталось", 0, html.count("ул. Нагорная"))

print("13. /api/health говорит, что стоит на страницах")
proverit("строка otzyvy", "виджет с отзывами, карточка 1234567890", app.reviews_state())
app = zagruzit("1234567890", otvet=Otvet(headers={"X-Frame-Options": "DENY"}))
dozhdatsya(app)
proverit("когда Яндекс не пустил — сказано почему", True,
         "X-Frame-Options" in app.reviews_state())

print("14. Анимация не прячет блоки при выключенном JavaScript")
proverit("прячем только при работающем скрипте", True,
         ".js-anim .reveal { opacity: 0" in c.get("/", base_url="https://granat-kmv.ru").get_data(as_text=True))

print()
if oshibki:
    print("НЕ СОШЛОСЬ:")
    for o in oshibki:
        print(" -", o)
    sys.exit(1)
print("Все проверки прошли.")
