/* Проверка секретаря на сайте: прогон по всем сценариям разом.
 *
 * ЗАЧЕМ. Владелица 19.08.2026: «я откуда знаю, что ещё может вылезти».
 * И правда — не должна знать. До сих пор каждая дыра в секретаре
 * находилась одинаково: приходил живой клиент, упирался в неё и уходил.
 * Так были найдены двойной вопрос про макет, тупик в «Другой задаче»,
 * поле с непонятным названием и разговор про заливку там, где заливки
 * нет вовсе.
 *
 * Эта проверка ищет то же самое, но за секунду и до клиента.
 *
 * Запуск: npm run sekretar-proverka
 *
 * ЧЕГО ОНА НЕ ДЕЛАЕТ. Она не открывает браузер и не жмёт кнопки —
 * значит не поймает ошибку вёрстки или неверную цену. Она смотрит
 * устройство разговора: какие вопросы задаются, в каком порядке,
 * не спрашивается ли одно и то же дважды, попадёт ли ответ в заявку
 * понятным словом.
 */

import { readFileSync } from 'node:fs';

const FAJL = 'zhivoj-sajt/templates/partials/_js-sekretar.html';
const ishodnik = readFileSync(FAJL, 'utf8');

let bed = 0;
const beda = (s) => { bed++; console.log('  ✗ ' + s); };
const norma = (s) => console.log('  · ' + s);

/* ── Сценарии и их шаги ─────────────────────────────────────────────
   Разбираем текстом, а не запуском: скрипт секретаря живёт в браузере
   и без окна не поднимется. Нам и не нужно — вопросы видно в исходнике. */
function scenarii() {
  const nachalo = ishodnik.indexOf('var SCENARII = {');
  const konec = ishodnik.indexOf('\n    var vybor = {}', nachalo);
  const kusok = ishodnik.slice(nachalo, konec);

  const iz = [];
  const re = /^      ([a-z_]+): \{$/gm;
  let m;
  const granicy = [];
  while ((m = re.exec(kusok)) !== null) granicy.push({ kod: m[1], ot: m.index });
  granicy.forEach((g, i) => {
    const telo = kusok.slice(g.ot, i + 1 < granicy.length ? granicy[i + 1].ot : kusok.length);
    const imya = (telo.match(/imya: '([^']+)'/) || [])[1] || g.kod;
    const shagi = [...telo.matchAll(/\{ id: '([a-z_]+)'/g)].map((x) => x[1]);
    iz.push({ kod: g.kod, imya, shagi, telo });
  });
  return iz;
}

console.log('СЕКРЕТАРЬ НА САЙТЕ — проверка сценариев\n');

const spisok = scenarii();
if (!spisok.length) {
  beda('сценарии не найдены — изменилась разметка файла, проверку надо чинить');
}

for (const s of spisok) {
  console.log(`${s.imya}  (${s.kod})`);
  console.log('  вопросы: ' + (s.shagi.length ? s.shagi.join(' → ') : '— нет вопросов —'));

  /* 1. Один и тот же вопрос дважды. Ровно так 18.08.2026 клиента
        спрашивали про макет два раза, и цену считал ВТОРОЙ ответ,
        затирая первый. */
  const povtory = s.shagi.filter((x, i) => s.shagi.indexOf(x) !== i);
  if (povtory.length) beda(`вопрос задаётся дважды: ${[...new Set(povtory)].join(', ')}`);

  /* 2. Срок. Без него заказ не поставить в очередь, а клиент
        не скажет «мне срочно». */
  if (s.kod !== 'drugoe' && !s.shagi.includes('srok')) {
    beda('не спрашивается срок');
  }

  /* 3. Считать цену нечем. «Другая задача» — единственное законное
        исключение: там человек пишет словами. */
  if (!/schet: function/.test(s.telo)) beda('нет расчёта цены');
  if (!s.shagi.length && s.kod !== 'drugoe') beda('нет ни одного вопроса');
}

/* ── Подписи шагов ─────────────────────────────────────────────────── */
console.log('\nПодписи шагов для заявки');
const podpisiKusok = ishodnik.slice(ishodnik.indexOf('var PODPISI = {'));
const podpisi = [...podpisiKusok.slice(0, podpisiKusok.indexOf('};'))
  .matchAll(/^      ([a-z_]+): '([^']+)'/gm)].map((m) => m[1]);

const dubli = podpisi.filter((x, i) => podpisi.indexOf(x) !== i);
if (dubli.length) {
  beda(`подпись задана дважды: ${[...new Set(dubli)].join(', ')} — ` +
       'в JavaScript побеждает последняя, и первая молча пропадает');
} else {
  norma(`подписей ${podpisi.length}, повторов нет`);
}

const vseShagi = [...new Set(spisok.flatMap((s) => s.shagi))];
const bezPodpisi = vseShagi.filter((id) => !podpisi.includes(id));
if (bezPodpisi.length) {
  beda(`в заявке будут без названия: ${bezPodpisi.join(', ')} — ` +
       'владелица увидит голый ответ вроде «А4» и не поймёт, о чём он');
} else {
  norma('каждый вопрос попадает в заявку с названием');
}

/* ── Обещания клиенту ────────────────────────────────────────────────
   Смотрим ТОЛЬКО то, что видит человек. Комментарии выкидываем:
   в них разбор прошлых ошибок, и проверка ругалась на объяснение
   вместо самой ошибки. */
const vidimyj = ishodnik
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/^\s*\/\/.*$/gm, ' ')
  .replace(/<!--[\s\S]*?-->/g, ' ');
console.log('\nЧто секретарь обещает');
const zapreshcheno = [
  ['в течение суток', 'срок, которого нет в прайсе'],
  ['в течение дня', 'то же самое'],
  ['картон 300', 'принтер такую плотность не берёт'],
  ['картон 350', 'принтер такую плотность не берёт'],
  ['браузер не читает', 'неправда: PDF браузер открывает'],
];
for (const [slova, pochemu] of zapreshcheno) {
  if (vidimyj.toLowerCase().includes(slova)) beda(`обещание «${slova}» — ${pochemu}`);
}
if (!bed) norma('запрещённых обещаний не найдено');

/* ── Итог ──────────────────────────────────────────────────────────── */
console.log('\n' + (bed
  ? `НАЙДЕНО ПРОБЛЕМ: ${bed}`
  : 'Разговор целый: повторов нет, срок спрашивается, заявка читается.'));
process.exit(bed ? 1 : 0);
