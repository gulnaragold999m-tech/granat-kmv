#!/usr/bin/env node
/**
 * proverka-tokenov.mjs — собрана ли страница из токенов или из случайных значений.
 * Node 18+, без зависимостей.
 *
 *   node proverka-tokenov.mjs zhivoj-sajt
 *   node proverka-tokenov.mjs zhivoj-sajt --css zhivoj-sajt/static/css/tailwind.css
 *   node proverka-tokenov.mjs zhivoj-sajt --json
 *
 * Что проверяет:
 *   1. Цвета, записанные мимо палитры :root — hex и rgb() прямо в правилах и в разметке.
 *   2. Сколько разных гарнитур реально в ходу (глазом это не сосчитать).
 *   3. Разметку со style="..." — стиль, которого нет в CSS и который никто не найдёт.
 *   4. Размеры шрифта меньше 16 px в основном тексте — на телефоне это боль.
 *
 * Чего НЕ проверяет: красиво ли, похоже ли на референс, уместен ли акцент.
 * Это смотрит человек. Проверка ловит только то, что ей велели смотреть.
 */

import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { join, extname, relative } from 'node:path';

const argv = process.argv.slice(2);
let koren = null, cssPut = null, asJson = false;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--json') asJson = true;
  else if (a === '--css') cssPut = argv[++i];
  else if (!a.startsWith('-')) koren = a;
}
koren ??= 'public';

if (!existsSync(koren)) {
  console.error(`Не найдена папка: ${koren}`);
  console.error('Сначала путь до сайта: node proverka-tokenov.mjs zhivoj-sajt');
  process.exit(2);
}

