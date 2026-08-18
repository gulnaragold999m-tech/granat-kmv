#!/usr/bin/env node
/**
 * proverka-dvizheniya.mjs — не сломает ли анимация страницу на слабом телефоне.
 * Node 18+, без зависимостей.
 *
 *   node proverka-dvizheniya.mjs zhivoj-sajt
 *   node proverka-dvizheniya.mjs zhivoj-sajt --json
 *
 * Что проверяет:
 *   1. Анимацию свойств, которые считает не видеокарта, а браузер (left, width, box-shadow…).
 *   2. Длительности дольше 800 мс — это уже не анимация, а задержка.
 *   3. Файлы, где есть @keyframes или transition, но нет глушения prefers-reduced-motion.
 *   4. Бесконечные анимации — их должно быть наперечёт.
 *   5. will-change, который никто не снимает.
 *
 * Чего НЕ проверяет: тормозит ли на самом деле, уместно ли движение и красиво ли оно.
 * Это смотрится на живом телефоне. Проверка ловит только то, что ей велели смотреть.
 */

import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';

const argv = process.argv.slice(2);
let koren = null, asJson = false;
for (const a of argv) { if (a === '--json') asJson = true; else if (!a.startsWith('-')) koren = a; }
koren ??= 'public';

if (!existsSync(koren)) {
  console.error(`Не найдена папка: ${koren}`);
  console.error('Сначала путь до сайта: node proverka-dvizheniya.mjs zhivoj-sajt');
  process.exit(2);
}

