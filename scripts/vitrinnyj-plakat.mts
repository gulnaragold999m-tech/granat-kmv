/* ВИТРИННЫЙ ПЛАКАТ СТУДИИ «ГРАНАТ» — тот, что клеится на стекло.

   Запуск:  npm run plakat

   Собирает два варианта — светлый и тёмный — и для каждого четыре файла:
   картинку для показа в чате и три PDF под печать (А2, А3, А4).

   ПОЧЕМУ СКРИПТОМ, А НЕ КАРТИНКОЙ. Плакат висит на витрине и обещает
   цену прохожему. Цена живёт в `data/prices.ts` — правило владелицы,
   и оно уже спасало от разъезда прайса на сайте, в боте и в макетах.
   Нарисованный руками плакат к этому правилу не подключить: поправят
   прайс, а на стекле останется старая цифра, и человек придёт с ней.
   Здесь ни одной суммы нет — все берутся из таблиц прайса при сборке.

   ЦЕНЫ БЕРЁМ ЗА ОДНУ ШТУКУ, а не «от». Прохожий с улицы — розничный
   клиент: ему нужна одна копия, одно фото, один документ. Написать
   «копия от 8 ₽» и взять с него 10 ₽ — обмануть на витрине. Поэтому
   на плакате стоит цена за первую штуку, а про тираж сказано отдельной
   строкой: он всегда дешевле, и разочароваться на нём нельзя.

   АКЦИИ ПОДХВАТЫВАЮТСЯ САМИ. Есть в прайсе живая акция — на плакате
   появляется полоса с её названием и сроком. Витрина — такой же канал
   объявления, как пост ВКонтакте, и правило «объявили в рекламе —
   завели в прайс» работает в обе стороны.

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

/* ── Шрифты ────────────────────────────────────────────────────────
   Берём ПОЛНЫЕ подмножества, а не те три файла, которыми набран
   логотип. Причина простая и обнаружилась при первой сборке:
   в кириллическом подмножестве Montserrat нет ни одной цифры, а знака
   рубля нет ни в одном из трёх файлов вовсе. Плакат без цифр и без «₽»
   бессмыслен, а системный запасной шрифт — это чужие буквы посреди
   фирменного макета. Здесь цифры, латиница, кириллица и рубль лежат
   в одном файле, поэтому подмена шрифта невозможна в принципе. */
const shrift = (imya: string) =>
  readFileSync(join(KOREN, 'firmennyj-stil', 'shrifty', imya)).toString('base64');

const MONTSERRAT = shrift('montserrat-600-polnyj.woff2');
const PLAYFAIR = shrift('playfair-display-700-polnyj.woff2');

/* ── Логотип ───────────────────────────────────────────────────────
   Собирается той же функцией, что и остальные логотипы студии, а не
   подкладывается готовым файлом. Поменяется знак — поменяется и плакат.
   Вариант со слоганом «ПЕЧАТЬ · ЛЕРМОНТОВ · КМВ»: на витрине он
   работает как подзаголовок и говорит прохожему, что здесь делают. */
const LOGOTIP = Buffer.from(
  logotipSvg({
    sVenzelem: true,
    slogan: 'ПЕЧАТЬ · ЛЕРМОНТОВ · КМВ',
    keglSlogana: 54,
  }),
).toString('base64');

/* ── QR-код ────────────────────────────────────────────────────────
   Рисуется здесь, при сборке, как и в шпаргалке секретаря: на макете
   не должно быть ни одной картинки с чужого сервера — плакат печатают
   и через полгода, когда сервер может не ответить. */
function qrSvg(ssylka: string, cvet: string, fon: string): string {
  const code = `
import segno, io, sys
qr = segno.make(sys.argv[1], error='m')
buf = io.BytesIO()
qr.save(buf, kind='svg', scale=8, border=2,
        dark=sys.argv[2], light=sys.argv[3], xmldecl=False, svgns=True)
sys.stdout.write(buf.getvalue().decode('utf-8'))
`;
  return execFileSync('python3', ['-c', code, ssylka, cvet, fon], {
    encoding: 'utf8',
  });
}

/* ── Что показываем ────────────────────────────────────────────────
   Шесть строк, больше на витрину не влезет читаемым кеглем. Отобраны
   по одному признаку: с этим приходят с улицы без звонка и без макета.
   Визитки, флаеры и буклеты в цену не вынесены — они начинаются
   с тиража и с разговора, для них внизу отдельная строка перечнем. */
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

