import Link from "next/link";

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
            Печать приглашений, сертификатов, визиток. Сайты, Telegram-боты и
            автоматизация. Ваш бизнес запомнят с первого взгляда.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/pechat"
              className="px-8 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-semibold"
            >
              Полиграфия и дизайн
            </Link>
            <Link
              href="/cifra"
              className="px-8 py-3 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition font-semibold"
            >
              Сайты и боты
            </Link>
          </div>
        </div>
      </section>

      {/* Почему клиенты уходят */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-6">Почему клиенты уходят к другим</h2>
          <div className="bg-gray-100 p-8 rounded-lg mb-8">
            <p className="text-lg text-gray-700 mb-4">
              Логотип «на коленке» и сайт из 2010-го убивают доверие ещё до
              разговора.
            </p>
            <p className="text-gray-600">
              Клиенту хватает пары секунд, чтобы решить: серьёзный вы бизнес —
              или «ещё один такой же». Слабая упаковка — и он уходит к тому,
              кто выглядит дороже. Даже если ваш продукт
              лучше.
            </p>
          </div>
        </div>
      </section>

      {/* Выгода в цифрах */}
      <section className="py-16 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Что вы получаете на деле</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="bg-white p-6 rounded-lg">
              <div className="text-3xl font-bold text-red-600 mb-2">2 сек.</div>
              <p className="text-gray-600">столько нужно клиенту, чтобы решить — доверять вам</p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <div className="text-3xl font-bold text-red-600 mb-2">350 г/м²</div>
              <p className="text-gray-600">плотная дизайнерская бумага — премиум в руке</p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <div className="text-3xl font-bold text-red-600 mb-2">5–7 дней</div>
              <p className="text-gray-600">от идеи до готового изделия или сайта</p>
            </div>
            <div className="bg-white p-6 rounded-lg">
              <div className="text-3xl font-bold text-red-600 mb-2">1 студия</div>
              <p className="text-gray-600">печать и код — без пяти подрядчиков</p>
            </div>
          </div>
        </div>
      </section>

      {/* Услуги */}
      <section className="py-16 px-4 bg-white">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold mb-12 text-center">Услуги</h2>
          <div className="grid md:grid-cols-2 gap-8">
            <Link
              href="/pechat"
              className="bg-gradient-to-br from-red-50 to-red-100 p-8 rounded-lg hover:shadow-lg transition"
            >
              <h3 className="text-2xl font-bold mb-4 text-gray-900">Печать и полиграфия</h3>
              <p className="text-gray-600 mb-4">
                Приглашения, сертификаты, визитки с тиснением золотом, плоттерной резкой и
                премиальными материалами.
              </p>
              <span className="text-red-600 font-semibold">От 200 ₽ →</span>
            </Link>
            <Link
              href="/cifra"
              className="bg-gradient-to-br from-blue-50 to-blue-100 p-8 rounded-lg hover:shadow-lg transition"
            >
              <h3 className="text-2xl font-bold mb-4 text-gray-900">Сайты и боты</h3>
              <p className="text-gray-600 mb-4">
                Лендинги, многостраничные сайты и Telegram-боты кодом, без конструкторов.
              </p>
              <span className="text-blue-600 font-semibold">От 25 000 ₽ →</span>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-4 bg-red-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Пусть вас запомнят</h2>
          <p className="text-lg mb-8">
            Один разговор — и мы покажем примеры и назовём цену.
          </p>
          <Link
            href="/kontakty#zayavka"
            className="inline-block px-8 py-3 bg-white text-red-600 rounded-lg hover:bg-gray-100 transition font-semibold"
          >
            Оставить заявку
          </Link>
        </div>
      </section>
    </div>
  );
}
