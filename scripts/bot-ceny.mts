/* Цены для бота ВКонтакте и Telegram — из того же прайса, что и сайт.

   Запуск:  npm run bot-ceny
   Кладёт:  bot/ceny_iz_prajsa.py

   ЗАЧЕМ. У бота свой прайс на Python — `prices.py`. Он писался
   10.08.2026 и с тех пор отстал: обещает картон 300 и 350 г/м²,
   которых принтер не берёт, и держит цены листовок, снятые 18.08
   как убыточные.

   Это ровно та беда, от которой владелица предостерегала 13.08:
   «мы можем подправить прайс на сайте и забыть про бота. Это должно
   быть автоматическое обновление».

   ЧТО ДЕЛАЕМ. Цифры генерируются сюда из data/prices.ts. Логика бота
   остаётся своей — меняются только числа, и меняются в одном месте.

   КАК ПОДКЛЮЧИТЬ в prices.py:
       from ceny_iz_prajsa import PRICES_ROWS, COEFFICIENTS, OPLATA, ADDONS_NOVYE
   и заменить одноимённые куски. Пока этого не сделано, файл лежит
   рядом и ни на что не влияет. */

import { writeFileSync, mkdirSync } from 'node:fs';
import {
  FLAERY, VIZITKI, NACENKA_ZA_PLOTNOST, ZAPOLNENIE_MAKETA,
  OPLATA, OTDELKA, DOSTAVKA, MAKSIMALNAYA_PLOTNOST,
} from '../data/prices.ts';

const cena = (v: unknown) =>
  typeof v === 'number' ? v : (v && typeof v === 'object' && 'ot' in (v as any)) ? (v as any).ot : null;

/* Ступени тиража прайса -> границы для бота. Бот ищет строку по «от и до»,
   поэтому верхнюю границу берём до начала следующей ступени. */
const STUPENI: [number, number][] = [[50, 199], [200, 499], [500, 999], [1000, 10 ** 6]];
const FORMATY: Record<string, string> = {
  'А6, 105×148 мм': 'A6', 'Евро, 210×97 мм': 'euro',
  'А5, 148×210 мм': 'A5', 'А4, 210×297 мм': 'A4',
};

const stroki: string[] = [];
for (const s of FLAERY.stroki) {
  const f = FORMATY[s.nazvanie];
  if (!f) continue;
  s.ceny.forEach((c: unknown, i: number) => {
    const p = cena(c);
    if (p == null || !STUPENI[i]) return;
    stroki.push(`    ("flyers", {"format": "${f}"}, ${STUPENI[i][0]}, ${STUPENI[i][1]}, ${p}, "per_piece"),`);
  });
}

const vizitki: string[] = [];
VIZITKI.stroki.forEach((s: any) => {
  const storon = s.nazvanie.indexOf('4+4') === 0 ? 'two' : 'one';
  s.ceny.forEach((c: unknown, i: number) => {
    const p = cena(c);
    const tirazh = [50, 100, 200, 500][i];
    if (p == null || !tirazh) return;
    vizitki.push(`    ("cards", {"sides": "${storon}"}, ${tirazh}, ${tirazh}, ${p}, "per_order"),`);
  });
});

const plotnosti = NACENKA_ZA_PLOTNOST.stroki
  .filter((p: any) => p.nacenka > 0)
  .map((p: any) => {
    const klyuch = 'paper_' + p.bumaga.replace(/[^0-9]/g, '').slice(-3);
    return `    "${klyuch}": ("Бумага ${p.bumaga}", ${(1 + p.nacenka / 100).toFixed(2)}, "base"),`;
  });

const zalivka = ZAPOLNENIE_MAKETA.stroki.map((z: any, i: number) => {
  const klyuch = ['fill_light', 'fill_standard', 'fill_dense'][i];
  const imya = z.nazvanie.split(':')[0];
  return `    "${klyuch}": ("Заполнение макета: ${imya.toLowerCase()}", ${z.koef}, "base"),`;
});

