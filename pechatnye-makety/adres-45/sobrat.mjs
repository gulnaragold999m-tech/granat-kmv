#!/usr/bin/env node
/* Подбирает кегль так, чтобы текст улёгся в полосу бланка, и собирает PDF.
   Зачем скриптом: «на глаз» кегль подбирают до первой правки текста, потом
   строка вылезает на золото и этого никто не замечает до печати.
       node sobrat.mjs
   Требуется playwright (ставится разово: npm install --no-save playwright). */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const koren = dirname(fileURLToPath(import.meta.url));
const fajl = join(koren, 'adres-polnyj.html');

const brauzer = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })
  .catch(() => chromium.launch());
const stranica = await brauzer.newPage({ viewport: { width: 794, height: 1123 } });

await stranica.goto('file://' + fajl, { waitUntil: 'load' });
await stranica.waitForTimeout(700);          // даём шрифту догрузиться один раз

// Кегль меняем прямо на странице и сразу меряем: так подбор занимает секунды,
// а не минуты на перезагрузках.
const podoshlo = await stranica.evaluate(() => {
  const koren = document.documentElement;
  const polosa = document.querySelector('.polosa');
  const vlezlo = () => {
    const shire = [...polosa.querySelectorAll('p')].some(el => {
      const r = document.createRange(); r.selectNodeContents(el);
      return r.getBoundingClientRect().width > el.clientWidth + 1;
    });
    return polosa.scrollHeight <= polosa.clientHeight + 1 && !shire;
  };
  for (let kegl = 4.4; kegl >= 2.8; kegl -= 0.1) {
    const shag = +(kegl * 1.6).toFixed(2);
    koren.style.setProperty('--kegl', kegl.toFixed(1) + 'mm');
    koren.style.setProperty('--shag', shag + 'mm');
    if (vlezlo()) return { kegl: kegl.toFixed(1), shag };
  }
  return null;
});

if (!podoshlo) {
  console.error('Текст не помещается даже мелким кеглем. Сократите текст или расширьте полосу.');
  await brauzer.close();
  process.exit(1);
}

const itog = readFileSync(fajl, 'utf8')
  .replace(/--kegl: [\d.]+mm;/, `--kegl: ${podoshlo.kegl}mm;`)
  .replace(/--shag: [\d.]+mm;/, `--shag: ${podoshlo.shag}mm;`);
writeFileSync(fajl, itog);

await stranica.goto('file://' + fajl);
await stranica.waitForTimeout(500);
await stranica.pdf({ path: join(koren, 'adres-polnyj.pdf'), format: 'A4',
  printBackground: false, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
await stranica.screenshot({ path: join(koren, 'adres-predprosmotr.png') });

/* Ещё один файл — текст на прозрачном фоне, 300 точек на дюйм. Он нужен,
   чтобы положить текст поверх картинки бланка в любом редакторе: слой
   ляжет ровно, а белый прямоугольник золото не закроет.
   Плотность важна: экранные 96 точек на бумаге дают рваные буквы. */
const dlyaPechati = await brauzer.newPage({
  viewport: { width: 794, height: 1123 }, deviceScaleFactor: 3.2,
});
await dlyaPechati.goto('file://' + fajl);
await dlyaPechati.waitForTimeout(600);
await dlyaPechati.evaluate(() => {
  document.body.style.background = 'transparent';
  document.querySelector('.list').style.background = 'transparent';
  document.querySelector('.granicy').style.display = 'none';
});
await dlyaPechati.screenshot({ path: join(koren, 'adres-tekst-prozrachnyj.png'), omitBackground: true });
await brauzer.close();

console.log(`Кегль ${podoshlo.kegl} мм (≈ ${(podoshlo.kegl * 2.835).toFixed(1)} пт), шаг строк ${podoshlo.shag} мм.`);
console.log('Готово: adres-polnyj.pdf и adres-predprosmotr.png');
