/* Шпаргалка у стойки — одна страница А4, которую можно распечатать
   и положить рядом с кассой.

   Запуск:  npm run shpargalka
   Результат: shpargalka.html в корне. Открыть в браузере, Ctrl+P,
   поставить галочку «Фоновая графика» — и на бумагу.

   ЗАЧЕМ. Прайс — десять страниц, и при клиенте их не листают. Раньше
   цену за штучный сертификат называли на глаз: 16.08.2026 вышло 50 ₽
   там, где бот считал 1200 ₽. Шпаргалка нужна, чтобы у стойки лежал
   ответ, а не догадка.

   ПОЧЕМУ ГЕНЕРАТОР, А НЕ ГОТОВЫЙ ФАЙЛ. Переписанная руками цена
   разъезжается — на этом проекте уже дважды. Здесь все числа берутся
   из `data/prices.ts`. Поменяли прайс — перегенерировали шпаргалку,
   и она не может отстать. */

import {
  STUDIYA,
  MAKSIMALNAYA_PLOTNOST,
  ISTOCHNIK,
  FOTO_NA_DOKUMENTY,
  KSEROKOPIYA,
  PECHAT_FOTO,
  FLAERY,
  OTKRYTKI,
  PRIGLASHENIYA,
  LAMINACIYA,
  PRIGLASHENIE_INDIVIDUALNOE,
  MATERIAL_I_OTDELKA,
  DOSTAVKA,
  RABOTA_S_MAKETOM,
  KAK_SCHITAEM,
  NET_V_PRAJSE,
  cenaTekstom,
  type TirazhTablica,
} from '../data/prices.ts';

import { writeFileSync } from 'node:fs';

const ekr = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Таблица тиражей в компактном виде: формат и цены по столбцам. */
function tablica(t: TirazhTablica, tolkoStroki?: string[]): string {
  const stroki = tolkoStroki
    ? t.stroki.filter((s) => tolkoStroki.includes(s.nazvanie))
    : t.stroki;

  const shapka = t.kolonki.map((k) => `<th>${ekr(k)}</th>`).join('');
  const telo = stroki
    .map(
      (s) =>
        `<tr><td class="n">${ekr(s.nazvanie)}</td>` +
        s.ceny.map((c) => `<td>${ekr(cenaTekstom(c))}</td>`).join('') +
        '</tr>',
    )
    .join('');

  return `<table><thead><tr><th class="n">${ekr(t.pervyjStolbec)}</th>${shapka}</tr></thead><tbody>${telo}</tbody></table>`;
}

/** Простой список «услуга — цена». */
function spisok(pozicii: { nazvanie: string; cena: unknown }[]): string {
  return (
    '<ul class="pl">' +
    pozicii
      .map(
        (p) =>
          `<li><span>${ekr(p.nazvanie)}</span><b>${ekr(cenaTekstom(p.cena as never))}</b></li>`,
      )
      .join('') +
    '</ul>'
  );
}

const minimalki = KAK_SCHITAEM.find((k) => k.nazvanie === 'Минимальный заказ');
const srochno = KAK_SCHITAEM.find((k) => k.nazvanie === 'Срочно');
const srok = KAK_SCHITAEM.find((k) => k.nazvanie === 'Срок');
const predoplata = KAK_SCHITAEM.find((k) => k.nazvanie === 'Предоплата');

