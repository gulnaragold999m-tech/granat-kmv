/* ============================================================
   ЦЕЛИ ЯНДЕКС.МЕТРИКИ — granat-kmv.ru (Flask + HTML)
   Счётчик: 110961373

   ВАЖНО: сам счётчик здесь НЕ подключается — он уже стоит в <head>.
   Этот файл только добавляет цели и разбивку по разделам.
   Второй раз счётчик не инициализировать: будут двойные визиты.

   Подключён в templates/base.html перед </body> — значит работает на всех
   страницах сразу. url_for здесь не используется: static_folder у приложения
   равен корню проекта, и url_for('static', ...) дал бы /js/..., а файл лежит
   в /static/js/. Поэтому в шаблоне стоит прямой путь.
   ============================================================ */
(function () {
  'use strict';

  var COUNTER_ID = 110961373;

  /* --- Безопасный вызов: не падаем, если счётчик заблокирован --- */
  function ymCall() {
    if (typeof window.ym !== 'function') return;
    var args = [COUNTER_ID].concat(Array.prototype.slice.call(arguments));
    try { window.ym.apply(null, args); } catch (e) {}
  }

  function goal(name, params) {
    if (!name) return;
    ymCall('reachGoal', name, params || {});
  }

  /* Доступно из любого скрипта на сайте: window.granatGoal('lead_form') */
  window.granatGoal = goal;

  /* --- Раздел сайта --------------------------------------------
     Берётся из адреса: /pechat/vizitki → 'pechat'.
     Даёт в отчётах разбивку «полиграфия vs сайты и боты».
     Переопределить вручную: <body data-section="pechat">          */
  var section =
    (document.body && document.body.getAttribute('data-section')) ||
    location.pathname.split('/').filter(Boolean)[0] ||
    'glavnaya';

  ymCall('params', { section: section });

  /* --- Защита от двойной отправки одной цели -------------------- */
  var fired = {};
  function once(name) {
    var now = new Date().getTime();
    if (fired[name] && now - fired[name] < 2000) return false;
    fired[name] = now;
    return true;
  }

  /* --- Цели по кликам ------------------------------------------
     Телефон, WhatsApp, Telegram, почта — автоматически по href.
     Остальное — атрибутом data-goal="имя_цели" в вёрстке.        */
  document.addEventListener('click', function (ev) {
    var node = ev.target;
    if (node && node.nodeType === 3) node = node.parentNode;
    if (!node || !node.closest) return;

    var marked = node.closest('[data-goal]');
    if (marked) {
      var name = marked.getAttribute('data-goal');
      if (name && once(name)) goal(name, { section: section });
    }

    var link = node.closest('a[href]');
    if (!link) return;
    var href = (link.getAttribute('href') || '').toLowerCase();

    if (href.indexOf('tel:') === 0) {
      if (once('call_click')) goal('call_click', { section: section });
    } else if (href.indexOf('wa.me') > -1 || href.indexOf('whatsapp') > -1) {
      if (once('whatsapp_click')) goal('whatsapp_click', { section: section });
    } else if (href.indexOf('t.me') > -1 || href.indexOf('telegram') > -1) {
      if (once('telegram_click')) goal('telegram_click', { section: section });
    } else if (href.indexOf('mailto:') === 0) {
      if (once('email_click')) goal('email_click', { section: section });
    }
  }, true);

  /* --- Формы ---------------------------------------------------
     Цель отправляется только после успешной отправки, не по клику
     по кнопке. Иначе в Метрике будут заявки, которых нет.

     а) Обычная форма с POST и перезагрузкой:
        <form method="post" data-goal-form="lead_form"> ... </form>
        (надёжнее — цель типа «Посещение страниц» на /spasibo,
         она не зависит от JS вообще)

     б) Форма на fetch/AJAX — вызвать вручную в момент успеха:
        window.granatGoal('lead_form', {form: 'kontakty'});        */
  document.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (!form || !form.getAttribute) return;
    var name = form.getAttribute('data-goal-form');
    if (!name) return;
    if (form.checkValidity && !form.checkValidity()) return;
    goal(name, {
      section: section,
      form: form.getAttribute('name') || form.getAttribute('id') || 'no_name'
    });
  }, true);

  /* --- Дочитал страницу до 75% ---------------------------------
     Показывает, доходят ли люди до цены и формы на длинных
     страницах услуг.                                              */
  var scrollDone = false;
  window.addEventListener('scroll', function () {
    if (scrollDone) return;
    var el = document.documentElement;
    var ratio = (el.scrollTop + window.innerHeight) / el.scrollHeight;
    if (ratio >= 0.75) {
      scrollDone = true;
      goal('scroll_75', { section: section });
    }
  }, { passive: true });

  /* --- Кнопка согласия на куки ---------------------------------
     Баннер на сайте уже есть. Чтобы видеть, сколько людей его
     принимает, добавить на кнопку атрибут data-goal="cookie_accept" —
     отдельный код не нужен, она поймается блоком выше.            */
})();
