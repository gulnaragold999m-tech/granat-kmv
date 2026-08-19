#!/usr/bin/env node
/* Подбирает кегль для торжественного макета и собирает PDF с фоном.
   Ждём document.fonts.ready: без этого каллиграфия не успевает
   загрузиться, и в PDF уходит запасная антиква — на первом оттиске
   это уже случилось. */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const koren = dirname(fileURLToPath(import.meta.url));
const fajl = join(koren, 'adres-edinyj.html');
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
const s = await b.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 2 });
await s.goto('file://' + fajl, { waitUntil: 'load' });
await s.evaluate(() => document.fonts.ready);
await s.waitForTimeout(400);

const shrifty = await s.evaluate(() => ({
  obrashchenie: getComputedStyle(document.querySelector('.obrashchenie')).fontFamily,
  zagruzheny: [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family),
}));

const podoshlo = await s.evaluate(() => {
  const koren = document.documentElement, pol = document.querySelector('.polosa');
  for (let kegl = 4.8; kegl >= 3.2; kegl -= 0.1) {
    koren.style.setProperty('--kegl', kegl.toFixed(1) + 'mm');
    koren.style.setProperty('--shag', (kegl * 1.62).toFixed(2) + 'mm');
    if (pol.scrollHeight <= pol.clientHeight + 1) return kegl.toFixed(1);
  }
  return null;
});
if (!podoshlo) { console.error('Текст не помещается.'); await b.close(); process.exit(1); }

writeFileSync(fajl, readFileSync(fajl, 'utf8')
  .replace(/--kegl:[\d. ]+mm;/, `--kegl:${podoshlo}mm;`)
  .replace(/--shag:[\d. ]+mm;/, `--shag:${(podoshlo * 1.62).toFixed(2)}mm;`));

await s.goto('file://' + fajl);
await s.evaluate(() => document.fonts.ready);
await s.waitForTimeout(400);
await s.pdf({ path: join(koren, 'adres-edinyj.pdf'), format: 'A4', printBackground: true,
              margin: { top: 0, right: 0, bottom: 0, left: 0 } });
await s.screenshot({ path: join(koren, 'adres-edinyj-predprosmotr.png') });
await b.close();
console.log('Кегль', podoshlo, 'мм. Шрифт обращения:', shrifty.obrashchenie);
console.log('Загруженные гарнитуры:', [...new Set(shrifty.zagruzheny)].join(', ') || '— ни одной');
