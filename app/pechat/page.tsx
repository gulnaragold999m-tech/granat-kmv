/* Страница «Печать и полиграфия».

   ЦЕНЫ ЗДЕСЬ НЕ ПИШУТСЯ РУКАМИ. Всё, что видно на странице, берётся
   из `data/prices.ts` — там источник правды. До 15.08.2026 цены стояли
   в разметке, и это были выдуманные цифры: визитки 200–500 ₽,
   фирменный стиль 5000–15000 ₽. В печатном прайсе таких позиций нет,
   а приглашение А6 сотней стоит не «500–2000 ₽», а 38 ₽ за штуку.
   Человек приходил с одной цифрой в голове и слышал другую. */

import Link from 'next/link';
import FormWithConsent from '../FormWithConsent';
import {
  STUDIYA,
  ISTOCHNIK,
  FOTO_NA_DOKUMENTY,
  RAZDELY,
  NACENKA_ZA_PLOTNOST,
  PRIGLASHENIE_INDIVIDUALNOE,
  MATERIAL_I_OTDELKA,
  RABOTA_S_MAKETOM,
  KAK_SCHITAEM,
  ZAKLYUCHENIE,
  cenaTekstom,
  type TirazhTablica,
} from '../../data/prices';

export const metadata = {
  title: 'Печать и полиграфия в Лермонтове — прайс | Студия «Гранат»',
  description:
    'Фото на документы от 150 ₽, печать фотографий от 20 ₽, ксерокопия от 8 ₽ за лист, флаеры от 8 ₽, буклеты, открытки, чертежи А0, ламинация. Студия «Гранат», Лермонтов, работаем по всему КМВ.',
};

/* Таблица прокручивается вбок на телефоне: у чертежей четыре столбца,
   и на 360 пикселях они иначе не помещаются. */
