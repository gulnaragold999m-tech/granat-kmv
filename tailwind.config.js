/** Конфигурация Tailwind — та же, что раньше стояла инлайном в <head>.
 *  Цвета и шрифты студии: их используют классы вида text-ink, bg-primary.
 *  content — где искать классы. Классы встречаются и внутри строк в
 *  JavaScript (симулятор бота собирает разметку через innerHTML), поэтому
 *  сканируем шаблоны целиком, а не только вёрстку. */
module.exports = {
  content: ["./templates/**/*.html", "./*.html", "./static/js/*.js"],
  theme: {
    extend: {
      colors: { primary: '#4A0E17', secondary: '#F9F3EB', accent: '#D4AF37', ink: '#1C1C1C' },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['Montserrat', 'sans-serif'],
      },
    },
  },
};
