import FormWithConsent from '../FormWithConsent';
import Link from 'next/link';

export const metadata = {
  title: 'Печать и полиграфия — от 200 ₽ | Гранат',
  description: 'Приглашения, сертификаты, визитки с тиснением золотом. Премиальные материалы, дизайн, быстрая печать в Лермонтове.',
};

export default function Pechat() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-b from-red-50 to-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900">
            Печать и полиграфия
          </h1>
          <p className="text-xl text-gray-600 mb-6">
            Приглашения, сертификаты, визитки, буклеты, стикеры с премиальными материалами.
            Тиснение золотом, плоттерная резка, 5–7 дней до готовности.
          </p>
          <div className="flex flex-wrap gap-4">
            <span className="text-2xl font-bold text-red-600">От 200 ₽</span>
            <span className="text-lg text-gray-600">Срок: 5–7 дней</span>
          </div>
        </div>
      </section>

      {/* Услуги */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Что мы печатаем</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { title: 'Визитки', price: '200–500 ₽', desc: 'Матовая, глянцевая, фактурная бумага. Разные форматы.' },
              { title: 'Приглашения', price: '500–2000 ₽', desc: 'На свадьбы, корпративы, события. Авторский дизайн.' },
              { title: 'Сертификаты', price: '300–1500 ₽', desc: 'Для награждений, благодарностей. Конгрев, тиснение.' },
              { title: 'Буклеты', price: '1000–5000 ₽', desc: 'Трёхсложные, разворотные. Глянцевая или матовая бумага.' },
              { title: 'Стикеры', price: '100–500 ₽', desc: 'Наклейки на любой материал. Виниловые, ПВХ, бумажные.' },
              { title: 'Фирменный стиль', price: '5000–15000 ₽', desc: 'Логотип, лого на всё. Гайдлайны и комплект.' },
            ].map((service, i) => (
              <div key={i} className="bg-red-50 p-6 rounded-lg border border-red-200">
                <h3 className="text-xl font-bold mb-2 text-gray-900">{service.title}</h3>
                <p className="text-gray-600 mb-4">{service.desc}</p>
                <p className="text-lg font-semibold text-red-600">{service.price}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Материалы */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">Материалы и эффекты</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-bold mb-4 text-gray-900">Бумага</h3>
              <ul className="space-y-2 text-gray-700">
                <li>• Премиум 350 г/м² (фактурная, дизайнерская)</li>
                <li>• Стандарт 250 г/м²</li>
                <li>• Крафт, гофрокартон, картон</li>
                <li>• Матовые и глянцевые покрытия</li>
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-bold mb-4 text-gray-900">Эффекты</h3>
              <ul className="space-y-2 text-gray-700">
                <li>• Тиснение золотом/серебром/медью</li>
                <li>• Конгрев (выпуклые элементы)</li>
                <li>• УФ-лак (блеск на части дизайна)</li>
                <li>• Плоттерная резка по контуру</li>
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
              { num: '1', title: 'Встреча', desc: 'Обсудим идею, выберем материал и эффекты.' },
              { num: '2', title: 'Дизайн', desc: 'Макет на согласование (или вы приносите свой).' },
              { num: '3', title: 'Подготовка', desc: 'Настройка для печати, пробный оттиск.' },
              { num: '4', title: 'Печать', desc: 'Производство тиража, отделка (конгрев, тиснение).' },
            ].map((step, i) => (
              <div key={i} className="flex gap-4">
                <div className="w-10 h-10 bg-red-600 text-white rounded-full flex items-center justify-center font-bold flex-shrink-0">
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
      <section className="py-16 px-4 bg-red-50">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">Обсудим ваш проект?</h2>
          <FormWithConsent />
          <p className="text-center text-sm text-gray-600 mt-6">
            Или позвоните:{' '}
            <a href="tel:+79992449999" className="text-red-600 hover:underline font-semibold">
              +7 999 244 9999
            </a>
          </p>
        </div>
      </section>

      {/* Back to home */}
      <section className="py-8 px-4 text-center">
        <Link href="/" className="text-red-600 hover:underline font-semibold">
          ← Вернуться на главную
        </Link>
      </section>
    </div>
  );
}
