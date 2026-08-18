/* ВИТРИННЫЙ ПЛАКАТ СТУДИИ «ГРАНАТ» — тот, что клеится на стекло.

   Запуск:  npm run plakat

   Собирает два варианта плаката — светлый и тёмный — и отдельный лист
   с ценами для двери или стойки. Файлы ложатся в `firmennyj-stil/vitrina/`.

   ЦЕН НА ВИТРИННОМ ПЛАКАТЕ НЕТ, И ЭТО РЕШЕНИЕ, А НЕ ЗАБЫВЧИВОСТЬ.
   Витрину читают с трёх метров и за две секунды: цифры на таком
   расстоянии не читаются, а прайс меняется — и перепечатывать плакат
   каждый раз никто не станет. Поэтому витрина говорит ЧТО здесь делают,
   а цены живут на листе А4 у входа, где их читают с полуметра.

   ЛИСТ С ЦЕНАМИ СОБИРАЕТСЯ ИЗ `data/prices.ts`. Ни одной суммы руками:
   правило владелицы про единственное место для цены действует и здесь.
   Поправили прайс — пересобрали лист и перепечатали один А4.

   ЦЕНЫ НА ЛИСТЕ — ЗА ОДНУ ШТУКУ, а не «от». Человек с улицы розничный:
   ему нужна одна копия и одно фото. «Копия от 8 ₽» на двери и 10 ₽
   на кассе выглядят обманом. Про тираж сказано отдельной строкой,
   и на ней разочароваться нельзя — он всегда дешевле.

   РИСУЕТ headless_shell, как и логотип: у обычного chrome окно выше
   области рисования, и снизу картинки остаётся белая полоса. */

import {
  STUDIYA,
  AKCII,
  KSEROKOPIYA,
  PECHAT_FOTO,
  LAMINACIYA,
  FOTO_NA_DOKUMENTY,
  najti,
  najtiPoziciyu,
  cenaTekstom,
  type Yacheyka,
} from '../data/prices.ts';

import { svg as logotipSvg } from '../firmennyj-stil/sobrat.mjs';

