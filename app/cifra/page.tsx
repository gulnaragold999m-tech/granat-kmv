import FormWithConsent from '../FormWithConsent';
import Link from 'next/link';

export const metadata = {
  title: 'Сайты и Telegram-боты — от 25 000 ₽ | Гранат',
  description: 'Лендинги, многостраничные сайты и Telegram-боты. Next.js, React, быстрая загрузка, SEO. От 25 000 ₽.',
};

export default function Cifra() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-b from-blue-50 to-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900">
            Сайты и Telegram-боты
          </h1>
          <p className="text-xl text-gray-600 mb-6">
            Лендинги, многостраничные сайты и боты кодом. Быстрая загрузка, SEO-оптимизация,
            интеграции с CRM и платёжными системами. Исходники остаются у вас.
          </p>
          <div className="flex flex-wrap gap-4">
            <span className="text-2xl font-bold text-blue-600">От 25 000 ₽</span>
            <span className="text-lg text-gray-600">Срок: 5–14 дней</span>
          </div>
        </div>
      </section>

      {/* Услуги */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Что мы делаем</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              {
                title: 'Лендинги',
                desc: 'Одностраничные продающие сайты. Быстрая загрузка, мобильная оптимизация, интеграция с аналитикой.',
                price: '25 000–50 000 ₽',
              },
              {
                title: 'Многостраничные сайты',
                desc: 'Корпоративные сайты, портфолио, каталоги. SEO-структура, быстрая загрузка, админ-панель.',
                price: '50 000–150 000 ₽',
              },
              {
                title: 'Telegram-боты',
                desc: 'Боты для приёма заявок, рассылок, поддержки. Интеграция с CRM, Яндекс.Метрикой, уведомления.',
                price: '15 000–50 000 ₽',
              },
              {
                title: 'Web-приложения',
                desc: 'Интерактивные приложения, системы управления, калькуляторы. Работают на всех устройствах.',
                price: '100 000–300 000 ₽',
              },
              {
                title: 'Интеграции',
                desc: 'Подключение CRM, платёжных систем, API, Яндекс.Карты, Google Sheets, n8n, Zapier.',
                price: '5 000–30 000 ₽',
              },
              {
                title: 'SEO-оптимизация',
                desc: 'Техническая SEO, структура сайта, метатеги, микроразметка, sitemap.xml.',
                price: '15 000–40 000 ₽',
              },
            ].map((service, i) => (
              <div key={i} className="bg-blue-50 p-6 rounded-lg border border-blue-200">
                <h3 className="text-xl font-bold mb-3 text-gray-900">{service.title}</h3>
                <p className="text-gray-600 mb-4">{service.desc}</p>
                <p className="text-lg font-semibold text-blue-600">{service.price}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Технологии */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">На чём мы пишем</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4 text-gray-900">Frontend</h3>
              <ul className="space-y-2 text-gray-700">
                <li>• React / Next.js (быстрые, SEO-friendly)</li>
                <li>• Tailwind CSS (стили без лишних файлов)</li>
                <li>• TypeScript (безопасный код)</li>
                <li>• PWA (работает и без интернета)</li>
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-bold mb-4 text-gray-900">Backend & Интеграции</h3>
              <ul className="space-y-2 text-gray-700">
                <li>• Node.js / Express (серверная часть)</li>
                <li>• PostgreSQL / MongoDB (базы данных)</li>
                <li>• Telegram API (боты)</li>
                <li>• CRM: Airtable, 1C, Битрикс</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Процесс */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Как мы работаем</h2>
          <div className="space-y-6">
            {[
              { num: '1', title: 'Встреча', desc: 'Обсудим идею, цели и бюджет. Покажем примеры.' },
              { num: '2', title: 'Смета', desc: 'Детальная смета с разбором по задачам и срокам.' },
              { num: '3', title: 'Дизайн', desc: 'Макет на согласование (если нужен).' },
              { num: '4', title: 'Разработка', desc: 'Пишем код, интегрируем, тестируем.' },
              { num: '5', title: 'Тестирование', desc: 'Проверка на всех устройствах и браузерах.' },
              { num: '6', title: 'Запуск', desc: 'Деплой на сервер, настройка домена, аналитика.' },
            ].map((step, i) => (
              <div key={i} className="flex gap-4">
                <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold flex-shrink-0">
                  {step.num}
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{step.title}</h3>
                  <p className="text-gray-600 text-sm">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 bg-blue-50">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">Обсудим ваш проект?</h2>
          <FormWithConsent />
          <p className="text-center text-sm text-gray-600 mt-6">
            Или позвоните:{' '}
            <a href="tel:+79992449999" className="text-blue-600 hover:underline font-semibold">
              +7 999 244 9999
            </a>
          </p>
        </div>
      </section>

      {/* Back to home */}
      <section className="py-8 px-4 text-center">
        <Link href="/" className="text-blue-600 hover:underline font-semibold">
          ← Вернуться на главную
        </Link>
      </section>
    </div>
  );
}
