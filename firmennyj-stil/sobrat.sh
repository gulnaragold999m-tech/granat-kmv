#!/bin/sh
# Пересобрать PNG из SVG. Запускать из папки firmennyj-stil.
#
# ПОЧЕМУ headless_shell, а не обычный chrome: у chrome окно на 85 точек
# выше области рисования, и снизу картинки остаётся белая полоса.
# У headless_shell окна нет вовсе, снимок совпадает с размером кадра.
CHROME=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell

sdelat() {   # $1 — размер стороны, $2 — имя файла
  cat > _r.html <<HTML
<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;padding:0;width:$1px;height:$1px;overflow:hidden}
img{display:block;width:$1px;height:$1px}</style>
<img src="granat-logo-2gis.svg">
HTML
  "$CHROME" --disable-gpu --no-sandbox --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=$1,$1 --screenshot="$2" "file://$PWD/_r.html" 2>/dev/null
  rm -f _r.html
  echo "готово: $2 — ${1}x${1}"
}

sdelat 1500 granat-logo-2gis-1500.png
