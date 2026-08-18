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

const postoyannye = [P.arenda, P.svet, P.internet, P.iiModeli, P.prochee];
const zapolneny = postoyannye.every((v) => v != null) && P.zakazovVMesyac != null;

let dolyaPostoyannyh = 0;
if (zapolneny) {
  const vMesyac = postoyannye.reduce((s, v) => s + (v as number), 0);
  dolyaPostoyannyh = vMesyac / (P.zakazovVMesyac as number);
  console.log(`  аренда и прочее  ${rub(dolyaPostoyannyh)}  (${rub(vMesyac)} в месяц ÷ ${P.zakazovVMesyac} заказов)`);
} else {
  console.log('  аренда, свет, интернет, ИИ — НЕ ПОСЧИТАНЫ');
  console.log('     Заполнить POSTOYANNYE_RASHODY в data/prices.ts.');
  console.log('     Пока они пустые, ответ ниже ЗАВЫШЕН: реальный минус больше.');
}

const itog = ZAKAZ.cena - materialy - nalog - bank - dolyaPostoyannyh;
console.log(`\n  ИТОГО расходов: ${rub(materialy + nalog + bank + dolyaPostoyannyh)}`);
console.log(`  ${itog >= 0 ? 'ПРИБЫЛЬ' : 'УБЫТОК'}: ${rub(Math.abs(itog))}\n`);

const nol = (materialy + dolyaPostoyannyh) / (1 - (P.nalogProcent + P.ekvajringProcent) / 100);
console.log(`Чтобы выйти в ноль, тираж должен стоить ${rub(nol)} — это ${rub(nol / ZAKAZ.listov)} за лист.`);
console.log(`С прибылью 30%: ${rub(nol * 1.3)}, или ${rub(nol * 1.3 / ZAKAZ.listov)} за лист.\n`);
