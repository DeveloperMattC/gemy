# One-time install: Gemy runs automatically whenever the board boots on any power source.
# Still use the USER button to stop/start. Run while USB is connected to the PC.
#
#   powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1
#   powershell -ExecutionPolicy Bypass -File install-gemy-standalone.ps1 -ForceBootAutostart

param(
    [switch]$NoAutostartOnBoot,
    [switch]$ForceBootAutostart
)

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
. (Join-Path $PSScriptRoot "..\lib\GemyFeatures.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host ""
Write-Host "  Gemy standalone installer" -ForegroundColor Green
Write-Host "  (boot autostart follows windows\lib\GemyFeatures.ps1 unless -ForceBootAutostart)" -ForegroundColor DarkGray
Write-Host ""

$devs = & adb devices 2>&1 | Out-String
if ($devs -notmatch "`tdevice") {
    Write-Host "ERROR: No Coralboard on ADB. Plug in USB-C and retry." -ForegroundColor Red
    exit 1
}

Write-Host "Cleaning up old demos..."
$cleanup = Join-RobotPath "windows", "setup", "cleanup-board.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $cleanup -Quiet | Out-Null

Write-Host "Pushing Gemy files to board..."
& adb wait-for-device
$files = @(
    @("board", "python", "greeter.py"),
    @("board", "python", "hat.py"),
    @("board", "python", "gemma_mood.py"),
    @("board", "python", "gemma_mood_worker.py"),
    @("board", "python", "gemy-watcher.py"),
    @("board", "shell", "gemy-boot.sh")
)
foreach ($parts in $files) {
    $local = Join-RobotPath @parts
    $name = $parts[-1]
    if (-not (Test-Path $local)) { Write-Error "Missing $local"; exit 1 }
    & adb push $local "/home/root/$name" | Out-Null
    Write-Host "  OK  $name"
}

$enable = Join-RobotPath "windows", "setup", "enable-gemy-autostart.ps1"
$wantBoot = ($ForceBootAutostart) -or ((Get-GemyBootAutostartEnabled) -and (-not $NoAutostartOnBoot))

# Always install watcher + push boot script; enable/disable autostart per flag.
& powershell -NoProfile -ExecutionPolicy Bypass -File $enable -Quiet -Disable 2>&1 | Out-Null
& adb shell "systemctl enable gemy-watcher.service 2>/dev/null; systemctl restart gemy-watcher.service 2>/dev/null" 2>&1 | Out-Null

if ($wantBoot) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $enable -Quiet -EnableOnly
    Write-Host ""
    Write-Host "Done. Gemy will start on every boot (~30-90s after power-on)." -ForegroundColor Green
} else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $enable -Quiet -Disable
    Write-Host ""
    Write-Host "Done. Boot autostart OFF - use USER button or Gemy Control Center." -ForegroundColor Yellow
}
Write-Host "  Log: adb shell tail -f /home/root/gemy.log"

Write-Host ""
Write-Host "Unplug from PC and use any USB power. USER button still toggles Gemy on/off."
Write-Host "Log: adb shell tail -f /home/root/gemy.log"
Write-Host "Status: adb shell systemctl status gemy-autostart gemy-watcher"
Write-Host ""
