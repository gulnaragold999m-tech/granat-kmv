/* Приём заявки с формы.

   ЧТО БЫЛО ДО 15.08.2026. Обработчик писал заявку в `console.log`
   и отвечал «Заявка получена». Человек видел зелёную надпись «Мы
   свяжемся с вами в течение часа», а заявка не уходила никуда:
   в логе Amvera её никто не читает, а лог живёт до перезапуска.
   Пока на сайте висел Telegram, часть людей писала туда и заявки
   доходили. Telegram с сайта снят — значит форма обязана доставлять.

   КУДА УХОДИТ ТЕПЕРЬ. На почту, через SMTP Яндекса. Письмо остаётся
   в ящике, его видно с телефона и с компьютера, его можно переслать.

   ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (Amvera → Настройки → Переменные окружения):
     MAIL_TO    — куда слать заявки, можно несколько через запятую
     SMTP_USER  — ящик, ОТ которого уходит письмо (он же логин)
     SMTP_PASS  — пароль ПРИЛОЖЕНИЯ, не основной пароль от почты
     SMTP_HOST  — необязательно, по умолчанию smtp.yandex.ru
     SMTP_PORT  — необязательно, по умолчанию 465

   Пароль приложения заводится тут: id.yandex.ru → Безопасность →
   Пароли приложений → Почта. Он даёт право только отправлять письма
   и отзывается, не трогая основной пароль.

   ПРО ЗАКОН. Ящик на Яндексе — сервер в России, персональные данные
   из заявки границу не пересекают. Поменяете SMTP_HOST на зарубежный —
   это уже трансграничная передача, с уведомлением в Роскомнадзор.

   ПОЧЕМУ НЕ ОТВЕЧАЕМ «ОК», КОГДА НЕ ОТПРАВИЛОСЬ. Заявка, о которой
   человек думает, что она ушла, хуже честной ошибки: он ждёт звонка
   и не звонит сам. Не доставили — говорим об этом и даём телефон. */

import { NextRequest, NextResponse } from 'next/server';
import nodemailer, { type Transporter } from 'nodemailer';
import { STUDIYA } from '../../../data/prices';

const SMTP_HOST = process.env.SMTP_HOST || 'smtp.yandex.ru';
const SMTP_PORT = Number(process.env.SMTP_PORT) || 465;

function pochtaNastroena(): boolean {
  return Boolean(process.env.SMTP_USER && process.env.SMTP_PASS && process.env.MAIL_TO);
}

/* Транспорт создаём один раз: пересоздание на каждую заявку —
   лишнее рукопожатие с почтовым сервером. */
let transport: Transporter | null = null;

function getTransport(): Transporter {
  if (transport) return transport;
  transport = nodemailer.createTransport({
    host: SMTP_HOST,
    port: SMTP_PORT,
    secure: SMTP_PORT === 465,
    auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
    /* Без таймаутов зависший SMTP держит запрос до победного,
       и человек смотрит на крутящуюся кнопку. */
    connectionTimeout: 10000,
    greetingTimeout: 10000,
    socketTimeout: 15000,
  });
  return transport;
}

export async function POST(request: NextRequest) {
  let body: { name?: string; phone?: string; email?: string; consent?: boolean };

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Не удалось прочитать заявку' }, { status: 400 });
  }

  const name = String(body.name || '').trim();
  const phone = String(body.phone || '').trim();
  const email = String(body.email || '').trim();

  if (!name || !phone || !body.consent) {
    return NextResponse.json(
      { error: 'Заполните имя и телефон и подтвердите согласие' },
      { status: 400 },
    );
  }

  const kontaktnyjTelefon = `${STUDIYA.telefon}`;
  const nedostavleno = {
    error: `Заявка не ушла. Позвоните нам: ${kontaktnyjTelefon} — ответим сразу.`,
  };

  if (!pochtaNastroena()) {
    /* Видно в логе Amvera: заявка была, канала доставки не было. */
    console.error('Заявка не доставлена: не заданы SMTP_USER, SMTP_PASS или MAIL_TO', {
      name,
      phone,
    });
    return NextResponse.json(nedostavleno, { status: 503 });
  }

  const tekst = [
    'Заявка с сайта granat-kmv.ru',
    '',
    `Имя: ${name}`,
    `Телефон: ${phone}`,
    `Почта: ${email || 'не указана'}`,
    `Согласие на обработку ПДн: да`,
    `Время: ${new Date().toISOString()}`,
  ].join('\n');

  try {
    await getTransport().sendMail({
      from: process.env.SMTP_USER, // Яндекс отвергает письмо, если From не равен логину
      to: process.env.MAIL_TO,
      replyTo: email || undefined,
      subject: `Заявка с сайта: ${name}, ${phone}`,
      text: tekst,
    });
  } catch (e) {
    console.error('Заявка не доставлена, ошибка почты:', e);
    return NextResponse.json(nedostavleno, { status: 502 });
  }

  return NextResponse.json({ success: true, message: 'Заявка получена' }, { status: 200 });
}
