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
const VENZEL = readFileSync(join(TUT, 'venzel-g.png')).toString('base64');

/* Разрядка на сайте задана как .18em, а в SVG letter-spacing считается
   в точках. Поэтому переводим: 0.18 × размер шрифта. */
const razryadka = (kegl, em) => Math.round(kegl * em);

function svg({ sVenzelem }) {
  /* С вензелем название меньше: втроём — дуга, вензель и слово — они
     не помещаются, если каждому дать полный размер.
     17.08.2026 поднято со 168 до 196: владелица выбрала вариант
     с вензелем основным, а в кружке 2ГИС из трёх ярусов читается только
     название. Больше 196 слово упирается в кольцо. */
  const kegl = sVenzelem ? 196 : 232;

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
  </defs>

  <rect width="1500" height="1500" fill="url(#fon)"/>
  <circle cx="750" cy="750" r="688" fill="none" stroke="url(#zoloto)" stroke-width="26"/>
  <circle cx="750" cy="750" r="645" fill="none" stroke="url(#zolotoTonkoe)" stroke-width="6"/>

  <text font-family="Montserrat" font-size="70" font-weight="600"
        letter-spacing="${razryadka(70, 0.22)}" fill="url(#zolotoTonkoe)">
    <textPath href="#dugaVerh" startOffset="50%" text-anchor="middle">ДИЗАЙНЕРСКАЯ СТУДИЯ</textPath>
  </text>
${sVenzelem ? `
  <image x="548" y="372" width="404" height="540" href="data:image/png;base64,${VENZEL}"/>
` : ''}
  <text x="750" y="${sVenzelem ? 1120 : 872}" text-anchor="middle"
        font-family="Playfair Display" font-size="${kegl}" font-weight="700"
        letter-spacing="${razryadka(kegl, 0.18)}" fill="url(#zoloto)">ГРАНАТ</text>
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

function risovat(imyaSvg, storona, vyhod, krug) {
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

for (const sVenzelem of [false, true]) {
  const hvost = sVenzelem ? '-s-venzelem' : '';
  const imyaSvg = `granat-logo-2gis${hvost}.svg`;
  writeFileSync(join(TUT, imyaSvg), svg({ sVenzelem }));
  console.log(sVenzelem ? 'С вензелем:' : 'Без вензеля:');
  console.log(`  ${imyaSvg}`);
  risovat(imyaSvg, 1500, `granat-logo-2gis${hvost}-1500.png`, false);
  risovat(imyaSvg, 200, `proba${hvost || '-bez-venzelya'}-200.png`, true);
}
