# Анимация на чистом CSS — рабочие рецепты

Всё ниже — без библиотек. Проверять после вставки одним и тем же
способом: открыть на телефоне, включить в системе «уменьшить движение»
и убедиться, что движение исчезло, а содержимое осталось.

## Появление блока при прокрутке

Разметка ничего не знает про анимацию — класс вешает наблюдатель.

```css
.poyavlenie {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity .35s cubic-bezier(0.16, 1, 0.3, 1),
              transform .35s cubic-bezier(0.16, 1, 0.3, 1);
}
.poyavlenie.vidno { opacity: 1; transform: none; }

@media (prefers-reduced-motion: reduce) {
  .poyavlenie { opacity: 1; transform: none; transition: none; }
}
```

```js
const nabl = new IntersectionObserver((zapisi) => {
  for (const z of zapisi) {
    if (!z.isIntersecting) continue;
    z.target.classList.add('vidno');
    nabl.unobserve(z.target);      // показали один раз и забыли
  }
}, { rootMargin: '0px 0px -10% 0px' });

document.querySelectorAll('.poyavlenie').forEach(el => nabl.observe(el));
```

Три вещи, из-за которых этот приём чаще всего портит страницу:

- **Анимировать каждый абзац.** Появляться должны блоки, а не строки.
- **Не отписываться.** Без `unobserve` блок мигает при каждой прокрутке
  туда-сюда.
- **Прятать содержимое насовсем.** Если JS не выполнился, `opacity: 0`
  остаётся навсегда и страница пустая. Поэтому класс `.poyavlenie`
  вешать скриптом при старте, а в разметке держать видимое состояние.

## Задержка по очереди

Пять карточек одна за другой. Шаг 60–80 мс: меньше — не читается как
очередь, больше — ожидание.

```css
.karta:nth-child(1) { transition-delay: 0ms; }
.karta:nth-child(2) { transition-delay: 70ms; }
.karta:nth-child(3) { transition-delay: 140ms; }
```

Больше пяти-шести элементов так не делать: последний приедет через
полсекунды после первого, и человек уже прокрутил дальше.

## Кнопка: наведение, нажатие, фокус

Три состояния, а не одно. Фокус — обязательно видимый: по клавиатуре
сайтом пользуются не только незрячие, но и все, у кого сломана мышь.

```css
.knopka {
  transition: transform .15s ease-out, background-color .15s ease-out;
}
.knopka:hover  { transform: translateY(-1px); }
.knopka:active { transform: translateY(0) scale(.98); }
.knopka:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
```

`:focus-visible`, а не `:focus` — иначе рамка вспыхивает и при клике
мышью, и её начинают убирать совсем, ломая доступность.

## Раскрытие блока без прыжка высоты

`height: auto` не анимируется. Два честных пути:

```css
/* 1. современный, короткий */
.skryto { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .3s ease-out; }
.skryto > div { overflow: hidden; }
.skryto.otkryto { grid-template-rows: 1fr; }

/* 2. надёжный: посчитать высоту в JS и записать в max-height */
```

Первый способ работает во всех живых браузерах. Проверять в Safari
на iPhone — там анимация сетки появилась позже остальных.

## Загрузчик

Единственное место, где уместен `linear` и бесконечный повтор.

```css
@keyframes vrashchenie { to { transform: rotate(360deg); } }
.zagruzka { animation: vrashchenie .8s linear infinite; }

@media (prefers-reduced-motion: reduce) {
  .zagruzka { animation: none; }
  .zagruzka::after { content: 'Отправляем…'; }
}
```

При выключенном движении вращение заменяется словами — человек всё
равно должен понимать, что система работает.

## Чего не делать

- **Параллакс на прокрутке через `background-position` или `top`.**
  Дёргается везде, кроме десктопа разработчика. Если очень нужно —
  `transform: translate3d()` и только на десктопе.
- **Анимировать появление шапки при прокрутке вверх** на телефоне:
  шапка мельтешит при каждом касании.
- **Печатающийся текст** на первом экране. Заголовок должен быть виден
  сразу — его читает и человек, и поисковый робот.
- **Автопрокрутку карусели** быстрее семи секунд. И обязательно пауза
  при наведении и при фокусе.
