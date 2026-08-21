# -*- coding: utf-8 -*-
"""Контроль исполнения: что обещано в журнале и до сих пор не закрыто.

   Запуск:  npm run kontrol

   ЗАЧЕМ. 21.08.2026 в журнале лежало 182 незакрытых пункта `- [ ]`,
   из них 41 — в записях последней недели. Их никто не перечитывает:
   журнал пишется сверху вниз, а хвост остаётся внизу и уходит
   из поля зрения на следующий же день.

   Правило владелицы: галочка `[x]` ставится не когда код написан,
   а когда результат виден. Значит, между «сделали» и «работает»
   всегда есть разрыв, и кто-то обязан его называть вслух.
   Роль описана в roli/kontroler.md, данные ей даёт этот скрипт.

   ЧТО ЭТО ДЕЛАЕТ. Достаёт каждый `- [ ]`, привязывает к дате записи,
   в которой он стоит, и показывает: сколько дней висит и сколько раз
   обещан. Ничего не меняет и ничего не закрывает.

   ЧЕГО ЭТО НЕ ДЕЛАЕТ. Не знает, сделана ли задача на самом деле:
   человек мог сделать и не поставить галочку. Не отличает задачу
   для владелицы от задачи для кода. Не ходит на живой сайт.
"""

import os
import re
import sys
from datetime import date

KORNI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEGODNYA = date.today()

MESYACY = {
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
    'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12,
}


def data_iz_zagolovka(stroka):
    """Дата из заголовка записи. В журнале их пишут двумя способами —
       «16.08.2026 — ...» и «18 августа», — потому что писали разные
       беседы в разные дни. Понимаем оба, иначе половина хвостов
       останется без даты."""
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', stroka)
    if m:
        d, mm, g = (int(x) for x in m.groups())
        try:
            return date(g, mm, d)
        except ValueError:
            return None
    m = re.search(r'(\d{1,2})\s+(' + '|'.join(MESYACY) + r')', stroka)
    if m:
        d, nazv = int(m.group(1)), m.group(2)
        # Года в такой записи нет. Берём текущий: журнал ведётся
        # третью неделю, прошлогодних записей в нём быть не может.
        try:
            return date(SEGODNYA.year, MESYACY[nazv], d)
        except ValueError:
            return None
    return None


def sobrat(put):
    """Каждый `- [ ]` с датой ближайшего заголовка ВЫШЕ него."""
    with open(put, encoding='utf-8') as f:
        stroki = f.read().split('\n')

    tekushchaya = None
    hvosty = []
    for nomer, s in enumerate(stroki, 1):
        if s.startswith('#'):
            d = data_iz_zagolovka(s)
            if d:
                tekushchaya = d
            continue
        m = re.match(r'^- \[ \] (.+)$', s)
        if m:
            tekst = re.sub(r'\*\*|`', '', m.group(1)).strip()
            hvosty.append({'tekst': tekst, 'data': tekushchaya, 'stroka': nomer})
    return hvosty


def klyuch(tekst):
    """Ключ для поиска повторов: первые слова без знаков и регистра.
       Один и тот же хвост переписывают разными словами, но начало
       у него обычно совпадает."""
    t = re.sub(r'[^\w\s]', ' ', tekst.lower())
    return ' '.join(t.split()[:6])


def vozrast(h):
    return (SEGODNYA - h['data']).days if h['data'] else None


