# Turn OFF Gemy starting on every power-on. Safe to run anytime the board is on USB.
#
#   powershell -ExecutionPolicy Bypass -File disable-gemy-autostart.ps1
#
# Also stops greeter now and turns the buzzer off.

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")

Write-Host ""
Write-Host "  Disable Gemy boot autostart" -ForegroundColor Cyan
Write-Host ""

$devs = & adb devices 2>&1 | Out-String
if ($devs -notmatch "`tdevice") {
    Write-Host "ERROR: Board not on ADB. Plug in USB-C, wait for boot, run again." -ForegroundColor Red
    exit 1
}

$cleanup = Join-RobotPath "windows", "setup", "cleanup-board.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $cleanup -KeepBootAutostart 2>&1 | ForEach-Object { Write-Host $_ }

$enable = Join-RobotPath "windows", "setup", "enable-gemy-autostart.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $enable -Disable

$state = (& adb shell "systemctl is-enabled gemy-autostart.service 2>/dev/null" 2>&1 | Out-String).Trim()
Write-Host ""
if ($state -eq "disabled") {
    Write-Host "Boot autostart is OFF. Gemy will NOT start on power-on." -ForegroundColor Green
    Write-Host "Start Gemy with the USER button or Gemy Control Center." -ForegroundColor DarkGray
} else {
    Write-Host "systemctl reports: $state" -ForegroundColor Yellow
    Write-Host "If it still starts on boot, run this again after a full board reboot." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Crash log: adb shell tail -50 /home/root/gemy.log"
Write-Host ""