function Tablica({ t }: { t: TirazhTablica }) {
  return (
    <div className="mb-12">
      <h3 className="text-2xl font-bold mb-1 text-gray-900">{t.zagolovok}</h3>
      <p className="text-sm uppercase tracking-wide text-gray-500 mb-4">{t.edinica}</p>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-300">
              <th scope="col" className="py-2 pr-4 text-sm font-semibold text-gray-500">
                {t.pervyjStolbec}
              </th>
              {t.kolonki.map((k) => (
                <th
                  key={k}
                  scope="col"
                  className="py-2 pr-4 text-sm font-semibold text-gray-500 whitespace-nowrap"
                >
                  {k}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {t.stroki.map((s) => (
              <tr key={s.nazvanie} className="border-b border-gray-200">
                <th scope="row" className="py-3 pr-4 font-medium text-gray-900 text-left">
                  {s.nazvanie}
                </th>
                {s.ceny.map((c, i) => (
                  <td key={i} className="py-3 pr-4 text-gray-900 whitespace-nowrap">
                    {cenaTekstom(c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {t.primechaniya.length > 0 && (
        <ul className="mt-4 space-y-1 text-sm text-gray-600">
          {t.primechaniya.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Pechat() {
  return (
    <div>
      {/* Первый экран */}
      <section className="bg-gradient-to-b from-red-50 to-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900">
            Печать и полиграфия
          </h1>
          <p className="text-xl text-gray-600 mb-6">
            Фото на документы, печать фотографий, копии, флаеры, буклеты, открытки
            и приглашения, чертежи до А0, ламинация. Печатаем при вас, если файл готов.
          </p>
          <dl className="grid sm:grid-cols-3 gap-4 mb-8 text-sm">
            <div>
              <dt className="text-gray-500">Адрес</dt>
              <dd className="text-gray-900 font-medium">{STUDIYA.adres}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Часы работы</dt>
              <dd className="text-gray-900 font-medium">{STUDIYA.chasy}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Телефон</dt>
              <dd className="font-medium">
                <a
                  href={`tel:${STUDIYA.telefonSsylka}`}
                  className="text-red-600 hover:underline focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
                >
                  {STUDIYA.telefon}
                </a>
              </dd>
            </div>
          </dl>
          <a
            href="#zayavka"
            className="inline-block px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-600"
          >
            Прислать макет на расчёт
          </a>
        </div>
      </section>

      {/* Фото на документы */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-2 text-gray-900">
            {FOTO_NA_DOKUMENTY.zagolovok}
          </h2>
          <p className="text-gray-600 mb-6">{FOTO_NA_DOKUMENTY.vvodnaya}</p>

          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-300">
                <th scope="col" className="py-2 pr-4 text-sm font-semibold text-gray-500">
                  услуга
                </th>
                <th scope="col" className="py-2 text-sm font-semibold text-gray-500 text-right">
                  цена
                </th>
              </tr>
            </thead>
            <tbody>
              {FOTO_NA_DOKUMENTY.pozicii.map((p) => (
                <tr key={p.nazvanie} className="border-b border-gray-200">
                  <th scope="row" className="py-3 pr-4 font-medium text-gray-900 text-left">
                    {p.nazvanie}
                  </th>
                  <td className="py-3 text-gray-900 text-right whitespace-nowrap">
                    {cenaTekstom(p.cena)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <ul className="mt-4 space-y-1 text-sm text-gray-600">
            {FOTO_NA_DOKUMENTY.primechaniya.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* Тиражные разделы прайса */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          {RAZDELY.map((r) => (
            <div key={r.id}>
              <Tablica t={r} />

              {r.id === 'flaery' && (
                <div className="mb-12 bg-white p-6 rounded-lg border border-gray-200">
                  <h4 className="font-bold text-gray-900 mb-4">
                    {NACENKA_ZA_PLOTNOST.zagolovok}
                  </h4>
                  <ul className="space-y-2 text-gray-700">
                    {NACENKA_ZA_PLOTNOST.stroki.map((p) => (
                      <li key={p.bumaga}>
                        {p.bumaga} — <span className="font-semibold">{p.tekst}</span>
                      </li>
                    ))}
                  </ul>
                  <ul className="mt-4 space-y-1 text-sm text-gray-600">
                    {NACENKA_ZA_PLOTNOST.primechaniya.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                </div>
              )}

              {r.id === 'priglasheniya' && (
                <div className="mb-12 bg-white p-6 rounded-lg border border-gray-200">
                  <h4 className="font-bold text-gray-900 mb-2">
                    {PRIGLASHENIE_INDIVIDUALNOE.nazvanie} —{' '}
                    {cenaTekstom(PRIGLASHENIE_INDIVIDUALNOE.cena)} за штуку
                  </h4>
                  <ul className="space-y-1 text-sm text-gray-600">
                    {PRIGLASHENIE_INDIVIDUALNOE.primechaniya.map((n) => (
                      <li key={n}>{n}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

          {/* Материал и отделка */}
          <div className="mb-4">
            <h3 className="text-2xl font-bold mb-1 text-gray-900">
              {MATERIAL_I_OTDELKA.zagolovok}
            </h3>
            <p className="text-sm uppercase tracking-wide text-gray-500 mb-4">
              {MATERIAL_I_OTDELKA.stolbec}
            </p>
            <table className="w-full text-left border-collapse">
              <tbody>
                {MATERIAL_I_OTDELKA.stroki.map((m) => (
                  <tr key={m.nazvanie} className="border-b border-gray-200">
                    <th scope="row" className="py-3 pr-4 font-medium text-gray-900 text-left">
                      {m.nazvanie}
                    </th>
                    <td className="py-3 text-gray-900 text-right whitespace-nowrap">
                      {m.znachenie}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Работа с макетом */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-2 text-gray-900">
            {RABOTA_S_MAKETOM.zagolovok}
          </h2>
          <p className="text-gray-600 mb-6">{RABOTA_S_MAKETOM.vvodnaya}</p>

          <div className="space-y-4">
            {RABOTA_S_MAKETOM.pozicii.map((p) => (
              <div
                key={p.nazvanie}
                className="border-b border-gray-200 pb-4 flex flex-col sm:flex-row sm:justify-between sm:gap-8"
              >
                <div>
                  <h3 className="font-bold text-gray-900">{p.nazvanie}</h3>
                  <p className="text-gray-600 text-sm">{p.chtoDelaem}</p>
                </div>
                <p className="text-red-600 font-semibold whitespace-nowrap mt-2 sm:mt-0">
                  {cenaTekstom(p.cena)}
                </p>
              </div>
            ))}
          </div>

          {RABOTA_S_MAKETOM.primechaniya.map((n) => (
            <p key={n} className="mt-6 text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
              {n}
            </p>
          ))}
        </div>
      </section>

      {/* Как мы считаем */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-gray-900">Как мы считаем</h2>
          <dl className="space-y-4">
            {KAK_SCHITAEM.map((k) => (
              <div key={k.nazvanie} className="border-b border-gray-200 pb-4">
                <dt className="font-bold text-gray-900">{k.nazvanie}</dt>
                <dd className="text-gray-600">{k.tekst}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Заявка */}
      <section className="py-16 px-4 bg-red-50">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-4 text-center text-gray-900" id="zayavka">
            {ZAKLYUCHENIE.zagolovok}
          </h2>
          {ZAKLYUCHENIE.tekst.map((t) => (
            <p key={t} className="text-center text-sm text-gray-600 mb-4">
              {t}
            </p>
          ))}

          <FormWithConsent />

          <p className="text-center text-sm text-gray-600 mt-6">
            Или позвоните:{' '}
            <a
              href={`tel:${STUDIYA.telefonSsylka}`}
              className="text-red-600 hover:underline font-semibold focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
            >
              {STUDIYA.telefon}
            </a>
          </p>
          <p className="text-center text-xs text-gray-500 mt-2">
            Прайс от {ISTOCHNIK.data}. {STUDIYA.ohvat}.
          </p>
        </div>
      </section>

      <section className="py-8 px-4 text-center">
        <Link
          href="/"
          className="text-red-600 hover:underline font-semibold focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
        >
          ← Вернуться на главную
        </Link>
      </section>
    </div>
  );
}
