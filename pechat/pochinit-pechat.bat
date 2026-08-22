@echo off
chcp 65001 >nul
title Починить печать — студия Гранат
setlocal

rem ═══════════════════════════════════════════════════════════════
rem  ЗАЧЕМ ЭТОТ ФАЙЛ
rem
rem  Владелица, 22.08.2026: «поломка принтера или его отвратительная
rem  работа — это уже норма». То есть чинить надо не случай, а причину,
rem  и для этого нужны факты в момент поломки, а не через час.
rem
rem  Файл собирает эти факты и заодно делает то, что помогало раньше:
rem  чистит очередь и перезапускает службу печати.
rem
rem  Порядок шагов не случайный. 17.08.2026 «слетели» все принтеры
rem  разом, включая сканер, и виноват был не принтер: компьютер
rem  подключился к чужому Wi-Fi и оказался в другой сети. Поэтому
rem  сеть проверяется ПЕРВОЙ, до всего остального.
rem ═══════════════════════════════════════════════════════════════

rem Служба печати перезапускается только с правами администратора.
rem Без них файл просит их сам, обычным окном Windows.
net session >nul 2>&1
if errorlevel 1 (
    echo Нужны права администратора. Сейчас Windows спросит разрешение.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================================
echo  ШАГ 1. СЕТЬ. Компьютер и принтеры в одной сети?
echo ============================================================
echo.
echo  Имя сети Wi-Fi:
netsh wlan show interfaces | findstr /C:"SSID" | findstr /V /C:"BSSID"
echo.
echo  Адреса этого компьютера:
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' } | ForEach-Object { '   {0,-28} {1}' -f $_.InterfaceAlias, $_.IPAddress }"
echo.
powershell -NoProfile -Command "if (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.1.*' }) { '  ИТОГ: сеть СВОЯ. Дело не в ней, читайте дальше.' } else { '  ИТОГ: СЕТЬ ЧУЖАЯ. Принтеры настроены на 192.168.1.*, а компьютер' ; '        сейчас в другой сети. Ни один принтер отвечать не будет.' ; '        Переключитесь на GulNara-5GHZ — этого хватит, дальше не надо.' }"

echo.
echo ============================================================
echo  ШАГ 2. ПРИНТЕРЫ. Что с ними прямо сейчас
echo ============================================================
echo.
powershell -NoProfile -Command "Get-Printer | ForEach-Object { $p = Get-PrinterPort -Name $_.PortName -ErrorAction SilentlyContinue; $c = Get-PrintConfiguration -PrinterName $_.Name -ErrorAction SilentlyContinue; $j = @(Get-PrintJob -PrinterName $_.Name -ErrorAction SilentlyContinue).Count; [PSCustomObject]@{ 'Printer' = $_.Name; 'Status' = $_.PrinterStatus; 'Port' = $_.PortName; 'Address' = $p.PrinterHostAddress; 'SNMP' = $p.SNMPEnabled; 'Paper' = $c.PaperSize; 'Jobs' = $j } } | Format-List"

echo.
echo  Как это читать:
echo    Address — адрес, по которому Windows ищет принтер. Epson должен
echo              быть 192.168.1.122, Canon — 192.168.1.233. Другой адрес
echo              означает, что принтер переехал, а Windows об этом не знает.
echo    SNMP    — если True, Windows опрашивает принтер по сети и при первом
echo              же молчании помечает его «Отключен». По Wi-Fi это частая
echo              причина вечных «ошибок» у исправного принтера.
echo    Paper   — размер бумаги по умолчанию. Печатаете фото 10x15, а тут
echo              стоит A4 — принтер честно скажет «нет бумаги».
echo.

echo ============================================================
echo  ШАГ 3. Чищу очередь и перезапускаю службу печати
echo ============================================================
echo.
echo  Очередь чистится у ВСЕХ принтеров сразу: когда печать встала,
echo  разбираться, чьё задание виновато, некогда, а одно застрявшее
echo  задание держит все следующие.
echo.
net stop spooler
del /Q /F "%SystemRoot%\System32\spool\PRINTERS\*.*" >nul 2>&1
net start spooler

echo.
echo ============================================================
echo  ШАГ 4. Стало так
echo ============================================================
echo.
powershell -NoProfile -Command "Get-Printer | ForEach-Object { $j = @(Get-PrintJob -PrinterName $_.Name -ErrorAction SilentlyContinue).Count; '   {0,-30} {1,-14} в очереди: {2}' -f $_.Name, $_.PrinterStatus, $j }"

echo.
echo ============================================================
echo  ШАГ 5. Теперь руками, на самом принтере
echo ============================================================
echo.
echo    1. Выключите принтер кнопкой.
echo    2. Досчитайте до десяти.
echo    3. Включите.
echo    4. Отправьте фотографию на печать заново.
echo.
echo  Не помогло — сфотографируйте ШАГ 1 и ШАГ 2 и пришлите в чат.
echo  Там видно всё, что нужно, чтобы найти постоянную причину,
echo  а не чинить одно и то же каждую неделю.
echo.
pause