def main():
    put = os.path.join(KORNI, 'TASKS.md')
    if not os.path.exists(put):
        print('TASKS.md не найден. Контроль невозможен.')
        return 1

    hvosty = sobrat(put)
    print('\nКОНТРОЛЬ ИСПОЛНЕНИЯ · %s' % SEGODNYA.strftime('%d.%m.%Y'))
    print('Источник: TASKS.md, пункты `- [ ]`. Скрипт ничего не закрывает.\n')
    print('Всего незакрытых пунктов: %d' % len(hvosty))

    bez_daty = [h for h in hvosty if not h['data']]
    s_datoj = [h for h in hvosty if h['data']]

    # ── Повторы. РАЗНЫЕ ДНИ и ОДИН ДЕНЬ — это два разных диагноза,
    #    и первая версия скрипта их путала: она показала семь пунктов
    #    «обещано трижды», а все три раза были 20.08 — один и тот же
    #    хвост, переписанный дважды в одной записи. Это неаккуратность
    #    журнала, а не сорванное обещание. Считаем по числу РАЗНЫХ дат.
    gruppy = {}
    for h in hvosty:
        gruppy.setdefault(klyuch(h['tekst']), []).append(h)

    perenesennye = []   # обещано в разные дни — обещание сорвано
    dublikaty = []      # повтор внутри одного дня — журнал написан дважды
    for g in gruppy.values():
        if len(g) < 2:
            continue
        daty = sorted({h['data'] for h in g if h['data']})
        (perenesennye if len(daty) > 1 else dublikaty).append((g, daty))
    perenesennye.sort(key=lambda x: -len(x[1]))

    if perenesennye:
        print('\n\nПЕРЕНЕСЕНО С ДРУГОГО ДНЯ — %d пункт(ов)' % len(perenesennye))
        print('Один и тот же пункт заведён заново в новой записи.')
        print('Значит, задача не забыта, а не делается. Прежде чем')
        print('обещать снова, надо назвать причину.\n')
        for g, daty in perenesennye[:10]:
            print('  %d дн. · %s' % (len(daty), g[0]['tekst'][:88]))
            print('        обещано: %s' % ', '.join(d.strftime('%d.%m') for d in daty))
    else:
        print('\n\nПЕРЕНЕСЁННЫХ С ДРУГОГО ДНЯ НЕТ.')
        print('Ни один пункт не заводился заново в следующей записи.')

    if dublikaty:
        print('\n\nПОВТОР ВНУТРИ ОДНОГО ДНЯ: %d пункт(ов)' % len(dublikaty))
        print('Это не сорванный срок, а журнал, записанный дважды')
        print('за одну беседу. Лечится вычиткой, а не работой.')
        for g, daty in dublikaty[:6]:
            print('  %d× · %s' % (len(g), g[0]['tekst'][:88]))

    # ── Самые старые. Возраст считается от даты записи, а не от того,
    #    когда о хвосте вспомнили в последний раз.
    starye = sorted(s_datoj, key=lambda h: h['data'])
    if starye:
        print('\n\nСАМЫЕ СТАРЫЕ — 15 из %d датированных' % len(s_datoj))
        print('Возраст — сколько дней прошло с записи, где пункт заведён.\n')
        for h in starye[:15]:
            print('  %3d дн. · %s · %s' % (vozrast(h), h['data'].strftime('%d.%m'), h['tekst'][:88]))

    # ── Разбивка по возрасту: она отвечает на вопрос «мы копим или разгребаем».
    if s_datoj:
        vedra = {'старше 7 дней': 0, '3–7 дней': 0, 'моложе 3 дней': 0}
        for h in s_datoj:
            v = vozrast(h)
            if v > 7:
                vedra['старше 7 дней'] += 1
            elif v >= 3:
                vedra['3–7 дней'] += 1
            else:
                vedra['моложе 3 дней'] += 1
        print('\n\nПО ВОЗРАСТУ')
        for k, v in vedra.items():
            print('  %-16s %d' % (k, v))
        print('\nРастёт верхняя строка — задачи заводятся быстрее, чем закрываются.')

    if bez_daty:
        print('\n\nБЕЗ ДАТЫ: %d пункт(ов)' % len(bez_daty))
        print('Они стоят под заголовками без числа — возраст неизвестен.')
        print('Это не ошибка скрипта, а то, как записан журнал.')

    print('\n\nЧЕГО ЭТОТ СКРИПТ НЕ ЗНАЕТ:')
    print('  · сделана ли задача на самом деле — галочку ставит человек')
    print('  · чья задача: владелицы или кода')
    print('  · виден ли результат на живом сайте — туда он не ходит')
    print('  · закрытые пункты `[x]` он не считает вовсе\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
