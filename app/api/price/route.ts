/* Прайс для бота — и для любого другого канала, который спросит цену.

   ЗАЧЕМ ЭТО НУЖНО. Правило владелицы: «Мы можем подправить прайс
   на сайте и забыть про бота. Это должно быть автоматическое
   обновление». Бот студии «Гранат» живёт отдельным приложением
   на Amvera, и если вписать прайс ему в промпт руками, то при первой же
   правке цены сайт и бот разойдутся. Здесь бот берёт прайс по адресу,
   и правка в `data/prices.ts` доезжает до него сама.

   Как пользоваться:
     GET /api/price            прайс простым текстом — прямо в промпт боту
     GET /api/price?format=json  то же самое разобранным по разделам

   Отдаём без авторизации нарочно: это публичная цена, она и так
   напечатана на бумаге и лежит на странице /pechat. */

import { NextRequest, NextResponse } from 'next/server';
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
  NET_V_PRAJSE,
  prajsTekstom,
} from '../../../data/prices';

/* Кэш на час: прайс меняется правкой файла и выкаткой, а не в рантайме.
   Бот может опрашивать адрес хоть на каждое сообщение. */
export const revalidate = 3600;

export async function GET(request: NextRequest) {
  const format = request.nextUrl.searchParams.get('format');

  if (format === 'json') {
    return NextResponse.json({
      studiya: STUDIYA,
      istochnik: ISTOCHNIK,
      fotoNaDokumenty: FOTO_NA_DOKUMENTY,
      razdely: RAZDELY,
      nacenkaZaPlotnost: NACENKA_ZA_PLOTNOST,
      priglashenieIndividualnoe: PRIGLASHENIE_INDIVIDUALNOE,
      materialIOtdelka: MATERIAL_I_OTDELKA,
      rabotaSMaketom: RABOTA_S_MAKETOM,
      kakSchitaem: KAK_SCHITAEM,
      zaklyuchenie: ZAKLYUCHENIE,
      netVPrajse: NET_V_PRAJSE,
    });
  }

  return new NextResponse(prajsTekstom(), {
    status: 200,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
