/* Печатает весь прайс студии в окно.

   Запуск:  npm run ceny

   Нужен, чтобы посмотреть прайс целиком, не открывая код: цена лежит
   в `data/prices.ts` вперемешку со скобками, а здесь выходит списком. */

import { prajsTekstom } from '../data/prices.ts';

console.log(prajsTekstom());
