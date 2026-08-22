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
  ZAPOLNENIE_MAKETA,
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
  BAZOVAYA_ZASHCHITA,
  DOSTAVKA,
  PODAROCHNOE_OFORMLENIE,
  DOSTAVKA_PODAROCHNOGO,
  BIGOVKA,
  FOLGIROVANIE,
  TISNENIE,
  CHERTEZHI,
  MINIMUM_PLOTTER,
  FALCOVKA,
  PLOTNAYA_BUMAGA_KOEF,
  NACENKA_ZA_PLOTNOST,
  type TirazhTablica,
  type Yacheyka,
  SKIDKA_PENSIONERAM,
  PODARKI,
  MAKET_CIFRY,
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
    /* Ноль, а не 50: решение владелицы 19.08.2026. Один лист стоит
       12 ₽, и столько же она за него берёт — «мне это оплачивали».
       Ноль оставлен строкой, а не убран, чтобы секретарь не сломался
       на отсутствующем ключе, а порог было видно в одном месте. */
    kopii: 0,
    laminaciya: 50,
    poligrafiya: 300,
    otkrytki: 700,
    otkrytkaA4: SHTUCHNAYA_A4.minZakaz,
    sertifikat: SHTUCHNAYA_A4.roznicaSertifikat,
  },

  /* Штучная А4 на картоне: цена за экземпляр при 1–9 штуках. */
  shtuchnayaA4: SHTUCHNAYA_A4.cena,

  /* Работа с макетом — плоскими числами из MAKET_CIFRY: секретарю нужны
     числа, а не строки вида «300–500 ₽». До 22.08.2026 они были вписаны
     прямо здесь, и это была сумма в коде вопреки правилу проекта: прайс
     говорил одно, сборка могла говорить другое, и заметить это было
     некому. Теперь источник один — data/prices.ts. */
  maket: MAKET_CIFRY,

  /* Плоттер. Таблица не тиражная: столбцы — это заливка листа,
     а не количество. Поэтому выгружаем как есть, без порогов. */
  plotter: {
    formaty: CHERTEZHI.stroki.map((s) => s.nazvanie),
    zalivki: CHERTEZHI.kolonki,
    ceny: Object.fromEntries(
      CHERTEZHI.stroki.map((s) => [s.nazvanie, s.ceny.map(chislo)]),
    ),
    minimum: MINIMUM_PLOTTER,
    falcovka: FALCOVKA,
    plotnayaKoef: PLOTNAYA_BUMAGA_KOEF,
    /* А0 печатается только на широком рулоне 914 мм, а он у нас
       офисный 80 г/м². Плотного А0 предложить нельзя — секретарь
       должен сказать это до расчёта, а не после. */
    a0TolkoObychnaya: true,
  },

  /* Отделка — за штуку, добавляется к базовой цене. */
  otdelka: OTDELKA,
  zashchita: BAZOVAYA_ZASHCHITA,
  dostavka: DOSTAVKA,
  oformlenie: PODAROCHNOE_OFORMLENIE,
  dostavkaPodarochnogo: DOSTAVKA_PODAROCHNOGO,
  bigovka: BIGOVKA,
  folgirovanie: FOLGIROVANIE,
  /* Тиснение прессом — отдельная услуга, не заменяет фольгирование:
     в счёте они складываются. */
  tisnenie: TISNENIE,
  plotnosti: NACENKA_ZA_PLOTNOST.stroki,
  /* Категории заполнения макета. Заведены 18.08.2026: струйник тратит
     чернила по площади краски, и белая листовка с фотоколлажем не могут
     стоить одинаково. Секретарь спрашивает это ДО того, как назвать цену. */
  zapolnenie: ZAPOLNENIE_MAKETA.stroki,

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

  /* Персональное поздравление — апсейл после согласованного заказа.
     Цены те же, что у бота: в двух каналах цифра должна быть одна. */
  podarki: PODARKI.pozicii.filter((p) => (p as { aktivna?: boolean }).aktivna !== false),

  /* Скидка пенсионерам. В счёт НЕ вносится: подтверждается
     удостоверением на месте. Секретарь про неё говорит. */
  skidkaPensioneram: SKIDKA_PENSIONERAM.aktivna ? SKIDKA_PENSIONERAM : null,

  /* Предоплата: процент, номер для перевода и — когда появится —
     ссылка на оплату вместе с нарисованным по ней QR-кодом. */
  oplata: {
    procent: OPLATA.predoplataProcent,
    /* Половина вперёд на тиражах от 200 штук: 30% не покрывают
       материалы, а купить их надо до печати. */
    procentBolshoj: OPLATA.predoplataBolshojTirazh,
    // Ниже этой суммы заказ оплачивается целиком и сразу.
    melkijDo: OPLATA.melkijZakazDo,
    bolshojOt: OPLATA.bolshojTirazhOt,
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
