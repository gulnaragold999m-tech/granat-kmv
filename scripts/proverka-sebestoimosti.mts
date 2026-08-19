/* Проверка прайса на убыточность: где цена ниже материалов.

   Запуск:  npm run sebestoimost-prajs

   ЗАЧЕМ. 18.08.2026 выяснилось, что тираж 500 листовок А4 с плотной
   заливкой уходит в минус на 11 718 ₽. Вопрос владелицы: «давай-ка
   весь прайс пересчитаем, надо внимательно относиться к работе».

   ЧТО ЭТО ДЕЛАЕТ. Считает материалы на каждое изделие и сравнивает
   с ценой из прайса. Цены НЕ МЕНЯЕТ — печатает, где мы в минусе.

   ЧЕГО ЭТО НЕ ДЕЛАЕТ. Не считает копии, ламинацию, чертежи и плакаты:
   там другой расходник — тонер, плёнка, рулон плоттера, — и его цену
   мы не знаем. Не считает время работы: только материалы. */

import { SEBESTOIMOST_RASHODNIKOV as R, POSTOYANNYE_RASHODY as P, ZAPOLNENIE_MAKETA as Z } from '../data/prices.ts';
import * as PRAJS from '../data/prices.ts';

const rub = (n: number) => n.toFixed(1).replace('.', ',') + ' ₽';

/* Сколько изделий помещается на лист А4 и какую долю его площади
   занимает одно. Бумага делится на число изделий, чернила — по площади. */
const GEOMETRIYA: Record<string, { naListe: number; dolya: number; storon: number }> = {
  'А6':                { naListe: 4,  dolya: 0.25,  storon: 2 },
  'А6, 105×148 мм':    { naListe: 4,  dolya: 0.25,  storon: 2 },
  'Евро':              { naListe: 3,  dolya: 1 / 3, storon: 2 },
  'Евро, 210×97 мм':   { naListe: 3,  dolya: 1 / 3, storon: 2 },
  'А5':                { naListe: 2,  dolya: 0.5,   storon: 2 },
  'А5, 148×210 мм':    { naListe: 2,  dolya: 0.5,   storon: 2 },
  'А4':                { naListe: 1,  dolya: 1,     storon: 2 },
  'А4, 210×297 мм':    { naListe: 1,  dolya: 1,     storon: 2 },
  '4+0, односторонние': { naListe: 10, dolya: 0.1,  storon: 1 },
  '4+4, двусторонние':  { naListe: 10, dolya: 0.1,  storon: 2 },
};

const RAZDELY = [
  { klyuch: 'FLAERY', shtukVStupeni: [100, 300, 500, 1000] },
  { klyuch: 'OTKRYTKI', shtukVStupeni: [20, 50, 100, 200] },
  { klyuch: 'PRIGLASHENIYA', shtukVStupeni: [20, 50, 100, 200] },
  { klyuch: 'VIZITKI', shtukVStupeni: [50, 100, 200, 500] },
];

const scenarii = ['legkaya', 'srednyaya', 'plotnaya'] as const;

function materialyNaShtuku(g: { naListe: number; dolya: number; storon: number }, zalivka: typeof scenarii[number]) {
  const ml = R.ocenkaRashoda[zalivka];
  const chernila = g.dolya * ml * g.storon * R.chernila.zaMl;
  const bumaga = (R.bumaga130.zaList * R.zapasBumagi) / g.naListe;
  return chernila + bumaga;
}

const cena = (v: unknown) =>
  typeof v === 'number' ? v : (v && typeof v === 'object' && 'ot' in (v as any)) ? (v as any).ot : null;

console.log('\nПРОВЕРКА ПРАЙСА НА УБЫТОЧНОСТЬ');
console.log('Считаются только материалы: чернила по площади + бумага 130 г/м².');
console.log(`Чернила ${R.chernila.zaMl.toFixed(2)} ₽/мл · бумага ${R.bumaga130.zaList} ₽/лист А4 · запас ${Math.round((R.zapasBumagi - 1) * 100)}%\n`);

const minusy: string[] = [];

for (const { klyuch, shtukVStupeni } of RAZDELY) {
  const t = (PRAJS as any)[klyuch];
  console.log(`\n=== ${t.zagolovok} ===`);
  for (const stroka of t.stroki) {
    const g = GEOMETRIYA[stroka.nazvanie];
    if (!g) { console.log(`  ${stroka.nazvanie}: геометрия не задана, пропуск`); continue; }
    const sebes = scenarii.map((s) => materialyNaShtuku(g, s));
    /* БАЗОВАЯ ЦЕНА В ПРАЙСЕ — ЗА ЛЁГКУЮ ЗАЛИВКУ. Плотная продаётся
       с коэффициентом из ZAPOLNENIE_MAKETA, поэтому сравнивать надо
       цену×коэффициент с себестоимостью ТОЙ ЖЕ категории, а не базовую
       цену с плотной себестоимостью. Первая версия скрипта сравнивала
       напрямую и давала ложные минусы — по ним чуть не «починили»
       только что переписанные цены. */
    const koef = Z.stroki.map((s: any) => s.koef);
    const strokaVyvoda = stroka.ceny.map((c: unknown, i: number) => {
      const p = cena(c);
      if (p == null) return `${t.kolonki[i]}: —`;
      const zaShtuku = klyuch === 'VIZITKI' ? p / shtukVStupeni[i] : p;
      /* Проверяем все три категории: цена за категорию против её же
         себестоимости. Минус хотя бы в одной — позиция под вопросом. */
      const vMinuse = sebes.map((s, k) => zaShtuku * koef[k] < s);
      const marker = vMinuse[2] ? '✖ плотная' : vMinuse[1] ? '✖ средняя' : vMinuse[0] ? '✖ лёгкая' : '  ';
      if (vMinuse.some(Boolean)) minusy.push(`${t.zagolovok} · ${stroka.nazvanie} · ${t.kolonki[i]}`);
      return `${t.kolonki[i]}: ${rub(zaShtuku)}${vMinuse.some(Boolean) ? ' ' + marker : ''}`;
    });
    console.log(`  ${stroka.nazvanie}`);
    console.log(`    себестоимость: лёгкая ${rub(sebes[0])} · средняя ${rub(sebes[1])} · плотная ${rub(sebes[2])}`);
    console.log(`    цена — ${strokaVyvoda.join(' | ')}`);
  }
}

console.log('\n\nБазовая цена сравнивается с себестоимостью по каждой категории заливки,');
console.log('с учётом коэффициентов ' + Z.stroki.map((s: any) => s.koef).join(' / ') + '.');
console.log(`\nПОЗИЦИЙ НИЖЕ СЕБЕСТОИМОСТИ: ${minusy.length}`);
for (const m of minusy) console.log('  · ' + m);

console.log('\nЧТО НЕ ПОСЧИТАНО:');
console.log('  · время работы — только материалы');
console.log('  · постоянные расходы: 14 000 ₽/мес, доля на заказ неизвестна');
console.log(`  · налог ${P.nalogProcent}% (НПД с физлиц; с юрлиц ${P.nalogProcentYurlico}%)` +
            ` и эквайринг ${P.ekvajringProcent}% — берутся сверху с выручки`);
console.log('  · бумага открыток и приглашений идёт 250–260 г/м², а не 130.');
console.log('    Её закупочная цена НЕ ИЗВЕСТНА, поэтому эти строки посчитаны');
console.log('    по дешёвой бумаге и в реальности ДОРОЖЕ.');
console.log('  · копии, ламинация, чертежи, плакаты, фото — другой расходник\n');