/* Строка про тираж. Цифры те же, из прайса: последний столбец таблиц —
   это цена на большом тираже. Она обязана быть ниже розничной, иначе
   обещание «дешевле» окажется неправдой. */
const TIRAZH =
  `Больше тираж — дешевле: копия от ${cenaTekstom(najti(KSEROKOPIYA, 'A4, ч/б, ксерокопия', 2))}, ` +
  `фото от ${cenaTekstom(najti(PECHAT_FOTO, '10 × 15', 3))}`;

const ZHIVYE_AKCII = AKCII.filter((a) => a.aktivna);

/* ── Цвета ─────────────────────────────────────────────────────────
   Два варианта не для красоты, а потому что витрина — это стекло
   на солнце. Светлый читается сквозь блики и почти не ест краску:
   А2 сплошной заливки на своём принтере — это дорого и долго сохнет.
   Тёмный — фирменный и заметнее в сумерках, под витрину с подсветкой. */
const PALITRY = {
  svetlyj: {
    imya: 'svetlyj',
    zachem: 'СВЕТЛЫЙ — для витрины на солнце. Читается сквозь блики, экономит краску',
    fon: '#F7F1E4',
    fonGrad: 'linear-gradient(180deg,#FBF7EE 0%,#F4ECDA 100%)',
    tekst: '#4A0E17',
    tekstTihij: '#6E4A2E',
    zoloto: '#A9781B',
    ramka: '#5A1020',
    cena: '#5A1020',
    plashkaFon: '#5A1020',
    plashkaTekst: '#F2DFA0',
    qrTemnyj: '#4A0E17',
    qrSvetlyj: '#FBF7EE',
  },
  temnyj: {
    imya: 'temnyj',
    zachem: 'ТЁМНЫЙ — фирменный, для витрины с подсветкой. Краски уходит много',
    fon: '#5A1020',
    fonGrad: 'radial-gradient(120% 90% at 50% 32%,#71142A 0%,#5A1020 58%,#3C0A13 100%)',
    tekst: '#F5E7C0',
    tekstTihij: '#DCC08A',
    zoloto: '#DDB95B',
    ramka: '#C79A34',
    cena: '#F7E9B0',
    plashkaFon: '#C79A34',
    plashkaTekst: '#3C0A13',
    qrTemnyj: '#3C0A13',
    qrSvetlyj: '#F5E7C0',
  },
};

type Palitra = (typeof PALITRY)['svetlyj'];

/* ── Разметка ──────────────────────────────────────────────────────
   ВСЕ РАЗМЕРЫ В `rem`, И ЭТО ГЛАВНОЕ РЕШЕНИЕ МАКЕТА. Один rem равен
   одному проценту ширины листа. Листы А-серии подобны друг другу —
   у А2, А3 и А4 одинаковые пропорции, — поэтому та же разметка без
   единой правки печатается любым из трёх размеров. Иначе пришлось бы
   держать три макета и следить, чтобы они не разъехались. */