function obojti(dir, out = []) {
  for (const imya of readdirSync(dir)) {
    if (imya === 'node_modules' || imya.startsWith('.')) continue;
    const p = join(dir, imya);
    if (statSync(p).isDirectory()) obojti(p, out);
    else if (['.html', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}

/**
 * Собранный (минифицированный) файл — это не то, что писал человек:
 * ругаться на утилиты Tailwind или на сжатый бандл бессмысленно,
 * правится всё равно исходник. Признак: файл большой, а строк почти нет.
 */
function sobrannyj(put, text) {
  return text.length > 5000 && text.split('\n').length < 5;
}

// Свойства, ради которых браузер пересчитывает разметку на каждом кадре.
// Всё это делается через transform/opacity — как именно, написано в SKILL.md.
const TYAZHELYE = {
  left: 'transform: translateX()', top: 'transform: translateY()',
  right: 'transform: translateX()', bottom: 'transform: translateY()',
  width: 'transform: scaleX()', height: 'transform: scaleY()',
  margin: 'обёртка + translate', 'margin-top': 'обёртка + translate',
  'margin-left': 'обёртка + translate', padding: 'обёртка + translate',
  'box-shadow': 'псевдоэлемент с тенью + opacity',
  filter: 'по возможности opacity', 'background-position': 'transform у слоя внутри',
  'background-color': 'допустимо для мелких элементов, но не для крупных площадей',
};

const itog = { tyazhelye: [], dolgie: [], bezGlusheniya: [], skriptBezProverki: [], beskonechnye: [], willChange: [] };
let obshcheeGlushenie = false;   // блок prefers-reduced-motion со звёздочкой — накрывает весь CSS
const fajly = obojti(koren);

// сначала ищем общий блок глушения: @media (prefers-reduced-motion: reduce) { *, … }
for (const f of fajly) {
  const text = readFileSync(f, 'utf8');
  for (const m of text.matchAll(/prefers-reduced-motion[^{]*\{\s*([^{]*)\{/g)) {
    if (/\*/.test(m[1])) obshcheeGlushenie = true;
  }
}

let propushcheno = 0;

for (const f of fajly) {
  const text = readFileSync(f, 'utf8');
  const otn = relative('.', f);
  if (sobrannyj(f, text)) { propushcheno++; continue; }
  const stroki = text.split('\n');

  // CSS-анимации в файле: общий блок глушения со звёздочкой (если он есть
  // в проекте) накрывает их все разом, поэтому по файлам ругаемся, только
  // когда общего блока нет.
  if (/@keyframes/.test(text) && !/prefers-reduced-motion/.test(text)) itog.bezGlusheniya.push(otn);

  // Скриптовая анимация мимо CSS: её общий блок не достаёт, нужна проверка
  // matchMedia прямо в коде.
  const skript = /gsap\.|\.animate\(|requestAnimationFrame/.test(text);
  if (skript && !/prefers-reduced-motion/.test(text)) itog.skriptBezProverki.push(otn);

  stroki.forEach((str, i) => {
    const nomer = i + 1;

    // transition: <свойство> …
    const tr = str.match(/transition(?:-property)?\s*:\s*([^;}"']+)/i);
    if (tr) {
      for (const kusok of tr[1].split(',')) {
        const svojstvo = kusok.trim().split(/\s+/)[0].toLowerCase();
        if (TYAZHELYE[svojstvo]) {
          itog.tyazhelye.push({ fajl: otn, stroka: nomer, svojstvo, vmesto: TYAZHELYE[svojstvo] });
        }
      }
    }

    // свойство внутри @keyframes ловим грубо: строка вида "left: 40px;" внутри блока кадров
    // (точный разбор CSS тут не нужен — важно заметить и посмотреть глазами)

    for (const m of str.matchAll(/(?<![\d.])(\d+(?:\.\d+)?)\s*s\b/g)) {
      const ms = parseFloat(m[1]) * 1000;
      if (/animation-delay|transition-delay/i.test(str)) continue;   // задержка — не длительность
      // бесконечные фоновые анимации живут своей жизнью: у них длительность
      // и должна быть большой, иначе получится мельтешение. Их смотрим отдельно.
      if (/transition|animation/i.test(str) && !/\binfinite\b/i.test(str) && ms > 800 && ms < 60000) {
        itog.dolgie.push({ fajl: otn, stroka: nomer, ms, kusok: str.trim().slice(0, 70) });
      }
    }

    if (/animation[^;}]*\binfinite\b/i.test(str)) {
      itog.beskonechnye.push({ fajl: otn, stroka: nomer, kusok: str.trim().slice(0, 70) });
    }
    if (/will-change\s*:/i.test(str)) {
      itog.willChange.push({ fajl: otn, stroka: nomer, kusok: str.trim().slice(0, 70) });
    }
  });
}

// внутри @keyframes — отдельным проходом, по блокам
for (const f of fajly) {
  const text = readFileSync(f, 'utf8');
  const otn = relative('.', f);
  if (sobrannyj(f, text)) continue;
  for (const blok of text.matchAll(/@keyframes\s+([\w-]+)\s*\{([\s\S]*?)\n\s*\}/g)) {
    const [, imya, telo] = blok;
    for (const m of telo.matchAll(/^\s*([a-z-]+)\s*:/gim)) {
      const svojstvo = m[1].toLowerCase();
      if (TYAZHELYE[svojstvo]) {
        itog.tyazhelye.push({ fajl: otn, stroka: `@keyframes ${imya}`, svojstvo, vmesto: TYAZHELYE[svojstvo] });
      }
    }
  }
}

if (asJson) {
  console.log(JSON.stringify(itog, null, 2));
  process.exit(itog.tyazhelye.length || itog.bezGlusheniya.length ? 1 : 0);
}

const P = s => console.log(s);
const spisok = (arr, n = 8, f = x => `      ${x.fajl}:${x.stroka}  ${x.kusok ?? ''}`) => {
  arr.slice(0, n).forEach(x => P(f(x)));
  if (arr.length > n) P(`      … и ещё ${arr.length - n}`);
};

P('');
P(`Проверка движения: ${fajly.length} файлов в ${koren}` +
  (propushcheno ? `, из них ${propushcheno} собранных — пропущены, правится исходник` : ''));
P('');
let plohih = 0;

if (itog.tyazhelye.length === 0) {
  P('✅ Анимируются только лёгкие свойства.');
} else {
  P(`❌ Анимация тяжёлых свойств — ${itog.tyazhelye.length}. На телефоне это рывки:`);
  spisok(itog.tyazhelye, 10, x => `      ${x.fajl}:${x.stroka}  ${x.svojstvo}  →  ${x.vmesto}`);
  plohih++;
}
P('');

if (obshcheeGlushenie) P('✅ Общий блок prefers-reduced-motion найден — он накрывает CSS-анимации.');
if (!obshcheeGlushenie && itog.bezGlusheniya.length > 0) {
  P(`❌ @keyframes без глушения prefers-reduced-motion — ${itog.bezGlusheniya.length} файл(ов):`);
  itog.bezGlusheniya.slice(0, 10).forEach(f => P(`      ${f}`));
  if (itog.bezGlusheniya.length > 10) P(`      … и ещё ${itog.bezGlusheniya.length - 10}`);
  P('      Готовый блок — в SKILL.md, раздел про prefers-reduced-motion.');
  plohih++;
} else if (!obshcheeGlushenie) {
  P('✅ Везде, где есть @keyframes, есть и prefers-reduced-motion.');
}

if (itog.skriptBezProverki.length === 0) {
  P('✅ Скриптовые анимации проверяют настройку движения.');
} else {
  P(`❌ Анимация из JS без проверки matchMedia — ${itog.skriptBezProverki.length} файл(ов).`);
  P('   CSS-глушение до неё не достаёт, человек с включённым «уменьшить движение» её увидит:');
  itog.skriptBezProverki.slice(0, 10).forEach(f => P(`      ${f}`));
  if (itog.skriptBezProverki.length > 10) P(`      … и ещё ${itog.skriptBezProverki.length - 10}`);
  plohih++;
}
P('');

if (itog.dolgie.length === 0) P('✅ Длительностей дольше 800 мс нет.');
else {
  P(`⚠️  Дольше 800 мс — ${itog.dolgie.length}. Проверьте, это замысел или забытая единица:`);
  spisok(itog.dolgie, 6, x => `      ${x.fajl}:${x.stroka}  ${x.ms} мс  ${x.kusok}`);
}
P('');

P(itog.beskonechnye.length <= 5
  ? `✅ Бесконечных анимаций: ${itog.beskonechnye.length}.`
  : `⚠️  Бесконечных анимаций: ${itog.beskonechnye.length}. Рядом с текстом их быть не должно:`);
if (itog.beskonechnye.length > 5) spisok(itog.beskonechnye, 6);
P('');

if (itog.willChange.length > 6) {
  P(`⚠️  will-change — ${itog.willChange.length} мест. Постоянный will-change ест память, ставится точечно:`);
  spisok(itog.willChange, 6);
  P('');
}

if (plohih === 0) {
  P('Итог: движение можно выкатывать. Осталось посмотреть на живом телефоне.');
  process.exit(0);
}
P(`Итог: ${plohih} блок(а/ов) требует правки. Что делать — .claude/skills/animacii-veb/SKILL.md`);
process.exit(1);
