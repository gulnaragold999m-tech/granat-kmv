# Гранат — Типография и веб-студия

Многостраничный сайт студии Гранат на Next.js с поддержкой печати, сайтов и Telegram-ботов.

## Структура проекта

```
app/
├── page.tsx              # Главная
├── pechat/page.tsx       # Печать и полиграфия
├── cifra/page.tsx        # Сайты и боты
├── portfolio/page.tsx    # Портфолио
├── o-nas/page.tsx        # О студии
├── kontakty/page.tsx     # Контакты и форма
└── layout.tsx            # Главный лейаут с навигацией
```

## Стек

- **Frontend:** React 19, Next.js, Tailwind CSS
- **Хостинг:** Amvera
- **Язык:** TypeScript

## Установка

```bash
npm install
npm run dev
```

Сайт откроется на http://localhost:3000

## Переменные окружения

Скопируй `.env.example` в `.env.local` и заполни токены:

```bash
cp .env.example .env.local
```

⚠️ **ВАЖНО:** Никогда не коммить `.env.local` с токенами! Используй `.env.example` как шаблон.

## Деплой на Amvera

1. Создай аккаунт на https://amvera.ru
2. Подключи GitHub репо
3. Выбери ветку main
4. Укажи команду запуска: `npm install && npm run build && npm start`
5. Добавь переменные окружения в Amvera

## Команды

- `npm run dev` — разработка
- `npm run build` — сборка для продакшена
- `npm start` — запуск продакшена
- `npm run lint` — проверка кода

## Ссылки

- **Сайт:** https://granat-kmv.ru
- **Telegram:** @GranatJarvis_bot
- **Email:** gulnaravibecoder999@yandex.ru

---

© 2026 ИП Мелконян Г.Р. · Студия ГРАНАТ
