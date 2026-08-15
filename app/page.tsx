/* Главная страница.

   ЦЕНЫ И СРОКИ БЕРУТСЯ ИЗ `data/prices.ts`. Руками сюда не вписывать:
   до 15.08.2026 на первом экране стояло «Печать приглашений,
   сертификатов, визиток» и «От 200 ₽», а в печатном прайсе студии нет
   ни визиток, ни сертификатов, и минимальный заказ по полиграфии —
   от 300 ₽. Обещание, которое нечем закрыть, дороже любой красивой
   строчки. */

import Link from 'next/link';
import { VITRINA, KAK_SCHITAEM, cenaTekstom } from '../data/prices';

const SROK = KAK_SCHITAEM.find((k) => k.nazvanie === 'Срок')!.tekst;

export default function Home() {
  return (
    <div>
      {/* Герой */}
      <section className="bg-gradient-to-b from-gray-50 to-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 text-gray-900">
            Типография и дизайн-студия в Лермонтове
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Фото на документы, печать фотографий, копии, флаеры, буклеты,
            открытки и приглашения, чертежи до А0, ламинация. Сайты и боты —
            в соседнем разделе.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/pechat"
              className="px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-600"
            >
              Прайс на печать
            </Link>
            <Link
              href="/cifra"
              className="px-8 py-3 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            >
              Сайты и боты
            </Link>
          </div>
        </div>
      </section>

      {/* Цены, которые спрашивают чаще всего */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-2 text-center text-gray-900">
            Сколько стоит
          </h2>
          <p className="text-center text-gray-600 mb-12">
            Четыре цены, которые спрашивают чаще всего. Остальное — в прайсе.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {VITRINA.map((v) => (
              <div key={v.chto} className="bg-gray-50 p-6 rounded-lg">
                <div className="text-2xl font-bold text-red-600 mb-2">
                  {cenaTekstom(v.cena)}
                </div>
                <h3 className="font-bold text-gray-900 mb-1">{v.chto}</h3>
                <p className="text-sm text-gray-600">{v.poyasnenie}</p>
              </div>
            ))}
          </div>
          <p className="text-center mt-8">
            <Link
              href="/pechat"
              className="text-red-600 hover:underline font-semibold focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
            >
              Весь прайс на печать →
            </Link>
          </p>
        </div>
      </section>

      {/* Почему упаковка решает */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-6 text-gray-900">
            Почему клиенты уходят к другим
          </h2>
          <div className="bg-white p-8 rounded-lg mb-8">
            <p className="text-lg text-gray-700 mb-4">
              Логотип «на коленке» и сайт из 2010-го убивают доверие ещё до
              разговора.
            </p>
            <p className="text-gray-600">
              Клиенту хватает пары секунд, чтобы решить: серьёзный вы бизнес —
              или «ещё один такой же». Слабая упаковка — и он уходит к тому, кто
              выглядит дороже. Даже если ваш продукт лучше.
            </p>
          </div>
        </div>
      </section>

      {/* Как работаем */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center text-gray-900">
            Как мы работаем
          </h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-gray-50 p-6 rounded-lg">
              <div className="text-2xl font-bold text-red-600 mb-2">Срок</div>
              <p className="text-gray-600">{SROK}</p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <div className="text-2xl font-bold text-red-600 mb-2">
                Файл готов — печатаем при вас
              </div>
              <p className="text-gray-600">
                Фото на документы и распечатка по готовому файлу не ждут очереди
                и не требуют согласования макета.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <div className="text-2xl font-bold text-red-600 mb-2">350 г/м²</div>
              <p className="text-gray-600">
                Плотный картон для открыток и приглашений — премиум в руке.
              </p>
            </div>
            <div className="bg-gray-50 p-6 rounded-lg">
              <div className="text-2xl font-bold text-red-600 mb-2">1 студия</div>
              <p className="text-gray-600">
                Печать и код под одной крышей — без пяти подрядчиков.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Услуги */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center text-gray-900">Услуги</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <Link
              href="/pechat"
              className="bg-gradient-to-br from-red-50 to-red-100 p-8 rounded-lg hover:shadow-lg transition focus:outline-none focus:ring-2 focus:ring-red-600"
            >
              <h3 className="text-2xl font-bold mb-4 text-gray-900">
                Печать и полиграфия
              </h3>
              <p className="text-gray-600 mb-4">
                Фото на документы, фотографии, копии и распечатка, флаеры,
                буклеты, открытки и приглашения, чертежи, ламинация.
              </p>
              <span className="text-red-600 font-semibold">Смотреть прайс →</span>
            </Link>
            <Link
              href="/cifra"
              className="bg-gradient-to-br from-blue-50 to-blue-100 p-8 rounded-lg hover:shadow-lg transition focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <h3 className="text-2xl font-bold mb-4 text-gray-900">Сайты и боты</h3>
              <p className="text-gray-600 mb-4">
                Лендинги, многостраничные сайты и боты кодом, без конструкторов.
              </p>
              <span className="text-blue-600 font-semibold">От 25 000 ₽ →</span>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 bg-red-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Пришлите макет</h2>
          <p className="text-lg mb-8">
            Посчитаем точную стоимость в день обращения: на цену влияют бумага,
            отделка и срок.
          </p>
          <Link
            href="/kontakty#zayavka"
            className="inline-block px-8 py-3 bg-white text-red-600 rounded-lg hover:bg-gray-100 transition font-semibold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white"
          >
            Оставить заявку
          </Link>
        </div>
      </section>
    </div>
  );
}
