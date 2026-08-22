# ═══════════════════════════════════════════════════════════════
#  Утренняя проверка принтеров. Работает БЕЗ участия человека.
#
#  Владелица, 22.08.2026: «когда мне дойдут руки ещё печатать,
#  проверять, печатает оно или не печатает. Я знаю, что оно
#  не печатает. У меня уже сил просто не хватает».
#
#  Отсюда правило этого файла: он молчит, когда всё хорошо.
#  Никаких «проверка выполнена успешно» — это тоже нагрузка.
#  Окно появляется только если печатать сегодня нельзя.
#
#  Запускается сам при входе в Windows. Ставится один раз файлом
#  ustanovit-utrennyuyu-proverku.bat.
# ═══════════════════════════════════════════════════════════════

$bedy = @()

# 1. Сеть. Урок 17.08.2026: компьютер ушёл в чужой Wi-Fi, и пропали
#    сразу все принтеры вместе со сканером. Проверяем это первым.
$svoya = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
         Where-Object { $_.IPAddress -like '192.168.1.*' }
if (-not $svoya) {
    $adresa = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
               Where-Object { $_.IPAddress -ne '127.0.0.1' } |
               ForEach-Object { $_.IPAddress }) -join ', '
    $bedy += "Компьютер в ЧУЖОЙ сети (адрес: $adresa)." 
    $bedy += "Принтеры не отзовутся ни один. Переключитесь на GulNara-5GHZ."
} else {
    # 2. Принтеры по адресам. Проверяем, только если сеть своя:
    #    иначе получим два бессмысленных «не отвечает».
    $spisok = @(
        @{ imya = 'Epson L8188'; adres = '192.168.1.122' },
        @{ imya = 'Canon MF750C'; adres = '192.168.1.233' }
    )
    foreach ($p in $spisok) {
        if (-not (Test-Connection -ComputerName $p.adres -Count 2 -Quiet -ErrorAction SilentlyContinue)) {
            $bedy += ("{0} не отвечает по адресу {1}." -f $p.imya, $p.adres)
        }
    }

    # 3. Застрявшие задания. Одно такое держит все следующие.
    $zavislo = 0
    foreach ($pr in (Get-Printer -ErrorAction SilentlyContinue)) {
        $zavislo += @(Get-PrintJob -PrinterName $pr.Name -ErrorAction SilentlyContinue |
                      Where-Object { $_.JobStatus -match 'Error|Blocked|Offline|PaperOut' }).Count
    }
    if ($zavislo -gt 0) {
        $bedy += "В очереди застряло заданий: $zavislo. Запустите pochinit-pechat.bat."
    }
}

# Молчим, когда всё в порядке. Это главное правило файла.
if ($bedy.Count -eq 0) { exit }

Add-Type -AssemblyName PresentationFramework
$tekst = "Печатать сегодня нельзя, пока не починим:`r`n`r`n" + ($bedy -join "`r`n") +
         "`r`n`r`nЭто известно ДО прихода клиента — значит есть время."
[System.Windows.MessageBox]::Show($tekst, 'Гранат: проверка принтеров', 'OK', 'Warning') | Out-Null
