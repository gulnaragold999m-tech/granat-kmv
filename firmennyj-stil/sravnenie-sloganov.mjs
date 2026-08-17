import { svg, risovat } from './sobrat.mjs';
import { writeFileSync, unlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const VARIANTY = [
  ['А', 'ВАШ БИЗНЕС ЗАПОМНЯТ С ПЕРВОГО ВЗГЛЯДА', 40],
  ['Б', 'ЛЕРМОНТОВ · КМВ', 62],
  ['В', 'ПЕЧАТЬ · ДИЗАЙН · РЕКЛАМА', 52],
  ['Г', 'ПЕЧАТЬ ОТ ОДНОЙ ШТУКИ', 56],
];

let kartochki = '';
for (const [bukva, slogan, kegl] of VARIANTY) {
  const imya = `_var-${bukva}.svg`;
  writeFileSync(imya, svg({ sVenzelem: true, slogan, keglSlogana: kegl }));
  kartochki += `<figure><img src="${imya}"><figcaption>${bukva}. ${slogan}</figcaption></figure>`;
}

writeFileSync('_sheet.html', `<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;background:#12060a;width:1500px;height:1640px;overflow:hidden;
  font-family:sans-serif}
 .g{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:18px}
 figure{margin:0} img{display:block;width:714px;height:714px}
 figcaption{color:#E2C87A;font-size:19px;padding:9px 2px;letter-spacing:.04em}</style>
<div class="g">${kartochki}</div>`);

execFileSync('/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',
  ['--disable-gpu','--no-sandbox','--hide-scrollbars','--force-device-scale-factor=1',
   '--window-size=1500,1640','--screenshot=varianty-slogana.png',
   `file://${process.cwd()}/_sheet.html`], {stdio:'ignore'});
unlinkSync('_sheet.html');
for (const [b] of VARIANTY) unlinkSync(`_var-${b}.svg`);
console.log('готово: varianty-slogana.png');
