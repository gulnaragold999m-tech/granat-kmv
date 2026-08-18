# Минимальная сцена без сборщика

Способ, который работает в нашем стеке: статические файлы, никакого
npm-сборщика фронтенда, ничего с чужих CDN.

## Файлы

```
zhivoj-sajt/static/js/vendor/three.module.js        ядро
zhivoj-sajt/static/js/vendor/jsm/                   загрузчики и контролы (если нужны)
zhivoj-sajt/static/3d/model.glb                     модель, сжатая
zhivoj-sajt/static/3d/model-fallback.webp           кадр из этой же сцены
```

Скачивается с официального сайта или из релиза на GitHub, кладётся
руками. **Версию записать в комментарии** рядом с подключением: через
полгода примеры из интернета будут от другой версии, и без этой строчки
не понять, почему они не работают.

## Подключение через importmap

```html
<script type="importmap">
{
  "imports": {
    "three": "/static/js/vendor/three.module.js",
    "three/addons/": "/static/js/vendor/jsm/"
  }
}
</script>
<script type="module" src="/static/js/scena.js"></script>
```

`importmap` понимают все живые браузеры. Старые просто не выполнят
модуль — и покажут запасную картинку, что нам и нужно.

## Разметка: картинка первой, сцена вторая

```html
<div class="scena" data-scena>
  <img class="scena-zapas" src="/static/3d/model-fallback.webp"
       alt="Кресло «Гранат», вид три четверти" width="960" height="640" loading="lazy">
  <canvas class="scena-holst" hidden></canvas>
</div>
```

Картинка стоит в разметке **всегда**. Сцена, когда поднимется, покажет
холст и спрячет картинку. Так страница цела при любом сбое, а место
под сцену зарезервировано — верстка не прыгает.

## Скелет `scena.js`

```js
import * as THREE from 'three';

const korobka = document.querySelector('[data-scena]');

// ── причины вообще не запускать 3D ───────────────────────────────
const tiho   = matchMedia('(prefers-reduced-motion: reduce)').matches;
const ekonom = navigator.connection?.saveData === true;
const slabo  = (navigator.hardwareConcurrency ?? 4) <= 4 ||
               (navigator.deviceMemory ?? 4) <= 4;
const estWebGL = (() => {
  try { return !!document.createElement('canvas').getContext('webgl2'); }
  catch { return false; }
})();

// Ни одной причины не должно совпасть — иначе в разметке остаётся
// картинка, и это и есть запасной вариант. Обычный `return` здесь
// не годится: файл подключён как модуль, а на верхнем уровне модуля
// возврата нет — будет синтаксическая ошибка и не выполнится ничего.
const mozhno = korobka && !tiho && !ekonom && !slabo && estWebGL;

if (mozhno) {
  // ── сцена поднимается только когда подошла к экрану ────────────
  const nabl = new IntersectionObserver(([z]) => {
    if (!z.isIntersecting) return;
    nabl.disconnect();
    podnyat();
  }, { rootMargin: '200px' });
  nabl.observe(korobka);
}

function podnyat() {
  const holst = korobka.querySelector('.scena-holst');
  const renderer = new THREE.WebGLRenderer({ canvas: holst, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));   // выше двух смысла нет, цена — вчетверо
  renderer.setSize(korobka.clientWidth, korobka.clientHeight, false);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, korobka.clientWidth / korobka.clientHeight, .1, 100);
  camera.position.set(0, .6, 3);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.2));

  const kub = new THREE.Mesh(
    new THREE.BoxGeometry(1, 1, 1),
    new THREE.MeshStandardMaterial({ color: 0x00f0ff, roughness: .4 }),
  );
  scene.add(kub);

  holst.hidden = false;
  korobka.querySelector('.scena-zapas').hidden = true;

  // ── цикл, который умеет останавливаться ─────────────────────────
  let idet = true, kadr = 0;
  const risovat = () => {
    if (!idet) return;
    kub.rotation.y += .005;
    renderer.render(scene, camera);
    kadr = requestAnimationFrame(risovat);
  };
  const start = () => { if (!idet) { idet = true; risovat(); } };
  const stop  = () => { idet = false; cancelAnimationFrame(kadr); };

  document.addEventListener('visibilitychange', () => document.hidden ? stop() : start());
  new IntersectionObserver(([z]) => z.isIntersecting ? start() : stop()).observe(korobka);

  addEventListener('resize', () => {
    renderer.setSize(korobka.clientWidth, korobka.clientHeight, false);
    camera.aspect = korobka.clientWidth / korobka.clientHeight;
    camera.updateProjectionMatrix();
  }, { passive: true });

  risovat();
}
```

Что здесь главное и переносится в любую сцену:

- **Четыре причины не запускаться** проверяются до создания рендерера.
- **Ленивый подъём** — сцена не грузится, пока не подошла.
- **Останов при уходе с экрана и при скрытой вкладке** — иначе телефон
  греется, пока человек читает следующую секцию.
- **Ограничение `pixelRatio`** — самая дешёвая оптимизация из всех.
- Картинка прячется **после** успешного подъёма, а не до.

## Модель вместо кубика

Загрузчик `GLTFLoader` из `three/addons/`. Что помнить:

- **`.glb`, а не `.gltf` с отдельными файлами** — один запрос вместо
  десяти.
- **Сжимать геометрию** (Draco или meshopt) и текстуры (KTX2). Разница
  бывает в разы, и это единственный способ уложиться в разумный вес.
- **Освобождать память**, если сцена уходит: `geometry.dispose()`,
  `material.dispose()`, `renderer.dispose()`. Без этого при переходах
  по страницам память течёт.
- **API Three.js смотреть в справочнике `threejs.org/docs`** под свою
  версию, а не по памяти и не по статье трёхлетней давности:
  имена и сигнатуры меняются от релиза к релизу.