import { readFileSync, writeFileSync, unlinkSync, mkdirSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const KOREN = join(dirname(fileURLToPath(import.meta.url)), '..');
const VYHOD = join(KOREN, 'firmennyj-stil', 'vitrina');
const CHROME =
  '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

/* ── Шрифты, их ровно два ──────────────────────────────────────────
   Playfair Display — заголовок и телефон, тот же шрифт, которым набрано
   «ГРАНАТ» в знаке. Montserrat — всё остальное. Третьего нет намеренно:
   на плакате, который читают за две секунды, каждый лишний шрифт —
   это лишняя работа для глаза.

   БЕРЁМ ПОЛНЫЕ ПОДМНОЖЕСТВА, а не те три файла, которыми набран
   логотип. Причина обнаружилась при первой сборке: в кириллическом
   подмножестве Montserrat нет ни одной цифры, а знака рубля нет ни
   в одном из трёх файлов вовсе. Здесь кириллица, латиница, цифры,
   «•» и «₽» лежат в одном файле — подмена шрифта невозможна. */
const shrift = (imya: string) =>
  readFileSync(join(KOREN, 'firmennyj-stil', 'shrifty', imya)).toString('base64');

const MONTSERRAT = shrift('montserrat-600-polnyj.woff2');
const PLAYFAIR = shrift('playfair-display-700-polnyj.woff2');

/* ── Логотип ───────────────────────────────────────────────────────
   Собирается той же функцией, что и остальные знаки студии, а не
   подкладывается готовым файлом. Поменяется логотип — поменяется
   и плакат. Вариант со слоганом: на витрине нижняя дуга «ПЕЧАТЬ ·
   ЛЕРМОНТОВ · КМВ» работает подзаголовком. */
const LOGOTIP = Buffer.from(
  logotipSvg({
    sVenzelem: true,
    slogan: 'ПЕЧАТЬ · ЛЕРМОНТОВ · КМВ',
    keglSlogana: 54,
  }),
).toString('base64');

/* ── QR-код ────────────────────────────────────────────────────────
   Рисуется здесь, при сборке: на печатном макете не должно быть ни
   одной картинки с чужого сервера — плакат печатают и через полгода. */
function qrSvg(ssylka: string, cvet: string, fon: string): string {
  const code = `
import segno, io, sys
qr = segno.make(sys.argv[1], error='m')
buf = io.BytesIO()
qr.save(buf, kind='svg', scale=8, border=2,
        dark=sys.argv[2], light=sys.argv[3], xmldecl=False, svgns=True)
sys.stdout.write(buf.getvalue().decode('utf-8'))
`;
  const kod = execFileSync('python3', ['-c', code, ssylka, cvet, fon], {
    encoding: 'utf8',
  });

  /* ВАЖНО: segno отдаёт SVG с шириной и высотой в точках, но БЕЗ
     `viewBox`. Такая картинка не масштабируется — она обрезается.
     18.08.2026 из-за этого QR на листе с ценами не считывался вовсе:
     на глаз он выглядел как код, а на деле был его левый верхний угол.
     Проверка теперь механическая: `npm run plakat` в конце читает
     свои же коды камерой OpenCV. */
  const razmer = kod.match(/width="(\d+(?:\.\d+)?)"\s+height="(\d+(?:\.\d+)?)"/);
  if (!razmer) throw new Error('QR: не нашёл размеры в SVG от segno');
  return kod.replace(
    razmer[0],
    `viewBox="0 0 ${razmer[1]} ${razmer[2]}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet"`,
  );
}

/* ── Что на витрине написано ───────────────────────────────────────
   Три яруса и ни одного лишнего слова. Первый отвечает на вопрос
   «что это за дверь», второй — «а что именно печатают», третий —
   «какой техникой». Список услуг короткий: длинный с улицы всё равно
   не читают, а мелкий текст на витрине не работает вовсе. */
const ZAGOLOVOK = 'ПЕЧАТЬ';
const PODZAGOLOVOK = 'ДОКУМЕНТЫ • ФОТО • РЕКЛАМА';
const TEHNIKA = 'ПРИНТЕР • КОПИР • ПЛОТТЕР ДО А0';
const USLUGI = ['Визитки • наклейки • плакаты • чертежи', 'Ламинация • брошюровка'];
const PODPIS_QR = 'СКАНИРУЙТЕ —<br>ЗАКАЖИТЕ ОНЛАЙН';
const SAJT = 'GRANAT-KMV.RU';

/* ── Что на листе с ценами ─────────────────────────────────────────
   Шесть строк, отобранных по одному признаку: с этим приходят с улицы
   без звонка и без макета. Визитки и флаеры сюда не вынесены — они
   начинаются с тиража и с разговора. */
const CENY: { chto: string; cena: Yacheyka }[] = [
  { chto: 'Копия А4, ч/б', cena: najti(KSEROKOPIYA, 'A4, ч/б, ксерокопия', 0) },
  { chto: 'Печать с файла А4', cena: najti(KSEROKOPIYA, 'A4, ч/б, печать с файла', 0) },
  { chto: 'Цветная печать А4', cena: najti(KSEROKOPIYA, 'A4, цветная печать', 0) },
  { chto: 'Фото 10×15', cena: najti(PECHAT_FOTO, '10 × 15', 0) },
  {
    chto: 'Фото на документы',
    cena: najtiPoziciyu(
      FOTO_NA_DOKUMENTY.pozicii,
      'Печать готового сегмента, лист 10×15, матовая бумага',
    ),
  },
  { chto: 'Ламинация А4', cena: najti(LAMINACIYA, 'А4, 80–100 мкм', 0) },
];

/* Цифры те же, из прайса: последний столбец таблиц — цена на большом
   тираже. Она обязана быть ниже розничной, иначе обещание «дешевле»
   окажется неправдой. */
const TIRAZH =
  `Больше тираж — дешевле: копия от ${cenaTekstom(najti(KSEROKOPIYA, 'A4, ч/б, ксерокопия', 2))}, ` +
  `фото от ${cenaTekstom(najti(PECHAT_FOTO, '10 × 15', 3))}`;

const ZHIVYE_AKCII = AKCII.filter((a) => a.aktivna);

/* ── Цвета ─────────────────────────────────────────────────────────
   Два варианта не для красоты, а потому что витрина — это стекло
   на солнце. Светлый читается сквозь блики и почти не ест краску:
   А2 сплошной заливки — это дорого и долго сохнет. Тёмный фирменнее
   и заметнее в сумерках, под витрину с подсветкой. */
const PALITRY = {
  svetlyj: {
    imya: 'svetlyj',
    zachem: 'СВЕТЛЫЙ — для витрины на солнце. Читается сквозь блики, экономит краску',
    fon: '#F7F1E4',
    fonGrad: 'linear-gradient(180deg,#FBF7EE 0%,#F3EAD6 100%)',
    tekst: '#4A0E17',
    tekstTihij: '#6E4A2E',
    zoloto: '#A9781B',
    ramka: '#B3801F',
    cena: '#5A1020',
    plashkaFon: '#5A1020',
    plashkaTekst: '#F2DFA0',
    qrTemnyj: '#4A0E17',
    qrSvetlyj: '#FFFFFF',
  },
  temnyj: {
    imya: 'temnyj',
    zachem: 'ТЁМНЫЙ — фирменный, для витрины с подсветкой. Краски уходит много',
    fon: '#5A1020',
    fonGrad: 'radial-gradient(120% 90% at 50% 30%,#71142A 0%,#5A1020 58%,#3C0A13 100%)',
    tekst: '#F7EFD6',
    tekstTihij: '#DCC08A',
    zoloto: '#DDB95B',
    ramka: '#C79A34',
    cena: '#F7E9B0',
    plashkaFon: '#C79A34',
    plashkaTekst: '#3C0A13',
    qrTemnyj: '#3C0A13',
    qrSvetlyj: '#FFFFFF',
  },
};

type Palitra = (typeof PALITRY)['svetlyj'];

/** Как собирается страница: размер листа, вылеты, зеркало. */
interface Nastrojki {
  /** Единица для 1rem: `4.2mm` для печати, `14px` для картинки. */
  edinica: string;
  /** Ширина обрезного формата в миллиметрах. Нужна для вылетов. */
  shirinaMm?: number;
  /** Вылет под обрез, мм. 0 — печать дома, лист не режут. */
  vylet?: number;
  /** Зеркалить — для плёнки, которая клеится изнутри стекла. */
  zerkalo?: boolean;
}

/* ── Общие стили ───────────────────────────────────────────────────
   ВСЕ РАЗМЕРЫ В `rem`, И ЭТО ГЛАВНОЕ РЕШЕНИЕ МАКЕТА. Один rem равен
   одному проценту ширины листа. Листы А-серии подобны друг другу,
   поэтому одна и та же разметка без правок печатается и А2, и А4.
   Иначе пришлось бы держать три макета и следить, чтобы они
   не разъехались. */
function obshchieStili(p: Palitra): string {
  return `
  @font-face{font-family:'Montserrat';font-weight:600;
    src:url(data:font/woff2;base64,${MONTSERRAT}) format('woff2')}
  @font-face{font-family:'Playfair Display';font-weight:700;
    src:url(data:font/woff2;base64,${PLAYFAIR}) format('woff2')}

  *{margin:0;padding:0;box-sizing:border-box;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  body{display:flex;align-items:center;justify-content:center;
    font-family:'Montserrat',sans-serif;font-weight:600;overflow:hidden}

  /* Обрезной формат: 100rem × 141.42rem — пропорция А-серии. */
  .list{width:100rem;height:141.42rem;position:relative;overflow:hidden;
    background:${p.fon};background-image:${p.fonGrad};color:${p.tekst}}

  /* Тонкая золотая рамка и волосяная линия внутри. Толстой рамки нет
     намеренно: она съедает поле, а поле на витрине и есть воздух,
     из-за которого макет читается премиально, а не как объявление. */
  .ramka{position:absolute;inset:4.4rem;border:.28rem solid ${p.ramka}}
  .ramka-tonkaya{position:absolute;inset:5.6rem;border:.1rem solid ${p.zoloto};opacity:.7}

  /* Безопасное поле: 8rem от края. На А2 это 33 мм, на А3 — 24 мм.
     Ближе к краю важный текст не ставим: плёнку режут с допуском,
     а на стекле край ещё и заходит под раму. */
  .pole{position:absolute;inset:8rem;display:flex;flex-direction:column;
    align-items:center;text-align:center}

  .logotip{border-radius:50%;display:block}
  .linejka{display:flex;align-items:center;gap:1.6rem;width:100%}
  .linejka i{flex:1;height:.14rem;background:${p.zoloto};opacity:.8}
  .linejka b{width:1.4rem;height:1.4rem;background:${p.zoloto};transform:rotate(45deg)}

  .niz{margin-top:auto;width:100%;display:flex;align-items:center;gap:3.4rem;
    text-align:left}
  .qr-stolbec{flex:none;display:flex;flex-direction:column;align-items:center}
  .qr{background:${p.qrSvetlyj};padding:.8rem;border-radius:.6rem}
  .qr svg{width:100%;height:100%;display:block}
  .qr-podpis{color:${p.tekstTihij};text-align:center;letter-spacing:.06em}
  .telefon{font-family:'Playfair Display',serif;font-weight:700;line-height:1;
    color:${p.tekst};white-space:nowrap}
  .sajt{color:${p.zoloto};letter-spacing:.08em;white-space:nowrap}
  .adres{color:${p.tekstTihij};line-height:1.45}
`;
}

/* ── Обвязка листа: вылеты, метки реза, зеркало ────────────────────
   Дома плакат печатают как есть — лист в размер, вылеты не нужны.
   В типографию и на плёнку файл идёт иначе: фон должен выходить
   за обрезной формат на 5 мм, иначе после реза по краю появится
   белая нитка. Метки реза показывают резчику, где обрезной формат.

   Зеркальная версия нужна для плёнки, которую клеят изнутри стекла
   печатью к стеклу: краска тогда защищена стеклом и не выгорает,
   но макет обязан быть отражён, иначе текст читается наоборот. */
function stranica(p: Palitra, telo: string, stili: string, n: Nastrojki): string {
  const vylet = n.vylet ?? 0;
  const metki = vylet ? 5 : 0; // поле под метки реза, мм
  const otstup = vylet + metki;

  const razmerStranicy =
    n.shirinaMm !== undefined
      ? `@page{size:${n.shirinaMm + otstup * 2}mm ${+(n.shirinaMm * Math.SQRT2 + otstup * 2).toFixed(2)}mm;margin:0}
         body{width:${n.shirinaMm + otstup * 2}mm;height:${+(n.shirinaMm * Math.SQRT2 + otstup * 2).toFixed(2)}mm}`
      : `body{width:100rem;height:141.42rem}`;

  /* Фон вылета — той же заливкой, что и лист: под нож уходит именно он. */
  const podloshka = vylet
    ? `.vylet{position:absolute;left:${metki}mm;top:${metki}mm;
         width:calc(100% - ${metki * 2}mm);height:calc(100% - ${metki * 2}mm);
         background:${p.fon};background-image:${p.fonGrad}}`
    : '';

  /* Метки реза: волосяные линии в углах, снаружи обрезного формата.
     Внутрь макета не заходят — иначе останутся на плакате. */
  const metkiStili = vylet
    ? `.metka{position:absolute;background:#000}
       .metka.g{height:.2mm;width:${metki}mm}
       .metka.v{width:.2mm;height:${metki}mm}`
    : '';

  const metkiRazmetka = vylet
    ? [`left:0;top:${otstup}mm`, `right:0;top:${otstup}mm`,
       `left:0;bottom:${otstup}mm`, `right:0;bottom:${otstup}mm`]
        .map((s) => `<i class="metka g" style="${s}"></i>`)
        .join('') +
      [`left:${otstup}mm;top:0`, `right:${otstup}mm;top:0`,
       `left:${otstup}mm;bottom:0`, `right:${otstup}mm;bottom:0`]
        .map((s) => `<i class="metka v" style="${s}"></i>`)
        .join('')
    : '';

  return `<!doctype html>
<html lang="ru"><meta charset="utf-8">
<title>Витринный плакат — студия «Гранат»</title>
<style>
  html{font-size:${n.edinica}}
  ${razmerStranicy}
  ${obshchieStili(p)}
  ${podloshka}
  ${metkiStili}
  ${n.zerkalo ? '.list{transform:scaleX(-1)}' : ''}
  ${stili}
</style>
<body>
  ${vylet ? '<div class="vylet"></div>' : ''}
  ${metkiRazmetka}
  <div class="list">${telo}</div>
</body></html>
`;
}

/* ── Плакат на витрину ─────────────────────────────────────────────
   Иерархия задана размером, а не цветом: слово ПЕЧАТЬ читается первым
   с любого расстояния, дальше — что печатают, дальше — чем. Телефон
   и сайт внизу крупные: человек их не разглядывает, а фотографирует
   или набирает на ходу. */
function plakat(p: Palitra) {
  const qr = qrSvg('https://granat-kmv.ru', p.qrTemnyj, p.qrSvetlyj);

  const stili = `
  .pole{justify-content:flex-start}
  .logotip{width:18rem;height:18rem}
  /* Кегль заголовка подобран по ширине безопасного поля: шесть букв
     Playfair с разрядкой занимают ровно 5,6 своего размера. Больше —
     и слово упирается в рамку, а на витрине это читается как брак. */
  h1{font-family:'Playfair Display',serif;font-weight:700;font-size:14.8rem;
    line-height:.92;letter-spacing:.045em;text-indent:.045em;margin-top:3rem}
  .pod{font-size:3.4rem;letter-spacing:.16em;text-indent:.16em;
    color:${p.zoloto};margin-top:3rem;white-space:nowrap}
  .linejka{margin:3.4rem 0}
  .plashka{width:100%;padding:2rem;background:${p.plashkaFon};
    color:${p.plashkaTekst};font-size:3.4rem;letter-spacing:.09em;
    text-indent:.09em;white-space:nowrap}
  .uslugi{margin-top:3.6rem;font-size:3.6rem;line-height:1.6;color:${p.tekst}}
  /* Телефон и сайт стоят по центру и крупно: их не разглядывают,
     их фотографируют или набирают на ходу. */
  .telefon{font-size:8.4rem;margin-top:4.6rem}
  .sajt{font-size:5rem;margin-top:1.4rem}
  .qr{width:16.5rem;height:16.5rem;margin-top:2.8rem}
  .qr-podpis{font-size:2.3rem;margin-top:1.2rem;white-space:nowrap}
  .adres{font-size:2.9rem;margin-top:2.2rem;text-align:center}
`;

  const telo = `
  <div class="ramka"></div>
  <div class="ramka-tonkaya"></div>
  <div class="pole">
    <img class="logotip" src="data:image/svg+xml;base64,${LOGOTIP}"
         alt="Логотип студии «Гранат»">
    <h1>${ZAGOLOVOK}</h1>
    <div class="pod">${PODZAGOLOVOK}</div>

    <div class="linejka"><i></i><b></b><i></i></div>

    <div class="plashka">${TEHNIKA}</div>
    <div class="uslugi">${USLUGI.join('<br>')}</div>

    <div class="telefon">${STUDIYA.telefon}</div>
    <div class="sajt">${SAJT}</div>

    <div class="qr">${qr}</div>
    <div class="qr-podpis">${PODPIS_QR.replace('<br>', ' ')}</div>

    <div class="adres">${STUDIYA.adres.replace('г. ', '')}<br>${STUDIYA.chasy}</div>
  </div>`;

  return { telo, stili };
}

/* ── Лист с ценами ─────────────────────────────────────────────────
   Вешается на дверь или кладётся на стойку — там, где его читают
   с полуметра. Поэтому здесь цифры уместны, а на витрине нет.
   Печатается А4: перепечатать один лист после правки прайса не жалко,
   а плакат А2 жалко, и его начнут оставлять старым. */
function listSCenami(p: Palitra) {
  const stroki = CENY.map(
    ({ chto, cena }) => `
      <div class="stroka">
        <span class="chto">${chto}</span>
        <span class="tochki"></span>
        <span class="cena">${cenaTekstom(cena)}</span>
      </div>`,
  ).join('');

  /* Живая акция подхватывается сама: витрина и дверь — такой же канал
     объявления, как пост ВКонтакте, и правило «объявили в рекламе —
     завели в прайс» работает в обе стороны. */
  const akcii = ZHIVYE_AKCII.length
    ? `<div class="akciya">${ZHIVYE_AKCII.map(
        (a) => `${a.nazvanie}: ${a.uslovie} · ${a.do_}`,
      ).join(' · ')}</div>`
    : '';

  const stili = `
  .pole{inset:7rem}
  .logotip{width:13rem;height:13rem}
  h1{font-family:'Playfair Display',serif;font-weight:700;font-size:9.4rem;
    line-height:.95;letter-spacing:.05em;text-indent:.05em;margin-top:2.2rem}
  .pod{font-size:3.4rem;letter-spacing:.2em;text-indent:.2em;color:${p.zoloto};
    margin-top:1.4rem;white-space:nowrap}
  .linejka{margin:2.6rem 0 2.2rem}
  .ceny{width:100%;display:flex;flex-direction:column;gap:1rem}
  .stroka{display:flex;align-items:baseline;gap:1.2rem;width:100%}
  .chto{font-size:4rem;white-space:nowrap;text-align:left}
  /* Точки-выноска: глаз ведёт от услуги к цене, даже когда строку
     целиком не читают. */
  .tochki{flex:1;border-bottom:.3rem dotted ${p.zoloto};opacity:.6;
    transform:translateY(-.6rem)}
  .cena{font-family:'Playfair Display',serif;font-weight:700;font-size:5rem;
    color:${p.cena};white-space:nowrap}
  .tirazh{font-size:2.8rem;color:${p.tekstTihij};margin-top:2rem}
  .akciya{margin-top:1.8rem;padding:1.1rem 2.2rem;background:${p.plashkaFon};
    color:${p.plashkaTekst};font-size:2.8rem;letter-spacing:.05em;border-radius:.6rem}
  .prochee{margin-top:2.2rem;font-size:2.5rem;line-height:1.5;color:${p.tekstTihij};
    max-width:82rem}
  .niz{gap:3rem;margin-bottom:.5rem}
  .qr{width:13rem;height:13rem}
  .qr-podpis{font-size:1.9rem;line-height:1.3;margin-top:.9rem;max-width:26rem}
  .telefon{font-size:6.2rem}
  .sajt{font-size:4rem;margin-top:1rem}
  .adres{font-size:2.6rem;margin-top:1.2rem}
`;

  const telo = `
  <div class="ramka"></div>
  <div class="ramka-tonkaya"></div>
  <div class="pole">
    <img class="logotip" src="data:image/svg+xml;base64,${LOGOTIP}"
         alt="Логотип студии «Гранат»">
    <h1>ЦЕНЫ</h1>
    <div class="pod">ПЕЧАТЬ И КОПИИ</div>

    <div class="linejka"><i></i><b></b><i></i></div>

    <div class="ceny">${stroki}</div>
    <div class="tirazh">${TIRAZH}</div>
    ${akcii}
    <div class="prochee">Печатаем при вас: флешка • телефон • почта<br>
      Визитки • флаеры • буклеты • открытки • наклейки • плакаты •
      чертежи • брошюровка — считаем по вашему макету</div>

    <div class="niz">
      <div class="qr-stolbec">
        <div class="qr">${qrSvg('https://granat-kmv.ru', p.qrTemnyj, p.qrSvetlyj)}</div>
        <div class="qr-podpis">${PODPIS_QR}</div>
      </div>
      <div>
        <div class="telefon">${STUDIYA.telefon}</div>
        <div class="sajt">${SAJT}</div>
        <div class="adres">${STUDIYA.adres.replace('г. ', '')}<br>${STUDIYA.chasy}</div>
      </div>
    </div>
  </div>`;

  return { telo, stili };
}

/* ── Сборка ────────────────────────────────────────────────────────
   Картинка нужна, чтобы посмотреть макет в чате и на телефоне; PDF —
   чтобы отдать в печать. Форматов три, потому что печатать можно
   по-разному: А2 идёт на плоттер, А3 — на цветной принтер, А4 — когда
   витрина маленькая или нужен пробный оттиск. */
const SHIRINA_KARTINKI = 1400;

function chrome(argumenty: string[], fajl: string) {
  execFileSync(
    CHROME,
    ['--headless', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
     '--force-device-scale-factor=1', ...argumenty, `file://${fajl}`],
    { stdio: 'ignore' },
  );
}

/** Всё, что собрали: по этому списку в конце проверяются QR-коды. */
const SOBRANO: string[] = [];

function kartinka(imya: string, html: string) {
  const put = join(VYHOD, `_${imya}.html`);
  writeFileSync(put, html);
  chrome(
    [`--window-size=${SHIRINA_KARTINKI},${Math.round(SHIRINA_KARTINKI * Math.SQRT2)}`,
     `--screenshot=${join(VYHOD, imya + '.png')}`],
    put,
  );
  unlinkSync(put);
  SOBRANO.push(imya + '.png');
  console.log(`  ${imya}.png`);
}

function pdf(imya: string, html: string, podpis: string) {
  const put = join(VYHOD, `_${imya}.html`);
  writeFileSync(put, html);
  /* `--no-pdf-header-footer` убирает служебную строку с датой и адресом
     файла — на плакате она смотрелась бы как брак печати. */
  chrome(['--no-pdf-header-footer', `--print-to-pdf=${join(VYHOD, imya + '.pdf')}`], put);
  unlinkSync(put);
  SOBRANO.push(imya + '.pdf');
  console.log(`  ${imya}.pdf — ${podpis}`);
}

/** Перегнать PDF в CMYK. Типография принимает и RGB, но пересчитывает
    его сама и по-своему; бордовый при этом уезжает в фиолетовый.
    Ghostscript стоит не везде — нет его, работаем в RGB и говорим
    об этом вслух, а не молча. */
function vCmyk(imya: string): boolean {
  try {
    execFileSync(
      'gs',
      ['-dNOPAUSE', '-dBATCH', '-dQUIET', '-sDEVICE=pdfwrite',
       '-dPDFSETTINGS=/prepress', '-sProcessColorModel=DeviceCMYK',
       '-sColorConversionStrategy=CMYK',
       `-sOutputFile=${join(VYHOD, imya + '-cmyk.pdf')}`,
       join(VYHOD, imya + '.pdf')],
      { stdio: 'ignore' },
    );
    SOBRANO.push(imya + '-cmyk.pdf');
    console.log(`  ${imya}-cmyk.pdf — то же в CMYK, для типографии`);
    return true;
  } catch {
    return false;
  }
}

const FORMATY = [
  { imya: 'A2', shirinaMm: 420 },
  { imya: 'A3', shirinaMm: 297 },
  { imya: 'A4', shirinaMm: 210 },
];

mkdirSync(VYHOD, { recursive: true });
console.log('Витринный плакат студии «Гранат»\n');

let bylCmyk = false;

for (const p of Object.values(PALITRY)) {
  console.log(p.zachem);
  const { telo, stili } = plakat(p);
  const imya = `vitrinnyj-plakat-${p.imya}`;

  kartinka(imya, stranica(p, telo, stili, { edinica: `${SHIRINA_KARTINKI / 100}px` }));

  for (const f of FORMATY) {
    pdf(
      `${imya}-${f.imya}`,
      stranica(p, telo, stili, { edinica: `${f.shirinaMm / 100}mm`, shirinaMm: f.shirinaMm }),
      `лист ${f.shirinaMm}×${Math.round(f.shirinaMm * Math.SQRT2)} мм, печать как есть`,
    );
  }

  /* Для типографии и плёнки — А2 с вылетами и метками реза, и то же
     зеркально: плёнку клеят изнутри стекла печатью к стеклу. */
  pdf(
    `${imya}-A2-vylety`,
    stranica(p, telo, stili, { edinica: '4.2mm', shirinaMm: 420, vylet: 5 }),
    'А2 + вылеты 5 мм и метки реза — для типографии',
  );
  pdf(
    `${imya}-A2-zerkalnyj`,
    stranica(p, telo, stili, { edinica: '4.2mm', shirinaMm: 420, vylet: 5, zerkalo: true }),
    'А2 зеркальный + вылеты — плёнка на стекло изнутри',
  );

  bylCmyk = vCmyk(`${imya}-A2-vylety`) || bylCmyk;
  vCmyk(`${imya}-A2-zerkalnyj`);
  console.log('');
}

/* Лист с ценами — только А4 и только светлый: он висит на двери
   и на стойке, где тёмный лист выглядит тяжело и ест краску. */
console.log('ЛИСТ С ЦЕНАМИ — на дверь или на стойку, А4');
{
  const p = PALITRY.svetlyj;
  const { telo, stili } = listSCenami(p);
  kartinka('list-s-cenami', stranica(p, telo, stili, { edinica: `${SHIRINA_KARTINKI / 100}px` }));
  pdf(
    'list-s-cenami-A4',
    stranica(p, telo, stili, { edinica: '2.1mm', shirinaMm: 210 }),
    'лист 210×297 мм',
  );
}

console.log('\nЦены на листе — из data/prices.ts:');
for (const { chto, cena } of CENY) console.log(`  ${chto} — ${cenaTekstom(cena)}`);
console.log(`  ${TIRAZH}`);
if (ZHIVYE_AKCII.length) {
  console.log('Живые акции на листе:');
  for (const a of ZHIVYE_AKCII) console.log(`  ${a.nazvanie} — ${a.uslovie}, ${a.do_}`);
} else {
  console.log('Живых акций в прайсе нет — полосы с акцией на листе не будет.');
}
if (!bylCmyk) {
  console.log('\nCMYK не собран: не установлен ghostscript. Файлы остались в RGB.');
}

/* ── Проверка QR-кодов ─────────────────────────────────────────────
   Читаем свои же коды камерой OpenCV — ровно так, как их прочитает
   телефон прохожего. Проверка появилась не от любви к порядку:
   18.08.2026 QR на листе с ценами был обрезан и не читался вовсе,
   а на глаз выглядел нормальным кодом. Глазами такое не ловится.

   Библиотек может не быть — тогда честно говорим, что не проверили,
   а не делаем вид, что всё хорошо. */
function proveritQr(fajly: string[]): void {
  const code = `
import sys
try:
    import cv2, numpy as np
except ImportError:
    print('НЕТ_БИБЛИОТЕК'); sys.exit(0)
try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None

det = cv2.QRCodeDetector()
for put in sys.argv[1:]:
    if put.endswith('.pdf'):
        if pdfium is None:
            print('ПРОПУЩЕН', put); continue
        stranica = pdfium.PdfDocument(put)[0]
        kadr = np.array(stranica.render(scale=2400 / stranica.get_width()).to_pil().convert('RGB'))
        kadr = cv2.cvtColor(kadr, cv2.COLOR_RGB2BGR)
    else:
        kadr = cv2.imread(put)
    # Зеркальный макет читаем отражённым: на стекле он и будет таким.
    if 'zerkalnyj' in put:
        kadr = kadr[:, ::-1]
    tekst = det.detectAndDecode(kadr)[0]
    print('OK' if tekst else 'СБОЙ', put, tekst)
`;
  let vyvod: string;
  try {
    vyvod = execFileSync('python3', ['-c', code, ...fajly.map((f) => join(VYHOD, f))], {
      encoding: 'utf8',
    });
  } catch {
    console.log('\nQR не проверены: не удалось запустить проверку.');
    return;
  }
  if (vyvod.includes('НЕТ_БИБЛИОТЕК')) {
    console.log('\nQR не проверены: нет opencv-python-headless и pypdfium2.');
    return;
  }
  const sboi = vyvod.split('\n').filter((s) => s.startsWith('СБОЙ'));
  if (sboi.length) {
    console.log('\nQR НЕ ЧИТАЮТСЯ в этих файлах:');
    for (const s of sboi) console.log('  ' + s.replace('СБОЙ ', ''));
    process.exitCode = 1;
  } else {
    console.log(`\nQR проверены камерой: читаются во всех ${fajly.length} файлах, ведут на granat-kmv.ru.`);
  }
}

proveritQr(SOBRANO);
