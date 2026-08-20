/* Прайс для СТРАНИЦ УСЛУГ живого сайта.
 *
 *  Зачем отдельный генератор, если есть sekretar-ceny и bot-ceny.
 *  Секретарь считает цену в браузере, значит его таблицы живут
 *  в JavaScript — а поисковый робот читает JavaScript плохо. Запрос
 *  «сколько стоит напечатать грамоту в Лермонтове» закрывается только
 *  ценой, набранной обычным текстом в HTML.
 *
 *  Поэтому те же цифры выгружаются вторым файлом — JSON, который
 *  читает Flask и рисует таблицу на сервере. Источник тот же самый,
 *  data/prices.ts, и разъехаться они не могут.
 *
 *  Запуск: npm run sajt-ceny
 */
import {
  OTKRYTKI, PRIGLASHENIYA, VIZITKI, FOTO_NA_DOKUMENTY, CHERTEZHI,
  SHTUCHNAYA_A4, RABOTA_S_MAKETOM, KAK_SCHITAEM, DOSTAVKA,
  MAKSIMALNAYA_PLOTNOST, ISTOCHNIK,
} from '../data/prices.ts';
import { writeFileSync } from 'node:fs';

/** Таблица тиражей → простые строки для шаблона. */
function tablica(t: any) {
  return {
    zagolovok: t.zagolovok,
    edinica: t.edinica,
    pervyjStolbec: t.pervyjStolbec,
    kolonki: t.kolonki,
    stroki: t.stroki.map((s: any) => ({
      nazvanie: s.nazvanie,
      ceny: s.ceny.map((c: any) => (c == null ? '—' : `${c} ₽`)),
    })),
    primechaniya: t.primechaniya ?? [],
  };
}

const dannye = {
  sobrano: ISTOCHNIK.data,
  maksimalnayaPlotnost: MAKSIMALNAYA_PLOTNOST,
  otkrytki: tablica(OTKRYTKI),
  priglasheniya: tablica(PRIGLASHENIYA),
  vizitki: tablica(VIZITKI),
  chertezhi: tablica(CHERTEZHI),
  fotoNaDokumenty: {
    zagolovok: FOTO_NA_DOKUMENTY.zagolovok,
    vvodnaya: FOTO_NA_DOKUMENTY.vvodnaya,
    pozicii: FOTO_NA_DOKUMENTY.pozicii.map((p: any) => ({
      nazvanie: p.nazvanie,
      cena: typeof p.cena === 'number' ? `${p.cena} ₽` : String(p.cena ?? '—'),
    })),
  },
  maket: {
    zagolovok: RABOTA_S_MAKETOM.zagolovok,
    pozicii: RABOTA_S_MAKETOM.pozicii.map((p: any) => ({
      nazvanie: p.nazvanie,
      chtoDelaem: p.chtoDelaem,
      cena: typeof p.cena === 'number' ? `${p.cena} ₽` : String(p.cena ?? '—'),
    })),
  },
  sertifikatOt: SHTUCHNAYA_A4.roznicaSertifikat,
  shtuchnayaA4: SHTUCHNAYA_A4.cena,
  usloviya: KAK_SCHITAEM.map((k: any) => ({ nazvanie: k.nazvanie, tekst: k.tekst })),
  dostavka: DOSTAVKA.stroki.map((d: any) => ({ nazvanie: d.nazvanie, znachenie: d.znachenie })),
};

writeFileSync('zhivoj-sajt/ceny.json', JSON.stringify(dannye, null, 2) + '\n', 'utf8');
console.log('Готово: zhivoj-sajt/ceny.json — цены страниц услуг обновлены из прайса.');
