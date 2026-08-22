@echo off
chcp 65001 >nul
title Вылечить связь с принтером — студия Гранат
setlocal

rem ═══════════════════════════════════════════════════════════════
rem  ЧТО ЭТО ЛЕЧИТ
rem
rem  Принтер исправен, включён и стоит в сети, а Windows пишет
rem  «Отключен» или «Ошибка», задания копятся и не уходят.
rem
rem  Причина: Windows раз в несколько секунд опрашивает принтер
rem  по SNMP — жив ли он. По Wi-Fi ответ теряется (принтер уснул,
rem  сеть моргнула), и Windows метит исправный аппарат мёртвым.
rem  Дальше очередь встаёт, и человек стоит перед клиентом.
rem
rem  Файл выключает этот опрос у всех принтерных портов. Печать
rem  от этого не страдает: задания идут так же, Windows просто
rem  перестаёт делать вид, что знает больше принтера.
rem
rem  ЭТО НЕ ЛЕЧИТ «хватает бумагу и говорит нет бумаги» — там
rem  причина в размере бумаги или в самой бумаге, см. CLAUDE.md.
rem
rem  Вернуть как было: тот же путь в реестре, значение SNMP = 1.
rem ═══════════════════════════════════════════════════════════════

net session >nul 2>&1
if errorlevel 1 (
    echo Нужны права администратора. Сейчас Windows спросит разрешение.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================================
echo  Выключаю опрос SNMP у принтерных портов
echo ============================================================
echo.

powershell -NoProfile -Command "$b='HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Standard TCP/IP Port\Ports'; if (-not (Test-Path $b)) { '  Портов TCP/IP не найдено — лечить нечего.'; exit }; Get-ChildItem $b | ForEach-Object { $bylo = (Get-ItemProperty -Path $_.PSPath -Name SNMP -ErrorAction SilentlyContinue).SNMP; if ($null -eq $bylo) { $bylo = 'не задано' }; Set-ItemProperty -Path $_.PSPath -Name SNMP -Value 0 -Type DWord -ErrorAction SilentlyContinue; '  {0,-26} было: {1,-10} стало: 0' -f $_.PSChildName, $bylo }"

echo.
echo  Перезапускаю службу печати, чтобы правка вступила в силу.
echo.
net stop spooler
net start spooler

echo.
echo ============================================================
echo  Как теперь выглядят принтеры
echo ============================================================
echo.
powershell -NoProfile -Command "Get-Printer | ForEach-Object { '   {0,-30} {1}' -f $_.Name, $_.PrinterStatus }"

echo.
echo  «Готов» или «Normal» — связь вылечена.
echo.
echo  Осталось «Отключен» — принтер сейчас действительно не в сети:
echo  проверьте, включён ли он и в своей ли вы сети Wi-Fi.
echo.
pause
