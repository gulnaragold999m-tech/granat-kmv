import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { STUDIYA } from "../data/prices";

export const metadata: Metadata = {
  title: "Гранат — типография и веб-студия в Лермонтове",
  description:
    "Фото на документы, печать фотографий, копии, флаеры, буклеты, открытки и приглашения, чертежи, ламинация. Сайты и чат-боты. Студия «Гранат» в Лермонтове, работаем по всему КМВ.",
  metadataBase: new URL("https://granat-kmv.ru"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <meta charSet="utf-8" />
        <meta name="yandex-verification" content="4cb0c6f73fcadb40" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body className="bg-white text-gray-900 flex flex-col min-h-screen">
        {/* Навигация */}
        <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link href="/" className="text-2xl font-bold text-red-600">
                Гранат
              </Link>
              <div className="hidden md:flex space-x-8 text-sm">
                <Link href="/pechat" className="hover:text-red-600 transition">
                  Печать
                </Link>
                <Link href="/cifra" className="hover:text-red-600 transition">
                  Сайты и боты
                </Link>
                <Link href="/kontakty" className="hover:text-red-600 transition">
                  Контакты
                </Link>
              </div>
              <Link
                href="/kontakty#zayavka"
                className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition text-sm"
              >
                Заявка
              </Link>
            </div>
          </div>
        </nav>

        {/* Контент */}
        <main className="flex-grow">{children}</main>

        {/* Футер */}
        <footer className="bg-gray-900 text-white py-12 mt-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-8 mb-8">
              <div>
                <h3 className="text-xl font-bold mb-4">Гранат</h3>
                <p className="text-gray-400 text-sm">
                  Типография и дизайн-студия премиум-полиграфии и цифровых
                  решений. Печать и код под одной крышей.
                </p>
              </div>
              <div>
                <h4 className="font-bold mb-4">География</h4>
                <p className="text-gray-400 text-sm">
                  Лермонтов, Пятигорск, Ессентуки, Кисловодск, Минеральные
                  Воды, Железноводск и весь КМВ.
                </p>
              </div>
              <div>
                {/* Контакты берутся из прайса: адрес и часы работы напечатаны
                    на бумаге, которую клиент держит в руках, и разойтись
                    с сайтом не должны. Telegram убран 15.08.2026 — он больше
                    не канал для заявок. */}
                <h4 className="font-bold mb-4">Контакты</h4>
                <p className="text-gray-400 text-sm">
                  <a href={`tel:${STUDIYA.telefonSsylka}`} className="hover:text-white">
                    {STUDIYA.telefon}
                  </a>
                  <br />
                  <a
                    href={`https://wa.me/${STUDIYA.telefonSsylka.replace("+", "")}`}
                    className="hover:text-white"
                  >
                    Написать в WhatsApp
                  </a>
                  <br />
                  <a
                    href="mailto:gulnaravibecoder999@yandex.ru"
                    className="hover:text-white"
                  >
                    gulnaravibecoder999@yandex.ru
                  </a>
                  <br />
                  {STUDIYA.adres}
                  <br />
                  {STUDIYA.chasy}
                </p>
              </div>
            </div>
            <div className="border-t border-gray-700 pt-8 text-center text-gray-400 text-sm">
              <p>© 2026 ИП Мелконян Г.Р. · Студия ГРАНАТ · ИНН 490600091128</p>
              <div className="mt-4 space-x-4">
                <Link href="/privacy" className="hover:text-white">
                  Политика конфиденциальности
                </Link>
                |
                <Link href="/consent" className="hover:text-white">
                  Согласие на обработку ПДн
                </Link>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