const html = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Шпаргалка у стойки — ${ekr(STUDIYA.nazvanie)}</title>
<style>
  @page { size: A4; margin: 8mm; }
  * { box-sizing: border-box; }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 8.4pt; line-height: 1.28; color: #1a1a1a; margin: 0;
  }
  h1 { font-size: 14pt; margin: 0 0 1mm; color: #4A0E17; }
  .sub { font-size: 7.4pt; color: #666; margin-bottom: 2.5mm; }
  .cols { column-count: 2; column-gap: 6mm; }
  section { break-inside: avoid; margin-bottom: 3mm; }
  h2 {
    font-size: 8.8pt; margin: 0 0 1mm; padding: 0.8mm 1.6mm;
    background: #4A0E17; color: #fff; border-radius: 1mm;
  }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 0.5mm 1mm; text-align: right; border-bottom: 0.2mm solid #e2e2e2; }
  th { font-size: 7.2pt; color: #666; font-weight: 600; }
  .n { text-align: left; }
  td.n { font-weight: 600; }
  ul.pl { list-style: none; margin: 0; padding: 0; }
  ul.pl li {
    display: flex; justify-content: space-between; gap: 2mm;
    border-bottom: 0.2mm solid #e2e2e2; padding: 0.5mm 1mm;
  }
  ul.pl li b { white-space: nowrap; }
  .vopros { background: #FFF6E5; border: 0.3mm solid #E5B25D; border-radius: 1.5mm; padding: 2mm; }
  .vopros ol { margin: 0; padding-left: 4.5mm; }
  .vopros li { margin-bottom: 0.8mm; }
  .stop { background: #FDECEC; border: 0.3mm solid #D98A8A; border-radius: 1.5mm; padding: 2mm; }
  .stop b { color: #8B1A1A; }
  .note { font-size: 7.2pt; color: #555; margin-top: 1mm; }
  .big { font-size: 9.6pt; font-weight: 700; color: #4A0E17; }
  footer { margin-top: 2mm; font-size: 6.8pt; color: #888; text-align: center; }
</style>
</head>
<body>

<h1>Шпаргалка у стойки — ${ekr(STUDIYA.nazvanie)}</h1>
<div class="sub">${ekr(STUDIYA.telefon)} · ${ekr(STUDIYA.adres)} · ${ekr(STUDIYA.chasy)}</div>

<div class="cols">

<section class="vopros">
  <h2>Сначала спросить — потом называть цену</h2>
  <ol>
    <li><b>Сколько штук.</b> Цена за штуку падает с тиражом в два-три раза.</li>
    <li><b>Формат.</b> А6, Евро, А5, А4 — разные строки прайса.</li>
    <li><b>Макет готов?</b> Готов — печатаем по прайсу. Нет — это индивидуальная работа, ${ekr(cenaTekstom(PRIGLASHENIE_INDIVIDUALNOE.cena))} за штуку.</li>
    <li><b>Бумага.</b> До 200 г/м² — распечатка. От 250 г/м² плотная матовая — считается как открытка. <b>Выше ${MAKSIMALNAYA_PLOTNOST} г/м² принтер не берёт.</b></li>
    <li><b>Когда нужно.</b> ${ekr(srochno?.tekst ?? '')}</li>
  </ol>
  <div class="note">Файл принимаем почтой: ${ekr('gulnaravibecoder999@yandex.ru')}. Из мессенджера картинка сжата — в печати видны пятна и рваные края.</div>
</section>

<section>
  <h2>Открытки, сертификаты, дипломы · плотная матовая бумага 250–${MAKSIMALNAYA_PLOTNOST} г/м²</h2>
  ${tablica(OTKRYTKI)}
  <div class="note">
    <span class="big">Штучно А4 — 200 ₽/шт, заказ от 1200 ₽.</span><br>
    Сертификат, диплом, грамота на плотной бумаге — это ЭТА таблица, а не распечатка за 35 ₽. Жёсткого мелованного картона у нас НЕТ.
  </div>
</section>

<section>
  <h2>Приглашения по готовому макету</h2>
  ${tablica(PRIGLASHENIYA)}
  <div class="note">Макета нет — индивидуальное, ${ekr(cenaTekstom(PRIGLASHENIE_INDIVIDUALNOE.cena))} за штуку, минимум 10 штук.</div>
</section>

<section>
  <h2>Копия и распечатка · за лист</h2>
  ${tablica(KSEROKOPIYA)}
  <div class="note">Двусторонняя печать считается как два листа.</div>
</section>

<section>
  <h2>Фото на документы</h2>
  ${spisok(FOTO_NA_DOKUMENTY.pozicii)}
</section>

<section>
  <h2>Печать фотографий · за штуку</h2>
  ${tablica(PECHAT_FOTO)}
</section>

<section>
  <h2>Флаеры и листовки · за штуку</h2>
  ${tablica(FLAERY)}
  <div class="note">Мелованная 130 г/м², полноцвет с двух сторон, с резкой. Плотнее: 150 г/м² +10%, 170 +15%, 200 +25%.</div>
</section>

<section>
  <h2>Ламинация · за лист</h2>
  ${tablica(LAMINACIYA, ['А5, 80–100 мкм', 'А4, 80–100 мкм', 'А3, 80–100 мкм', 'А4, 250 мкм'])}
</section>

<section>
  <h2>Доплаты сверху</h2>
  <ul class="pl">
    ${MATERIAL_I_OTDELKA.stroki.map((s) => `<li><span>${ekr(s.nazvanie)}</span><b>${ekr(s.znachenie)}</b></li>`).join('')}
  </ul>
</section>

<section>
  <h2>Доставка — называть вместе с ценой</h2>
  <ul class="pl">
    ${DOSTAVKA.stroki.map((d) => `<li><span>${ekr(d.nazvanie)}</span><b>${ekr(d.znachenie)}</b></li>`).join('')}
  </ul>
  <div class="note">Не назвали — значит отдали даром. В июле заказ увезли
  такси за счёт студии, потому что строки о доставке в прайсе не было.</div>
</section>

<section>
  <h2>Работа с макетом</h2>
  ${spisok(RABOTA_S_MAKETOM.pozicii)}
</section>

<section>
  <h2>Условия сделки — называть вместе с ценой</h2>
  <div class="note"><b>Минимальный заказ:</b> ${ekr(minimalki?.tekst ?? '')}</div>
  <div class="note"><b>Срок:</b> ${ekr(srok?.tekst ?? '')}</div>
  <div class="note"><b>Срочно:</b> ${ekr(srochno?.tekst ?? '')}</div>
  <div class="note"><b>Предоплата:</b> ${ekr(predoplata?.tekst ?? '')}</div>
</section>

<section class="stop">
  <h2>Не обещать — этого у нас нет</h2>
  <b>${NET_V_PRAJSE.map(ekr).join(' · ')}</b>
  <div class="note">Спрашивают — говорим прямо, что не делаем, и предлагаем то, что делаем. Обещание, которого нельзя закрыть, дороже потерянного заказа.</div>
</section>

</div>

<footer>Собрано из data/prices.ts · источник: печатный прайс от ${ekr(ISTOCHNIK.data)} · цены менять только в прайсе, шпаргалку пересобирать</footer>

</body>
</html>
`;

writeFileSync(new URL('../shpargalka.html', import.meta.url), html, 'utf8');
console.log('Готово: shpargalka.html — открыть в браузере и печатать (Ctrl+P, «Фоновая графика»).');
