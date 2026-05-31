# Enable Gemy to start on every board power-on (systemd). Idempotent - safe to run often.
# Called from greet-demo.ps1 and install-gemy-standalone.ps1

param([switch]$Quiet, [switch]$Disable, [switch]$EnableOnly)

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")

function Say([string]$msg) { if (-not $Quiet) { Write-Host $msg } }

$devs = & adb devices 2>&1 | Out-String
if ($devs -notmatch "`tdevice") {
    Say "  (skip autostart: no board on ADB)"
    return 1
}

& adb wait-for-device | Out-Null

$pushBoot = @(
    @("board", "python", "gemy-watcher.py"),
    @("board", "shell", "gemy-boot.sh")
)
foreach ($parts in $pushBoot) {
    $local = Join-RobotPath @parts
    $name = $parts[-1]
    if (-not (Test-Path -LiteralPath $local)) {
        Say "  ERROR: missing $local"
        return 1
    }
    $r = Invoke-Adb push $local "/home/root/$name"
    if ($r.ExitCode -ne 0) { return 1 }
}

$r = Invoke-Adb push (Join-RobotPath "board", "systemd", "gemy-watcher.service") /tmp/gemy-watcher.service
if ($r.ExitCode -ne 0) { return 1 }
$r = Invoke-Adb push (Join-RobotPath "board", "systemd", "gemy-autostart.service") /tmp/gemy-autostart.service
if ($r.ExitCode -ne 0) { return 1 }

$installCmd = "chmod +x /home/root/gemy-watcher.py /home/root/gemy-boot.sh; " +
    "mv /tmp/gemy-watcher.service /etc/systemd/system/; " +
    "mv /tmp/gemy-autostart.service /etc/systemd/system/; " +
    "systemctl daemon-reload; " +
    "systemctl enable gemy-watcher.service; " +
    "systemctl restart gemy-watcher.service"
& adb shell $installCmd 2>&1 | Out-Null

if ($Disable) {
    & adb shell "systemctl disable gemy-autostart.service 2>/dev/null; systemctl stop gemy-autostart.service 2>/dev/null; systemctl reset-failed gemy-autostart.service 2>/dev/null; pkill -9 -f gemy-boot.sh 2>/dev/null; pkill -9 -f /home/root/greeter.py 2>/dev/null; true" 2>&1 | Out-Null
    $enabled = (& adb shell "systemctl is-enabled gemy-autostart.service 2>/dev/null" 2>&1 | Out-String).Trim()
    if ($enabled -eq 'disabled' -or $enabled -eq 'masked' -or $enabled -match 'not-found') {
        Say "  Boot autostart disabled."
        return 0
    }
    Say "  Boot autostart disable requested (systemd reports: $enabled)."
    return 0
}

if ($EnableOnly) {
    & adb shell "systemctl enable gemy-autostart.service 2>/dev/null" 2>&1 | Out-Null
} else {
    & adb shell "systemctl enable gemy-autostart.service; systemctl restart gemy-autostart.service" 2>&1 | Out-Null
}
$enabled = (& adb shell "systemctl is-enabled gemy-autostart.service 2>/dev/null" 2>&1 | Out-String).Trim()
if ($enabled -eq "enabled") {
    Say "  Boot autostart ON - Gemy starts ~30s after every power-on."
    return 0
}
Say "  Warning: could not confirm gemy-autostart is enabled (got: $enabled)"
return 1
