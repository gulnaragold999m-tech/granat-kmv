/* Себестоимость заказа: материалы, налог, банк и доля постоянных расходов.

   Запуск:  npm run sebestoimost

   ЗАЧЕМ. 18.08.2026 выяснилось, что тираж 500 листовок А4 с плотной
   заливкой уходит в минус на материалах. А владелица напомнила то,
   чего в расчёте не было вовсе: «налоговая сразу свои деньги возьмут,
   банк своё возьмёт, у меня ещё аренда, свет, интернет, ИИ-модели».

   Считать это в уме нельзя, а в переписке цифры теряются. Поэтому
   расчёт живёт скриптом и берёт числа из data/prices.ts. */

import { SEBESTOIMOST_RASHODNIKOV as R, POSTOYANNYE_RASHODY as P } from '../data/prices.ts';

const rub = (n: number) => Math.round(n).toLocaleString('ru-RU') + ' ₽';

/* Заказ, который разбираем. Меняется руками — это рабочий инструмент,
   а не витрина. */
const ZAKAZ = {
  imya: 'Витражи: 500 листовок А4, 4+4, плотная заливка',
  cena: 12000,
  listov: 500,
  storon: 2,
  zalivka: 'plotnaya' as keyof typeof R.ocenkaRashoda,
};

const rashodMl = R.ocenkaRashoda[ZAKAZ.zalivka];
const chernilaNaList = rashodMl * ZAKAZ.storon * R.chernila.zaMl;
const bumagaNaList = R.bumaga130.zaList * R.zapasBumagi;
const materialy = (chernilaNaList + bumagaNaList) * ZAKAZ.listov;

const nalog = ZAKAZ.cena * P.nalogProcent / 100;
const bank = ZAKAZ.cena * P.ekvajringProcent / 100;

console.log(`\n${ZAKAZ.imya}\nЦена для клиента: ${rub(ZAKAZ.cena)}\n`);
console.log('РАСХОДЫ:');
console.log(`  чернила   ${rub(chernilaNaList * ZAKAZ.listov)}  (${rashodMl} мл на сторону — ОЦЕНКА, не замер)`);
console.log(`  бумага    ${rub(bumagaNaList * ZAKAZ.listov)}  (с запасом ${Math.round((R.zapasBumagi - 1) * 100)}%)`);
console.log(`  налог     ${rub(nalog)}  (${P.nalogProcent}% с выручки)`);
console.log(`  банк      ${rub(bank)}  (${P.ekvajringProcent}% эквайринг)`);

/* Постоянные расходы считаем по тем строкам, что названы. Незаполненные
   пропускаем и говорим об этом вслух — молчаливый ноль хуже пробела. */
const stroki: [string, number | null][] = [
  ['аренда', P.arenda], ['свет', P.svet], ['интернет', P.internet],
  ['телефон', P.telefon], ['ИИ-модели', P.iiModeli], ['прочее', P.prochee],
];
const nazvany = stroki.filter(([, v]) => v != null);
const netu = stroki.filter(([, v]) => v == null).map(([k]) => k);
const vMesyac = nazvany.reduce((s, [, v]) => s + (v as number), 0);

console.log(`\nПОСТОЯННЫЕ РАСХОДЫ: ${rub(vMesyac)} в месяц`);
console.log('  ' + nazvany.map(([k, v]) => `${k} ${rub(v as number)}`).join(' · '));
if (netu.length) console.log(`  НЕ НАЗВАНО: ${netu.join(', ')} — значит сумма занижена`);

let dolyaPostoyannyh = 0;
if (P.zakazovVMesyac != null) {
  dolyaPostoyannyh = vMesyac / P.zakazovVMesyac;
  console.log(`  на один заказ: ${rub(dolyaPostoyannyh)} (÷ ${P.zakazovVMesyac} заказов)`);
} else {
  console.log('  Сколько заказов в месяц — НЕ НАЗВАНО. Вилка:');
  for (const n of [10, 20, 30, 50]) {
    console.log(`     ${String(n).padStart(2)} заказов -> ${rub(vMesyac / n)} на заказ`);
  }
  console.log('  В расчёте ниже доля постоянных расходов НЕ учтена.');
}

const itog = ZAKAZ.cena - materialy - nalog - bank - dolyaPostoyannyh;
console.log(`\n  ИТОГО расходов: ${rub(materialy + nalog + bank + dolyaPostoyannyh)}`);
console.log(`  ${itog >= 0 ? 'ПРИБЫЛЬ' : 'УБЫТОК'}: ${rub(Math.abs(itog))}\n`);

const nol = (materialy + dolyaPostoyannyh) / (1 - (P.nalogProcent + P.ekvajringProcent) / 100);
console.log(`Чтобы выйти в ноль, тираж должен стоить ${rub(nol)} — это ${rub(nol / ZAKAZ.listov)} за лист.`);
console.log(`С прибылью 30%: ${rub(nol * 1.3)}, или ${rub(nol * 1.3 / ZAKAZ.listov)} за лист.\n`);
