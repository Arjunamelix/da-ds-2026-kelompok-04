# setup_task_scheduler.ps1 - Setup Windows Task Scheduler untuk update data otomatis
# ===================================================================================
# Jalankan script ini SEKALI untuk mendaftarkan task otomatis di Windows.
# Setelah itu, Windows akan otomatis update data setiap hari jam 08.00 pagi.

$ErrorActionPreference = "Stop"

$TASK_NAME    = "UpdateDataHargaMedan"
$TASK_DESC    = "Update otomatis data harga bahan pokok Kota Medan dari SIMPANG"
$DIR_PROYEK   = "d:\Folder Semester 5\Data Science\Week 9\Praktikum\Dasi_Dalis_04"

# Cari Python
$PYTHON = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PYTHON) {
    $PYTHON = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $PYTHON) {
    Write-Error "Python tidak ditemukan! Pastikan Python terinstall dan ada di PATH."
    exit 1
}

$SCRIPT       = Join-Path $DIR_PROYEK "scripts\pipeline_update_data.py"
$LOG_FILE     = Join-Path $DIR_PROYEK "logs\pipeline_otomatis.log"
$API_URL      = "http://localhost:8080"
$JAM_MULAI    = "08:00"

# Buat folder logs jika belum ada
$LOG_DIR = Join-Path $DIR_PROYEK "logs"
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR | Out-Null
    Write-Host "[OK] Folder logs dibuat: $LOG_DIR"
}

Write-Host "======================================================="
Write-Host "  SETUP WINDOWS TASK SCHEDULER"
Write-Host "  Task     : $TASK_NAME"
Write-Host "  Python   : $PYTHON"
Write-Host "  Script   : $SCRIPT"
Write-Host "  Jadwal   : Setiap hari jam $JAM_MULAI"
Write-Host "  Log      : $LOG_FILE"
Write-Host "======================================================="

# Argument Python
$PYTHON_ARGS = "`"$SCRIPT`" --api $API_URL"

$Action = New-ScheduledTaskAction `
    -Execute $PYTHON `
    -Argument $PYTHON_ARGS `
    -WorkingDirectory $DIR_PROYEK

$Trigger = New-ScheduledTaskTrigger -Daily -At $JAM_MULAI

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# Hapus task lama jika ada
$existing = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "[INFO] Task lama dihapus."
}

# Daftarkan task baru
Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Description $TASK_DESC `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host ""
Write-Host "[SUKSES] Task Scheduler berhasil didaftarkan!"
Write-Host ""
Write-Host "Info task:"
Get-ScheduledTask -TaskName $TASK_NAME | Format-List TaskName, State, Description
Write-Host ""
Write-Host "Perintah berguna:"
Write-Host "  - Lihat status task   : Get-ScheduledTask -TaskName '$TASK_NAME'"
Write-Host "  - Test jalankan manual: Start-ScheduledTask -TaskName '$TASK_NAME'"
Write-Host "  - Hapus task          : Unregister-ScheduledTask -TaskName '$TASK_NAME' -Confirm:`$false"