function stranica(p: Palitra, edinica: string): string {
  const qr = qrSvg('https://granat-kmv.ru', p.qrTemnyj, p.qrSvetlyj);

  const stroki = CENY.map(
    ({ chto, cena }) => `
      <div class="stroka">
        <span class="chto">${chto}</span>
        <span class="tochki"></span>
        <span class="cena">${cenaTekstom(cena)}</span>
      </div>`,
  ).join('');

  const akcii = ZHIVYE_AKCII.length
    ? `<div class="akciya">${ZHIVYE_AKCII.map(
        (a) => `${a.nazvanie}: ${a.uslovie} · ${a.do_}`,
      ).join(' · ')}</div>`
    : '';

  return `<!doctype html>
<html lang="ru"><meta charset="utf-8">
<title>Витринный плакат — студия «Гранат»</title>
<style>
  @font-face{font-family:'Montserrat';font-weight:600;
    src:url(data:font/woff2;base64,${MONTSERRAT}) format('woff2')}
  @font-face{font-family:'Playfair Display';font-weight:700;
    src:url(data:font/woff2;base64,${PLAYFAIR}) format('woff2')}

  /* Ширина листа = 100rem, высота = 141.42rem: пропорция А-серии. */
  html{font-size:${edinica};-webkit-print-color-adjust:exact;print-color-adjust:exact}
  *{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  body{width:100rem;height:141.42rem;background:${p.fon};background-image:${p.fonGrad};
    color:${p.tekst};font-family:'Montserrat',sans-serif;font-weight:600;
    overflow:hidden;position:relative}

  /* Двойная рамка: толстая держит плакат на стекле как табличку,
     тонкая золотая внутри — фирменный приём с кольца логотипа. */
  .ramka{position:absolute;inset:2.6rem;border:0.75rem solid ${p.ramka}}
  .ramka-tonkaya{position:absolute;inset:4.3rem;border:0.2rem solid ${p.zoloto};opacity:.85}

  .list{position:absolute;inset:6.2rem 7.5rem 6.6rem;display:flex;flex-direction:column;
    align-items:center;text-align:center}

  .logotip{width:15.4rem;height:15.4rem;border-radius:50%;display:block}

  h1{font-family:'Playfair Display',serif;font-weight:700;font-size:11rem;
    line-height:.94;letter-spacing:.06em;text-indent:.06em;color:${p.tekst};margin-top:2rem}
  .pod{font-size:3.9rem;letter-spacing:.3em;text-indent:.3em;color:${p.zoloto};
    margin-top:1.4rem;white-space:nowrap}

  /* Линейка с ромбом посередине — тот же ромб, что в логотипе
     без вензеля. Она делит плакат на «кто мы» и «почём». */
  .linejka{display:flex;align-items:center;gap:1.6rem;width:100%;margin:2.8rem 0 2.2rem}
  .linejka i{flex:1;height:.2rem;background:${p.zoloto};opacity:.75}
  .linejka b{width:1.5rem;height:1.5rem;background:${p.zoloto};transform:rotate(45deg)}

  .ceny{width:100%;display:flex;flex-direction:column;gap:.6rem}
  .stroka{display:flex;align-items:baseline;gap:1.2rem;width:100%}
  .chto{font-size:3.7rem;white-space:nowrap;text-align:left}
  /* Точки-выноска: глаз ведёт от услуги к цене, даже когда смотрят
     с трёх метров и строку целиком не читают. */
  .tochki{flex:1;border-bottom:.32rem dotted ${p.zoloto};opacity:.6;transform:translateY(-.6rem)}
  .cena{font-family:'Playfair Display',serif;font-weight:700;font-size:4.8rem;
    color:${p.cena};white-space:nowrap}

  .tirazh{font-size:2.7rem;color:${p.tekstTihij};margin-top:1.5rem;letter-spacing:.02em}

  .akciya{margin-top:1.6rem;padding:1rem 2.2rem;background:${p.plashkaFon};
    color:${p.plashkaTekst};font-size:2.7rem;letter-spacing:.06em;border-radius:.6rem}

  /* Плашка со словом ПРИНТЕР — то, ради чего плакат вешают: прохожий
     должен с улицы понять, что здесь можно распечатать. */
  .plashka{margin-top:2.2rem;padding:1.4rem 2.6rem;background:${p.plashkaFon};color:${p.plashkaTekst};
    font-size:3.4rem;letter-spacing:.16em;text-indent:.16em;white-space:nowrap}
  .pri-vas{font-size:3.1rem;margin-top:1.5rem;color:${p.tekst};white-space:nowrap}
  .eshchyo{font-size:2.4rem;line-height:1.45;color:${p.tekstTihij};margin-top:1.1rem;
    max-width:80rem}

  .niz{margin-top:auto;width:100%;display:flex;align-items:center;gap:3rem;text-align:left}
  .qr{width:14rem;height:14rem;flex:none;background:${p.qrSvetlyj};padding:.6rem;border-radius:.6rem}
  .qr svg{width:100%;height:100%;display:block}
  .qr-stolbec{flex:none;display:flex;flex-direction:column;align-items:center}
  .qr-podpis{font-size:1.9rem;line-height:1.25;color:${p.tekstTihij};margin-top:.9rem;
    text-align:center;max-width:23rem}
  .telefon{font-family:'Playfair Display',serif;font-weight:700;font-size:6.1rem;
    line-height:1;letter-spacing:.02em;color:${p.tekst};white-space:nowrap}
  .adres{font-size:2.6rem;line-height:1.4;color:${p.tekstTihij};margin-top:1rem}
  .sajt{font-size:4.2rem;letter-spacing:.1em;color:${p.zoloto};margin-top:1rem;
    font-family:'Montserrat',sans-serif}
</style>
<body>
  <div class="ramka"></div>
  <div class="ramka-tonkaya"></div>
  <div class="list">
    <img class="logotip" src="data:image/svg+xml;base64,${LOGOTIP}"
         alt="Логотип студии «Гранат»">

    <h1>ПЕЧАТЬ</h1>
    <div class="pod">ДОКУМЕНТОВ И ФОТО</div>

    <div class="linejka"><i></i><b></b><i></i></div>

    <div class="ceny">${stroki}</div>
    <div class="tirazh">${TIRAZH}</div>
    ${akcii}

    <div class="plashka">ПРИНТЕР · КОПИР · ПЛОТТЕР ДО А0</div>
    <div class="pri-vas">Печатаем при вас: флешка · телефон · почта</div>
    <div class="eshchyo">Визитки · флаеры · буклеты · открытки · наклейки ·
      плакаты · чертежи · ламинация · брошюровка</div>

    <div class="niz">
      <div class="qr-stolbec">
        <div class="qr">${qr}</div>
        <div class="qr-podpis">Наведите камеру —<br>весь прайс на сайте</div>
      </div>
      <div>
        <div class="telefon">${STUDIYA.telefon}</div>
        <div class="adres">${STUDIYA.adres.replace('г. ', '')}<br>${STUDIYA.chasy}</div>
        <div class="sajt">GRANAT-KMV.RU</div>
      </div>
    </div>
  </div>
</body></html>
`;
}

