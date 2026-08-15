import FormWithConsent from '../FormWithConsent';
import Link from 'next/link';
import { STUDIYA } from '../../data/prices';

export const metadata = {
  title: 'Контакты — студия «Гранат», Лермонтов',
  description:
    'Телефон, WhatsApp, почта и адрес студии «Гранат»: г. Лермонтов, ул. Нагорная 2/1, этаж 2. Работаем по всему КМВ.',
};

export default function Kontakty() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-b from-gray-900 to-gray-800 py-16 px-4 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">Контакты</h1>
          <p className="text-xl text-gray-300">
            Готовы обсудить ваш проект? Напишите, позвоните или встретимся.
          </p>
        </div>
      </section>

      {/* Контакты */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12">
            {/* Контактная информация */}
            <div>
              <h2 className="text-2xl font-bold mb-8 text-gray-900">Как нас найти</h2>

              <div className="space-y-8">
                {/* Телефон */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">Телефон</h3>
                  <a
                    href={`tel:${STUDIYA.telefonSsylka}`}
                    className="text-xl text-red-600 hover:underline font-semibold focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
                  >
                    {STUDIYA.telefon}
                  </a>
                  <p className="text-sm text-gray-600 mt-1">{STUDIYA.chasy}</p>
                </div>

                {/* Email */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">Email</h3>
                  <a
                    href="mailto:gulnaravibecoder999@yandex.ru"
                    className="text-lg text-red-600 hover:underline focus:outline-none focus:ring-2 focus:ring-red-600 rounded"
                  >
                    gulnaravibecoder999@yandex.ru
                  </a>
                  <p className="text-sm text-gray-600 mt-1">
                    Сюда же присылайте макет: мессенджеры сжимают картинки, и в печати это видно
                  </p>
                </div>

                {/* WhatsApp */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">WhatsApp</h3>
                  <a
                    href="https://wa.me/79992449999"
                    target="_blank"
                    rel="noopener"
                    className="text-lg text-red-600 hover:underline"
                  >
                    Написать в WhatsApp
                  </a>
                  <p className="text-sm text-gray-600 mt-1">Быстрая связь</p>
                </div>

                {/* Адрес */}
                <div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">Адрес</h3>
                  <p className="text-gray-700">{STUDIYA.adres}</p>
                  <p className="text-sm text-gray-600 mt-1">{STUDIYA.ohvat}</p>
                </div>
              </div>
            </div>

            {/* Форма */}
            <div>
              <h2 className="text-2xl font-bold mb-8 text-gray-900" id="zayavka">
                Оставить заявку
              </h2>
              <FormWithConsent />
              <p className="text-sm text-gray-600 mt-6 text-center">
                Мы никогда не спамим и не передаём данные третьим лицам.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Часто спрашивают</h2>
          <div className="space-y-6">
            {[
              {
                q: 'Сколько стоит обсудить идею?',
                a: 'Бесплатно. Первая консультация — без обязательств. Послушаем вас, покажем примеры, обсудим сроки и бюджет.',
              },
              {
                q: 'Какой срок разработки?',
                a: 'Зависит от сложности. Лендинг — 3–5 дней, сайт — 2–3 недели, сложное приложение — месяц.',
              },
              {
                q: 'Можно ли редактировать сайт самому?',
                a: 'Да. Код остаётся у вас. Либо обучим команду, либо оставим админ-панель для правок.',
              },
              {
                q: 'Что если нужны доработки после запуска?',
                a: 'Бесплатные правки в течение двух недель после запуска. Дальнейшие доработки по почасовой ставке.',
              },
              {
                q: 'Работаете ли вы удалённо?',
                a: 'Да. Большинство проектов делаем по интернету. Встречаемся онлайн на созвонах.',
              },
            ].map((item, i) => (
              <details key={i} className="group bg-white p-6 rounded-lg cursor-pointer border border-gray-200">
                <summary className="font-bold text-gray-900 flex justify-between items-center">
                  {item.q}
                  <span className="group-open:rotate-180 transition">▼</span>
                </summary>
                <p className="text-gray-600 mt-4">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* Back to home */}
      <section className="py-8 px-4 text-center">
        <Link href="/" className="text-gray-900 hover:text-red-600 font-semibold">
          ← Вернуться на главную
        </Link>
      </section>
    </div>
  );
}