const py = `# -*- coding: utf-8 -*-
# ФАЙЛ СОБРАН АВТОМАТИЧЕСКИ: npm run bot-ceny
# Руками не править — правку затрёт следующая сборка.
# Цены живут в data/prices.ts, оттуда и берутся.
#
# Собрано из прайса студии «Гранат». Числа те же, что на сайте
# и у секретаря: один источник, чтобы бот и сайт не спорили.

# ── Строки цен ───────────────────────────────────────────────────────
# Формат тот же, что в prices.py: (услуга, признаки, от, до, цена, режим)
PRICES_ROWS = [
    # Листовки. Цены пересчитаны 18.08.2026 от себестоимости: старые
    # были ниже стоимости материалов на всех тиражах.
${stroki.join('\n')}

    # Визитки. Подняты 18.08.2026 до рыночных: были дешевле конкурентов
    # на бумаге плотнее.
${vizitki.join('\n')}
]

# ── Множители ────────────────────────────────────────────────────────
COEFFICIENTS = {
    "urgent": ("Срочно, день в день", ${(1 + 30 / 100).toFixed(2)}, "total"),

    # Плотность бумаги. Наценки те же, что на сайте.
${plotnosti.join('\n')}

    # ЗАПОЛНЕНИЕ МАКЕТА — новое с 18.08.2026 и главное для цены.
    # Струйник тратит чернила по площади краски: белая листовка
    # и фотоколлаж стоят студии по-разному в разы.
${zalivka.join('\n')}
}

# КАРТОН 300 и 350 г/м² УДАЛЁН. Принтер Epson L8188 берёт до
# ${MAKSIMALNAYA_PLOTNOST} г/м², и обещать плотнее нельзя: проверено живой
# печатью 17.08.2026, владелица потратила на этом пачку бумаги.
# Если в prices.py остались ключи carton_300 или carton_350 — убрать.

# ── Что раньше отдавалось бесплатно ──────────────────────────────────
# 18.08.2026: в июльском заказе открытка украшалась глиттером вручную,
# клалась в плотный файл и везлась такси за счёт студии. Ни одной
# из этих строк в прайсе не было, и в счёт они не попали.
ADDONS_NOVYE = {
    "handwork":  ("Ручная отделка: глиттер, стразы, ленты", ${OTDELKA.ruchnayaOtdelka}, "per_piece"),
    "hard_pack": ("Жёсткая упаковка: файл, конверт, подложка", ${OTDELKA.zhestkayaUpakovka}, "per_piece"),
    "delivery":  ("Доставка по Лермонтову", ${DOSTAVKA.poLermontovu}, "per_order"),
}
DOSTAVKA_BESPLATNO_OT = ${DOSTAVKA.besplatnoOt}

# Доставка по КМВ — два способа. Цифры с живой отправки Пятигорск —
# Лермонтов, поэтому называть их только со словом «от»: до Кисловодска
# дальше и выйдет дороже.
DOSTAVKA_KMV = {
    "kurer": (${DOSTAVKA.poKmvKurer}, "${DOSTAVKA.poKmvKurerSrok}"),
    "pvz_ozon": (${DOSTAVKA.poKmvPvz}, "${DOSTAVKA.poKmvPvzSrok}"),
}

# ── Оплата ───────────────────────────────────────────────────────────
# На тиражах от ${OPLATA.bolshojTirazhOt} штук предоплата выше: материалы
# закупаются ДО печати, а ${OPLATA.predoplataProcent}% их не покрывают.
OPLATA = {
    "predoplata_procent": ${OPLATA.predoplataProcent},
    "predoplata_bolshoj_tirazh": ${OPLATA.predoplataBolshojTirazh},
    "bolshoj_tirazh_ot": ${OPLATA.bolshojTirazhOt},
}

# ── Обязательные параметры, которые надо спросить ДО цены ────────────
# Указание владелицы 18.08.2026: «макет надо просить раньше, чем
# обговаривать цену». Без заливки цену листовок назвать нельзя —
# ошибка достигает 70%.
REQUIRED_DOPOLNENIYA = {
    "flyers": ("layout", "fill"),
}
`;

mkdirSync('bot', { recursive: true });
writeFileSync('bot/ceny_iz_prajsa.py', py);
console.log(`Готово: bot/ceny_iz_prajsa.py — ${stroki.length} строк листовок, ${vizitki.length} визиток,`);
console.log(`        ${plotnosti.length} плотностей, ${zalivka.length} категорий заливки.`);
