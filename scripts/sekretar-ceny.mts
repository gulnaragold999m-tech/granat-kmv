/* Цены для секретаря на сайте — выгрузка из прайса в шаблон.

   Запуск:  npm run sekretar
   Результат: zhivoj-sajt/templates/partials/_js-sekretar-ceny.html —
   инлайн-скрипт с константой CENY, которую читает секретарь.

   ЗАЧЕМ ГЕНЕРАТОР. Правило владелицы: цена живёт в одном месте. Секретарь
   на сайте — четвёртый канал после страницы, бота и шпаргалки, и если
   вписать цифры ему в код руками, они разъедутся так же, как разъехались
   у живого сайта. Здесь всё берётся из `data/prices.ts`: поменяли прайс —
   пересобрали, и секретарь считает по-новому.

   ПОЧЕМУ В ШАБЛОН, А НЕ В static/. Живой сайт выкатывается загрузкой
   папок в Amvera. Одна папка `templates` — одна загрузка и меньше шансов
   забыть вторую: 15.08.2026 так уже потеряли `templates` и сайт лежал
   ночь. Скрипт инлайновый, отдельного файла грузить не нужно.

   ПОРОГИ ТИРАЖЕЙ считаются из подписей столбцов автоматически: первое
   число в «10–20 шт.», «от 100 шт.», «50 шт.» и есть количество, с
   которого столбец действует. Добавили столбец в прайс — порог появится
   сам, руками ничего править не нужно. */

import {
  OTKRYTKI,
  SHTUCHNAYA_A4,
  PRIGLASHENIYA,
  PECHAT_FOTO,
  KSEROKOPIYA,
  FLAERY,
  LAMINACIYA,
  FOTO_NA_DOKUMENTY,
  NET_V_PRAJSE,
  AKCII,
  OPLATA,
  OTDELKA,
  BIGOVKA,
  type TirazhTablica,
  type Yacheyka,
} from '../data/prices.ts';

import { writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

/** QR-код ссылки в виде SVG. Рисуется здесь, при сборке, а не в браузере:
    так на странице нет ни внешних библиотек, ни запросов на чужие сервисы,
    и картинка не может «отвалиться» вместе с чужим сайтом. */
function qrSvg(ssylka: string): string {
  const code = `
import segno, io, sys
qr = segno.make(sys.argv[1], error='m')
buf = io.BytesIO()
qr.save(buf, kind='svg', scale=4, border=2,
        dark='#4A0E17', light='#ffffff', xmldecl=False, svgns=True)
sys.stdout.write(buf.getvalue().decode('utf-8'))
`;
  return execFileSync('python3', ['-c', code, ssylka], { encoding: 'utf8' });
}

/** Число из ячейки. Строка «по запросу» и прочерк — это не цена. */
function chislo(y: Yacheyka): number | null {
  if (typeof y === 'number') return y;
  if (typeof y === 'object' && 'ot' in y) return y.ot;
  return null;
}

/** Порог столбца: первое число в подписи. «от 100 шт.» → 100. */
function porog(podpis: string): number {
  const m = podpis.match(/\d+/);
  return m ? Number(m[0]) : 1;
}

/** Таблица в вид, удобный счётчику: пороги и цены по строкам. */
function vygruzka(t: TirazhTablica) {
  return {
    zagolovok: t.zagolovok,
    porogi: t.kolonki.map(porog),
    stroki: Object.fromEntries(
      t.stroki.map((s) => [s.nazvanie, s.ceny.map(chislo)]),
    ),
  };
}

const CENY = {
  otkrytki: vygruzka(OTKRYTKI),
  priglasheniya: vygruzka(PRIGLASHENIYA),
  foto: vygruzka(PECHAT_FOTO),
  kopii: vygruzka(KSEROKOPIYA),
  flaery: vygruzka(FLAERY),
  laminaciya: vygruzka(LAMINACIYA),

  /* Фото на документы — не тираж, а список услуг. */
  dokfoto: Object.fromEntries(
    FOTO_NA_DOKUMENTY.pozicii.map((p) => [p.nazvanie, chislo(p.cena)]),
  ),

  /* Минимальные заказы. Взяты из «Как мы считаем» и согласованы с
     `prices.py` бота: у него те же значения в MIN_ORDER, включая
     отдельный порог 1200 ₽ на штучную открытку А4. */
  minimalki: {
    kopii: 50,
    laminaciya: 50,
    poligrafiya: 300,
    otkrytki: 700,
    otkrytkaA4: SHTUCHNAYA_A4.minZakaz,
    sertifikat: SHTUCHNAYA_A4.roznicaSertifikat,
  },

  /* Штучная А4 на картоне: цена за экземпляр при 1–9 штуках. */
  shtuchnayaA4: SHTUCHNAYA_A4.cena,

  /* Работа с макетом. Цифры из RABOTA_S_MAKETOM, но плоские: секретарю
     нужны числа, а не строки вида «300–500 ₽». Нижняя граница вилки —
     чтобы расчёт не завышал, а точную сумму называют после проверки. */
  maket: {
    proverka: 150,
    adaptaciyaOt: 300,
    adaptaciyaDo: 500,
    slozhnyjOt: 600,
    sNulyaOt: 1000,
  },

  /* Отделка — за штуку, добавляется к базовой цене. */
  otdelka: OTDELKA,
  bigovka: BIGOVKA,

  /* Множители. Срочность одна на весь прайс — как у бота. */
  koefficienty: {
    srochno: 1.3,
    fotobumagaPlotnaya: 1.25,
    karton250: 0.9,
    karton350: 1.1,
  },

  netVPrajse: NET_V_PRAJSE,

  /* Действующие акции. Заводятся в data/prices.ts и попадают сюда сами:
     объявили скидку в рекламе — секретарь о ней знает. */
  akcii: AKCII.filter((a) => a.aktivna),

  /* Предоплата: процент, номер для перевода и — когда появится —
     ссылка на оплату вместе с нарисованным по ней QR-кодом. */
  oplata: {
    procent: OPLATA.predoplataProcent,
    nomer: OPLATA.nomer,
    ssylka: OPLATA.ssylka,
    qr: OPLATA.ssylka ? qrSvg(OPLATA.ssylka) : '',
  },
};

const html = `<!-- Цены секретаря. СГЕНЕРИРОВАНО, руками не править.
     Источник: data/prices.ts. Пересобрать: npm run sekretar -->
<script>
  window.CENY = ${JSON.stringify(CENY, null, 2)};
</script>
`;

writeFileSync(
  new URL('../zhivoj-sajt/templates/partials/_js-sekretar-ceny.html', import.meta.url),
  html,
  'utf8',
);
console.log('Готово: partials/_js-sekretar-ceny.html — цены секретаря обновлены из прайса.');