/* ── Сборка файлов ─────────────────────────────────────────────────
   Картинка нужна, чтобы посмотреть макет в чате и на телефоне; PDF —
   чтобы отдать в печать. Три размера, потому что печатать плакат
   можно по-разному: А2 идёт на плоттер, А3 — на цветной принтер,
   А4 — если витрина маленькая или нужен пробный оттиск. */
const RAZMERY = [
  { imya: 'A2', shirinaMm: 420 },
  { imya: 'A3', shirinaMm: 297 },
  { imya: 'A4', shirinaMm: 210 },
];

/** Ширина картинки для показа. 1400 точек — влезает в чат и в телефон,
    при этом мелкий текст ещё читается. */
const SHIRINA_KARTINKI = 1400;

function chrome(argumenty: string[], fajl: string) {
  execFileSync(
    CHROME,
    [
      '--headless',
      '--disable-gpu',
      '--no-sandbox',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      ...argumenty,
      `file://${fajl}`,
    ],
    { stdio: 'ignore' },
  );
}

mkdirSync(VYHOD, { recursive: true });
console.log('Витринный плакат студии «Гранат»\n');

for (const p of Object.values(PALITRY)) {
  console.log(p.zachem);

  /* Картинка: единица измерения в точках, лист ровно 1400 в ширину. */
  const htmlKartinka = join(VYHOD, `_${p.imya}.html`);
  writeFileSync(htmlKartinka, stranica(p, `${SHIRINA_KARTINKI / 100}px`));
  const png = `vitrinnyj-plakat-${p.imya}.png`;
  chrome(
    [
      `--window-size=${SHIRINA_KARTINKI},${Math.round(SHIRINA_KARTINKI * 1.4142)}`,
      `--screenshot=${join(VYHOD, png)}`,
    ],
    htmlKartinka,
  );
  console.log(`  ${png}`);
  unlinkSync(htmlKartinka);

  /* PDF: единица в миллиметрах, размер листа задаётся через @page.
     `--no-pdf-header-footer` убирает служебную строку с датой и адресом
     файла — на плакате она смотрелась бы как брак печати. */
  for (const { imya, shirinaMm } of RAZMERY) {
    const vysotaMm = +(shirinaMm * Math.sqrt(2)).toFixed(2);
    const html = join(VYHOD, `_${p.imya}-${imya}.html`);
    writeFileSync(
      html,
      stranica(p, `${shirinaMm / 100}mm`).replace(
        '<style>',
        `<style>@page{size:${shirinaMm}mm ${vysotaMm}mm;margin:0}`,
      ),
    );
    const pdf = `vitrinnyj-plakat-${p.imya}-${imya}.pdf`;
    chrome(
      ['--no-pdf-header-footer', `--print-to-pdf=${join(VYHOD, pdf)}`],
      html,
    );
    console.log(`  ${pdf} — лист ${shirinaMm}×${vysotaMm} мм`);
    unlinkSync(html);
  }
  console.log('');
}

console.log('Цены на плакате — из data/prices.ts:');
for (const { chto, cena } of CENY) console.log(`  ${chto} — ${cenaTekstom(cena)}`);
console.log(`  ${TIRAZH}`);
if (ZHIVYE_AKCII.length) {
  console.log('Живые акции на плакате:');
  for (const a of ZHIVYE_AKCII) console.log(`  ${a.nazvanie} — ${a.uslovie}, ${a.do_}`);
} else {
  console.log('Живых акций в прайсе нет — полосы с акцией на плакате не будет.');
}