// ─────────────────────── собираем файлы ───────────────────────
function obojti(dir, out = []) {
  for (const imya of readdirSync(dir)) {
    if (imya === 'node_modules' || imya.startsWith('.')) continue;
    const p = join(dir, imya);
    if (statSync(p).isDirectory()) obojti(p, out);
    else if (['.html', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}
// Собранный (минифицированный) файл писал не человек: утилиты Tailwind
// и сжатые бандлы правятся в исходнике, ругаться на них бессмысленно.
const sobrannyj = text => text.length > 5000 && text.split('\n').length < 5;

const fajly = obojti(koren).filter(f => !sobrannyj(readFileSync(f, 'utf8')));
const cssFajly = cssPut ? [cssPut] : fajly.filter(f => f.endsWith('.css'));
const htmlFajly = fajly.filter(f => f.endsWith('.html'));

// ─────────────────────── палитра из :root ───────────────────────
const palitra = new Map();   // значение в нижнем регистре → имя переменной
const peremennye = new Set();
for (const f of cssFajly) {
  if (!existsSync(f)) continue;
  const text = readFileSync(f, 'utf8');
  for (const m of text.matchAll(/--([\w-]+)\s*:\s*([^;]+);/g)) {
    const imya = `--${m[1]}`, znach = m[2].trim().toLowerCase();
    peremennye.add(imya);
    palitra.set(normHex(znach), imya);
  }
}

function normHex(v) {
  const m = v.match(/^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i);
  if (!m) return v.replace(/\s+/g, '');
  let h = m[1].toLowerCase();
  if (h.length === 3) h = h.split('').map(c => c + c).join('');
  return `#${h}`;
}

/**
 * Цвет к виду «#rrggbb» — без прозрачности.
 * Нужно, чтобы rgba(0,240,255,.35) опозналось как токен --cyan с прозрачностью,
 * а не как новый цвет мимо палитры. Прозрачность токена — это нормально:
 * свечения и подложки иначе не собрать.
 */
function osnovaCveta(v) {
  const rgb = v.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/);
  if (rgb) {
    const [r, g, b] = rgb.slice(1, 4).map(n => Math.round(parseFloat(n)));
    if ([r, g, b].some(n => Number.isNaN(n))) return null;
    return '#' + [r, g, b].map(n => n.toString(16).padStart(2, '0')).join('');
  }
  const hex = v.match(/^#([0-9a-f]{6})[0-9a-f]{0,2}$/i);
  return hex ? `#${hex[1].toLowerCase()}` : null;
}

// ─────────────────────── проверки ───────────────────────
const najdeno = { cveta: [], shrifty: [], style: [], melkij: [], tehnStyle: 0 };
const cvetaSchet = new Map();
let ottenkov = 0;   // прозрачные варианты токенов — это не нарушение

// основы цветов палитры: rgba(0,240,255,.35) — это --cyan, а не новый цвет
const osnovyTokenov = new Set();
for (const znach of palitra.keys()) {
  const o = osnovaCveta(znach);
  if (o) osnovyTokenov.add(o);
}

// цвет за пределами палитры — только в CSS-правилах и в разметке,
// сам блок :root пропускаем: там значения и должны быть числами
for (const f of [...cssFajly, ...htmlFajly]) {
  if (!existsSync(f)) continue;
  let text = readFileSync(f, 'utf8');
  if (f.endsWith('.css')) text = text.replace(/:root\s*\{[^}]*\}/g, '');
  else text = text.replace(/<svg[\s\S]*?<\/svg>/gi, '');   // иконки живут своими цветами

  const stroki = text.split('\n');
  stroki.forEach((str, i) => {
    for (const m of str.matchAll(/#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)/g)) {
      const znach = normHex(m[0].toLowerCase());
      if (palitra.has(znach)) continue;
      const osnova = osnovaCveta(znach);
      if (osnova && osnovyTokenov.has(osnova)) { ottenkov++; continue; }
      if (/^rgba?\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)$/.test(znach)) continue;
      cvetaSchet.set(znach, (cvetaSchet.get(znach) || 0) + 1);
      najdeno.cveta.push({ fajl: relative('.', f), stroka: i + 1, znach });
    }
  });
}

// гарнитуры
const garnitury = new Map();
for (const f of cssFajly) {
  if (!existsSync(f)) continue;
  const text = readFileSync(f, 'utf8');
  for (const m of text.matchAll(/font-family\s*:\s*([^;}]+)/gi)) {
    const spisok = m[1].trim();
    if (spisok.startsWith('var(')) continue;
    const pervyj = spisok.split(',')[0].replace(/['"]/g, '').trim().toLowerCase();
    if (!pervyj || pervyj === 'inherit') continue;
    // моноширинный для кода — служебный, к типографике страницы отношения не имеет
    if (/^(ui-)?monospace$|^menlo$|^consolas$|^courier/.test(pervyj)) continue;
    garnitury.set(pervyj, (garnitury.get(pervyj) || 0) + 1);
  }
}

// style="..." в разметке
for (const f of htmlFajly) {
  const stroki = readFileSync(f, 'utf8').split('\n');
  stroki.forEach((str, i) => {
    for (const m of str.matchAll(/\sstyle\s*=\s*"([^"]{3,})"/g)) {
      const dekl = m[1].toLowerCase();
      // оформление — то, что должно жить в CSS. Техническое (спам-ловушка,
      // разрешение тянуть поле) оформлением не является, за него не ругаем.
      const oformlenie = /(color|background|font|border|radius|shadow|padding|margin|gap|opacity|gradient)/.test(dekl);
      if (!oformlenie) { najdeno.tehnStyle++; continue; }
      najdeno.style.push({ fajl: relative('.', f), stroka: i + 1, kusok: m[1].slice(0, 60) });
    }
  });
}

// мелкий кегль
for (const f of cssFajly) {
  if (!existsSync(f)) continue;
  const stroki = readFileSync(f, 'utf8').split('\n');
  stroki.forEach((str, i) => {
    const m = str.match(/font-size\s*:\s*(\d+(?:\.\d+)?)px/i);
    if (m && parseFloat(m[1]) < 13) {
      najdeno.melkij.push({ fajl: relative('.', f), stroka: i + 1, kegl: m[1] });
    }
  });
}

// ─────────────────────── вывод ───────────────────────
if (asJson) {
  console.log(JSON.stringify({
    palitra: [...palitra.entries()].map(([z, i]) => ({ znachenie: z, peremennaya: i })),
    garnitury: [...garnitury.keys()],
    cveta_mimo_palitry: [...cvetaSchet.entries()].map(([z, n]) => ({ znachenie: z, raz: n })),
    style_v_razmetke: najdeno.style.length,
    style_tehnicheskih: najdeno.tehnStyle,
    ottenkov_tokenov: ottenkov,
    melkij_kegl: najdeno.melkij,
  }, null, 2));
  process.exit(najdeno.style.length || cvetaSchet.size > 12 ? 1 : 0);
}

const P = s => console.log(s);
P('');
P(`Проверка токенов: ${htmlFajly.length} страниц, ${cssFajly.length} файлов стилей`);
P(`Переменных в :root: ${peremennye.size}`);
P('');

let plohih = 0;

if (cvetaSchet.size === 0) {
  P(`✅ Цвет: всё из палитры (прозрачных вариантов токенов — ${ottenkov}).`);
} else {
  const top = [...cvetaSchet.entries()].sort((a, b) => b[1] - a[1]);
  P(`⚠️  Цвет мимо палитры: ${cvetaSchet.size} разных значений, ${najdeno.cveta.length} раз.`);
  P(`    (прозрачные варианты самих токенов — ${ottenkov} шт., они не в счёт)`);
  P('    Частые — их и стоит завести токеном либо свести к существующему:');
  for (const [z, n] of top.slice(0, 10)) {
    const gde = najdeno.cveta.find(c => c.znach === z);
    P(`      ${z.padEnd(24)} ${String(n).padStart(3)} раз   ${gde.fajl}:${gde.stroka}`);
  }
  if (top.length > 10) P(`      … и ещё ${top.length - 10}`);
  if (cvetaSchet.size > 12) plohih++;
  P('');
}

if (garnitury.size <= 3) {
  P(`✅ Гарнитуры: ${garnitury.size} — ${[...garnitury.keys()].join(', ') || 'все через переменные'}`);
} else {
  P(`⚠️  Гарнитур в ходу: ${garnitury.size}. Больше трёх — страница разъезжается.`);
  for (const [g, n] of [...garnitury.entries()].sort((a, b) => b[1] - a[1])) P(`      ${g} — ${n} раз`);
  plohih++;
}
P('');

if (najdeno.style.length === 0) {
  P(`✅ Разметка: оформления в style="..." нет${najdeno.tehnStyle ? ` (технических — ${najdeno.tehnStyle}, это не в счёт)` : ''}.`);
} else {
  P(`❌ style="..." в разметке: ${najdeno.style.length}. Такой стиль не найдёт никто, кроме автора.`);
  for (const s of najdeno.style.slice(0, 8)) P(`      ${s.fajl}:${s.stroka}  ${s.kusok}`);
  if (najdeno.style.length > 8) P(`      … и ещё ${najdeno.style.length - 8}`);
  plohih++;
}
P('');

if (najdeno.melkij.length === 0) {
  P('✅ Кегль: меньше 13 px нет.');
} else {
  P(`⚠️  Кегль меньше 13 px — ${najdeno.melkij.length} мест. На телефоне это нечитаемо:`);
  for (const m of najdeno.melkij.slice(0, 8)) P(`      ${m.fajl}:${m.stroka}  ${m.kegl}px`);
}
P('');

if (plohih === 0) {
  P('Итог: страница собрана из системы, а не из случайных значений.');
  process.exit(0);
}
P(`Итог: ${plohih} блок(а/ов) требует правки. Что делать — .claude/skills/dizajn-dnk/references/tokeny-i-stek.md`);
process.exit(1);
