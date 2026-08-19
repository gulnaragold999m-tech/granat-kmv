#!/usr/bin/env node
/* Подбирает кегль для варианта «по линейкам»: строки не переносятся,
   значит каждая обязана уложиться в ширину поля. Скрипт уменьшает кегль,
   пока самая длинная строка не влезет, и собирает PDF. */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const koren = dirname(fileURLToPath(import.meta.url));
const fajl = join(koren, 'adres-po-linejkam.html');
const brauzer = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' }).catch(() => chromium.launch());
const s = await brauzer.newPage({ viewport: { width: 794, height: 1123 } });
await s.goto('file://' + fajl, { waitUntil: 'load' });
await s.waitForTimeout(700);

const podoshlo = await s.evaluate(() => {
  const koren = document.documentElement;
  const stroki = [...document.querySelectorAll('.stroki p')];
  const shirina = document.querySelector('.stroki').clientWidth;
  for (let kegl = 4.0; kegl >= 2.6; kegl -= 0.05) {
    koren.style.setProperty('--kegl', kegl.toFixed(2) + 'mm');
    const vlezli = stroki.every(el => {
      const r = document.createRange(); r.selectNodeContents(el);
      return r.getBoundingClientRect().width <= shirina;
    });
    if (vlezli) return kegl.toFixed(2);
  }
  return null;
});

if (!podoshlo) { console.error('Строки не влезают. Разбейте текст иначе.'); await brauzer.close(); process.exit(1); }
writeFileSync(fajl, readFileSync(fajl, 'utf8').replace(/--kegl: [\d.]+mm;/, `--kegl: ${podoshlo}mm;`));
await s.goto('file://' + fajl);
await s.waitForTimeout(500);
await s.pdf({ path: join(koren, 'adres-po-linejkam.pdf'), format: 'A4', printBackground: false,
              margin: { top: 0, right: 0, bottom: 0, left: 0 } });
await s.screenshot({ path: join(koren, 'adres-po-linejkam-predprosmotr.png') });
await brauzer.close();
console.log(`Кегль ${podoshlo} мм (≈ ${(podoshlo * 2.835).toFixed(1)} пт). Готово.`);
