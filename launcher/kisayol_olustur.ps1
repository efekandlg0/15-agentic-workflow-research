# =============================================================
#  Masaüstüne "Utonium" kısayolu oluşturur (Windows)
#  - Hedef: start_windows_gizli.vbs (siyah komut penceresi göstermez)
#  - Simge: assets\icon_win.ico
#  Çalıştır (PowerShell):
#     powershell -ExecutionPolicy Bypass -File launcher\kisayol_olustur.ps1
# =============================================================
$ErrorActionPreference = "Stop"

$proje   = Split-Path -Parent $PSScriptRoot
$hedef   = Join-Path $PSScriptRoot "start_windows_gizli.vbs"
$simge   = Join-Path $proje "assets\icon_win.ico"
$masaust = [Environment]::GetFolderPath("Desktop")
$kisayol = Join-Path $masaust "Utonium.lnk"

if (-not (Test-Path $hedef)) { throw "Bulunamadi: $hedef" }
if (-not (Test-Path $simge)) { throw "Bulunamadi: $simge  (once: python launcher\make_icons.py)" }

$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut($kisayol)
$lnk.TargetPath       = $hedef
$lnk.WorkingDirectory = $proje
$lnk.IconLocation     = $simge
$lnk.Description      = "Utonium - agentic research workflow"
$lnk.Save()

Write-Host "Kisayol olusturuldu: $kisayol"
Write-Host "Masaustunde 'Utonium' simgesine cift tiklayarak baslatabilirsin."
Write-Host "Gorev cubuguna sabitlemek icin: sag tik -> Gorev cubuguna sabitle"
