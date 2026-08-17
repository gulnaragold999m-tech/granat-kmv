/* Сборка логотипа: SVG и PNG, оба варианта сразу.

   Запуск:  node firmennyj-stil/sobrat.mjs

   ПОЧЕМУ СКРИПТОМ, А НЕ РУКАМИ. Файлов получается шесть — два вектора,
   два PNG по 1500 и две пробы по 200. Правка размера или цвета в одном
   месте должна доехать до всех шести. Разъедутся — и мы получим ту же
   историю, что с ценой на макетах: на сайте одно, в карточке другое.

   ШРИФТЫ ВШИТЫ В ФАЙЛ. Playfair Display и Montserrat лежат рядом
   в `shrifty/` и вставляются в SVG как base64. Иначе вектор открылся бы
   на чужом компьютере системным шрифтом, и никто бы не понял, почему
   логотип «поплыл». Это те же шрифты, что заданы на сайте granat-kmv.ru.

   РИСУЕТ headless_shell, А НЕ chrome. У обычного chrome окно на 85 точек
   выше области рисования, и снизу картинки остаётся белая полоса. */

import { readFileSync, writeFileSync, unlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const TUT = dirname(fileURLToPath(import.meta.url));
const CHROME = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

const shrift = (imya) =>
  readFileSync(join(TUT, 'shrifty', imya)).toString('base64');

const PLAYFAIR = shrift('playfair-display-700.woff2');
const MONTSERRAT = shrift('montserrat-600.woff2');
/* Латиница отдельным шрифтом и под ДРУГИМ именем семейства.
   Причина: кириллическое подмножество Montserrat латинских букв
   не содержит вовсе, и адрес сайта набрался бы системным шрифтом —
   на глаз это чужие буквы посреди фирменного знака. */
const MONTSERRAT_LAT = shrift('montserrat-600-latin.woff2');
const VENZEL = readFileSync(join(TUT, 'venzel-g.png')).toString('base64');

/* СЛОГАН. Выбран владелицей 17.08.2026 из четырёх вариантов:
   «лучше написать Печать Лермонтов КМВ». Верхняя дуга говорит, КТО мы,
   нижняя — ЧТО делаем и ГДЕ. В картах география работает лучше
   красивых слов: человек ищет «печать Лермонтов», а не «запомнят
   с первого взгляда».

   Точки-разделители — не запятые: строка идёт по дуге, и запятая
   на изгибе читается как грязь. */
const SLOGAN = 'ПЕЧАТЬ · ЛЕРМОНТОВ · КМВ';
const KEGL_SLOGANA = 54;   // подобран под длину: 24 знака на дуге радиуса 545

/* Разрядка на сайте задана как .18em, а в SVG letter-spacing считается
   в точках. Поэтому переводим: 0.18 × размер шрифта. */
const razryadka = (kegl, em) => Math.round(kegl * em);

export function svg({ sVenzelem, slogan, keglSlogana = 46, sajt }) {
  /* С вензелем название меньше: втроём — дуга, вензель и слово — они
     не помещаются, если каждому дать полный размер.
     17.08.2026 поднято со 168 до 196: владелица выбрала вариант
     с вензелем основным, а в кружке 2ГИС из трёх ярусов читается только
     название. Больше 196 слово упирается в кольцо. */
  const kegl = sVenzelem ? (slogan && sajt ? 172 : slogan ? 180 : 196) : 232;

  /* СО СЛОГАНОМ ВСЁ ПОДНИМАЕТСЯ ВВЕРХ. Нижняя дуга — не прямая строка:
     краями она загибается вверх, к названию. При первой сборке слоган
     прошёл прямо сквозь «ГРАНАТ» — на глаз это было видно сразу,
     арифметикой не проверялось. Поэтому вензель и название сдвинуты
     выше, а внизу оставлена свободная полоса под дугу. */
  /* Когда внизу И слоган по дуге, И адрес строкой — ярусов становится
     пять, и каждому надо ужаться. Иначе низ забивается: адрес
     притирается к названию, а концы дуги лезут к адресу. */
  const vsyoSrazu = slogan && sajt;
  const venzelY = vsyoSrazu ? 300 : (slogan ? 310 : 372);
  const venzelH = vsyoSrazu ? 420 : (slogan ? 450 : 540);
  const venzelW = Math.round(venzelH * 299 / 400);   // пропорции картинки
  const nazvanieY = sVenzelem ? (slogan && sajt ? 900 : slogan ? 940 : 1120) : 872;
  const sajtY = slogan ? 990 : 1035;
  const keglSajta = slogan ? 42 : 46;

  return `<!-- Логотип студии «Гранат»${sVenzelem ? ' с вензелем' : ''}.
     Собран скриптом firmennyj-stil/sobrat.mjs — руками не править,
     правку затрёт следующая сборка. Шрифты: Playfair Display и
     Montserrat, те же, что заданы на сайте granat-kmv.ru. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 1500" width="1500" height="1500">
  <defs>
    <style>
      @font-face{font-family:'Playfair Display';font-weight:700;
        src:url(data:font/woff2;base64,${PLAYFAIR}) format('woff2')}
      @font-face{font-family:'Montserrat';font-weight:600;
        src:url(data:font/woff2;base64,${MONTSERRAT}) format('woff2')}
      @font-face{font-family:'Montserrat Lat';font-weight:600;
        src:url(data:font/woff2;base64,${MONTSERRAT_LAT}) format('woff2')}
    </style>
    <radialGradient id="fon" cx="50%" cy="40%" r="75%">
      <stop offset="0%"   stop-color="#71142A"/>
      <stop offset="62%"  stop-color="#5A1020"/>
      <stop offset="100%" stop-color="#420C15"/>
    </radialGradient>
    <linearGradient id="zoloto" x1="0" y1="0" x2="0.25" y2="1">
      <stop offset="0%"   stop-color="#F7E9B0"/>
      <stop offset="24%"  stop-color="#DDB95B"/>
      <stop offset="48%"  stop-color="#B3801F"/>
      <stop offset="72%"  stop-color="#EBD285"/>
      <stop offset="100%" stop-color="#9E6F17"/>
    </linearGradient>
    <linearGradient id="zolotoTonkoe" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#F2DFA0"/>
      <stop offset="50%"  stop-color="#C79A34"/>
      <stop offset="100%" stop-color="#EFD98F"/>
    </linearGradient>
    <path id="dugaVerh" fill="none" d="M 200,750 A 550,550 0 0 1 1300,750"/>
    <!-- Нижняя дуга идёт в обратную сторону — от левой точки через НИЗ
         к правой (sweep=0). Только так буквы стоят головой вверх;
         с sweep=1 слоган читался бы вверх ногами. -->
    <path id="dugaNiz" fill="none" d="M 205,750 A 545,545 0 0 0 1295,750"/>
  </defs>

  <rect width="1500" height="1500" fill="url(#fon)"/>
  <circle cx="750" cy="750" r="688" fill="none" stroke="url(#zoloto)" stroke-width="26"/>
  <circle cx="750" cy="750" r="645" fill="none" stroke="url(#zolotoTonkoe)" stroke-width="6"/>

  <text font-family="Montserrat" font-size="70" font-weight="600"
        letter-spacing="${razryadka(70, 0.22)}" fill="url(#zolotoTonkoe)">
    <textPath href="#dugaVerh" startOffset="50%" text-anchor="middle">ДИЗАЙНЕРСКАЯ СТУДИЯ</textPath>
  </text>
${sVenzelem ? `
  <image x="${750 - Math.round(venzelW / 2)}" y="${venzelY}" width="${venzelW}" height="${venzelH}" href="data:image/png;base64,${VENZEL}"/>
` : ''}
${slogan ? `
  <!-- Слоган по нижней дуге. Кегль подбирается под длину строки:
       длинная фраза мельче, короткая крупнее. Слишком крупная упрётся
       концами в кольцо и обрежется без предупреждения. -->
  <text font-family="Montserrat" font-size="${keglSlogana}" font-weight="600"
        letter-spacing="${razryadka(keglSlogana, 0.16)}" fill="url(#zolotoTonkoe)">
    <textPath href="#dugaNiz" startOffset="50%" text-anchor="middle">${slogan}</textPath>
  </text>` : ''}
  <text x="750" y="${nazvanieY}" text-anchor="middle"
        font-family="Playfair Display" font-size="${kegl}" font-weight="700"
        letter-spacing="${razryadka(kegl, 0.18)}" fill="url(#zoloto)">ГРАНАТ</text>
${sajt ? `
  <!-- Адрес сайта — прямой строкой под названием, а не по дуге.
       По дуге латиница с точками и дефисом читается плохо: точка
       на изгибе теряется, и адрес переписывают с ошибкой. -->
  <text x="750" y="${sajtY}" text-anchor="middle"
        font-family="Montserrat Lat" font-size="${keglSajta}" font-weight="600"
        letter-spacing="${razryadka(keglSajta, 0.12)}" fill="url(#zolotoTonkoe)">${sajt}</text>` : ''}
${sVenzelem ? '' : `
  <!-- Три ромба уравновешивают надпись по дуге сверху и не добавляют
       ни одной буквы, которую пришлось бы читать в размере ногтя. -->
  <g fill="url(#zolotoTonkoe)">
    <rect x="655" y="945" width="34" height="34" transform="rotate(45 672 962)"/>
    <rect x="733" y="938" width="48" height="48" transform="rotate(45 757 962)"/>
    <rect x="811" y="945" width="34" height="34" transform="rotate(45 828 962)"/>
  </g>
`}</svg>
`;
}

export function risovat(imyaSvg, storona, vyhod, krug) {
  const html = join(TUT, '_r.html');
  writeFileSync(html, `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;padding:0;width:${storona}px;height:${storona}px;overflow:hidden}
img{display:block;width:${storona}px;height:${storona}px;${krug ? 'border-radius:50%' : ''}}</style>
<img src="${imyaSvg}">`);
  execFileSync(CHROME, ['--disable-gpu', '--no-sandbox', '--hide-scrollbars',
    '--force-device-scale-factor=1', `--window-size=${storona},${storona}`,
    `--screenshot=${join(TUT, vyhod)}`, `file://${html}`], { stdio: 'ignore' });
  unlinkSync(html);
  console.log(`  ${vyhod} — ${storona}×${storona}`);
}

/* Запущен напрямую — собираем. Импортирован (сравнение вариантов) —
   отдаём только функции, чтобы не перезаписать готовые файлы. */
if (process.argv[1] === fileURLToPath(import.meta.url)) {
/* ТРИ ФАЙЛА, И У КАЖДОГО СВОЁ МЕСТО. Разница не в красоте, а в том,
   что человек видит рядом со знаком.

   Карточка 2ГИС и Яндекса: ссылка на сайт там уже стоит кнопкой,
   писать адрес внутри знака — тратить место дважды. Зато слоган
   говорит, что мы делаем и где.

   Печатная продукция: рядом нет ни кнопки, ни карточки. Адрес внутри
   знака — единственный способ довести человека до сайта, поэтому
   он занимает место слогана. */
const SBORKI = [
  { imya: 'granat-logo-2gis-s-venzelem', proba: 'proba-s-venzelem',
    opts: { sVenzelem: true, slogan: SLOGAN, keglSlogana: KEGL_SLOGANA },
    zachem: 'ОСНОВНОЙ — карточки 2ГИС, Яндекс Бизнес, аватарка ВК' },

  { imya: 'granat-logo-polnyj', proba: 'proba-polnyj',
    opts: { sVenzelem: true, slogan: SLOGAN, keglSlogana: 50, sajt: 'GRANAT-KMV.RU' },
    zachem: 'ПОЛНЫЙ — слоган И адрес. Выбор владелицы 17.08.2026' },

  { imya: 'granat-logo-dlya-pechati', proba: 'proba-dlya-pechati',
    opts: { sVenzelem: true, slogan: 'GRANAT-KMV.RU', keglSlogana: 66 },
    zachem: 'ПЕЧАТЬ — только адрес, без слогана' },

  { imya: 'granat-logo-2gis', proba: 'proba-bez-venzelya',
    opts: { sVenzelem: false, slogan: SLOGAN, keglSlogana: KEGL_SLOGANA },
    zachem: 'МЕЛКИЙ РАЗМЕР — значок вкладки, аватарка в переписке' },
];

for (const { imya, proba, opts, zachem } of SBORKI) {
  const imyaSvg = `${imya}.svg`;
  writeFileSync(join(TUT, imyaSvg), svg(opts));
  console.log(`${zachem}\n  ${imyaSvg}`);
  risovat(imyaSvg, 1500, `${imya}-1500.png`, false);
  risovat(imyaSvg, 200, `${proba}-200.png`, true);
}
}
