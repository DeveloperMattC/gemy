param([switch]$AutostartOnBoot)

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Cleaning up old demos..."
& (Join-RobotPath "windows", "setup", "cleanup-board.ps1") -Quiet | Out-Null

Write-Host "Pushing Gemy files to board..."
& adb wait-for-device
foreach ($f in @("greeter.py", "hat.py", "gemy-watcher.py")) {
    $local = Join-RobotPath "board", "python", $f
    if (-not (Test-Path $local)) { Write-Error "Missing $local"; exit 1 }
    & adb push $local "/home/root/$f" | Out-Null
}
& adb push (Join-RobotPath "board", "systemd", "gemy-watcher.service") /tmp/gemy-watcher.service | Out-Null
& adb push (Join-RobotPath "board", "systemd", "gemy-autostart.service") /tmp/gemy-autostart.service | Out-Null
& adb shell "chmod +x /home/root/gemy-watcher.py; mv /tmp/gemy-watcher.service /etc/systemd/system/; mv /tmp/gemy-autostart.service /etc/systemd/system/" | Out-Null

& adb shell "systemctl daemon-reload"

if ($AutostartOnBoot) {
    & adb shell "systemctl enable gemy-watcher.service; systemctl enable gemy-autostart.service; systemctl restart gemy-watcher.service; systemctl restart gemy-autostart.service"
    Write-Host "Done. Gemy starts on boot. USER button still toggles on/off."
} else {
    & adb shell "systemctl disable gemy-autostart.service 2>/dev/null; systemctl stop gemy-autostart.service 2>/dev/null; systemctl enable gemy-watcher.service; systemctl restart gemy-watcher.service"
    Write-Host "Done. Press USER on the Coralboard to start/stop Gemy."
}

Write-Host "Log: /home/root/gemy.log  |  adb shell systemctl status gemy-watcher"
