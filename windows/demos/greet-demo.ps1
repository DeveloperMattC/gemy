# Launch Gemy - full stack from Control Center button 3 (or .\greet-demo.ps1).
# Does everything: adb check, push board scripts, cleanup, run greeter.py

param(
    [string]$Sensitivity = "medium",
    [switch]$NoSpeech,
    [switch]$NoVision,
    [switch]$SkipCleanup,
    [switch]$NoGemmaMood,
    [switch]$GemmaMood,
    [switch]$GemmaMoodSerial,
    [switch]$GemmaMoodSync
)

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
. (Join-Path $PSScriptRoot "..\lib\GemyFeatures.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Test-AdbBoard {
    $lines = & adb devices 2>&1 | Out-String
    return ($lines -match "`tdevice")
}

Write-Host ""
Write-Host "  Gemy - Coralboard greeting robot" -ForegroundColor Green
$mood = if ($NoGemmaMood -or (-not $GemmaMood -and -not $GemmaMoodSerial)) {
    "keyword moods -> beeps"
} elseif ($GemmaMoodSerial) {
    "keywords + Gemma serial (experimental)"
} else {
    "keywords + Gemma assist"
}
$mode = if ($NoVision) { "voice only - $mood" } else { "voice + camera - $mood" }
Write-Host "  (push + cleanup + Moonshine + $mode)" -ForegroundColor DarkGray
Write-Host ""

if (-not (Test-AdbBoard)) {
    Write-Host "ERROR: No Coralboard on ADB." -ForegroundColor Red
    Write-Host "  - Plug in USB-C (data cable, not charge-only)" -ForegroundColor Yellow
    Write-Host "  - Wait ~20s for boot, then run again" -ForegroundColor Yellow
    Write-Host "  - Or use Control Center -> Refresh connection" -ForegroundColor Yellow
    exit 1
}

Write-Step "Waiting for board..."
& adb wait-for-device | Out-Null

Write-Step "Pushing latest scripts to /home/root/ ..."
$pushList = @(
    "greeter.py", "hat.py", "gemma_mood.py", "gemma_mood_worker.py",
    "gemy_diag.py", "gemy_stability.py"
)
$missing = @()
foreach ($f in $pushList) {
    $local = Join-RobotPath "board", "python", $f
    if (-not (Test-Path -LiteralPath $local)) {
        $missing += $f
        continue
    }
    $out = & adb push $local "/home/root/$f" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED push $f : $out" -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK  $f" -ForegroundColor DarkGreen
}
if ($missing.Count -gt 0) {
    $miss = $missing -join ", "
    Write-Host "  MISSING in repo: $miss" -ForegroundColor Red
    exit 1
}

$enableBoot = Join-RobotPath "windows", "setup", "enable-gemy-autostart.ps1"
if (Test-Path -LiteralPath $enableBoot) {
    if (Get-GemyBootAutostartEnabled) {
        Write-Step "Enabling Gemy on every power-on (boot autostart)..."
        & powershell -NoProfile -ExecutionPolicy Bypass -File $enableBoot -Quiet -EnableOnly
    } else {
        Write-Step "Boot autostart OFF (feature flag) - disabling on board..."
        & powershell -NoProfile -ExecutionPolicy Bypass -File $enableBoot -Quiet -Disable
    }
} else {
    Write-Host "  Warning: enable-gemy-autostart.ps1 missing - run install-gemy-standalone.ps1 once." -ForegroundColor Yellow
    & adb shell "systemctl stop gemy-autostart.service 2>/dev/null; systemctl disable gemy-autostart.service 2>/dev/null; pkill -9 -f gemy-boot.sh 2>/dev/null; true" 2>$null | Out-Null
}
Start-Sleep -Seconds 1

if (-not $SkipCleanup) {
    Write-Step "Cleaning board (stop old demos, free camera, buzzer/LEDs off)..."
    $cleanup = Join-RobotPath "windows", "setup", "cleanup-board.ps1"
    if (-not (Test-Path -LiteralPath $cleanup)) {
        Write-Error "Missing cleanup script: $cleanup"
        exit 1
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $cleanup
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Warning: cleanup reported issues (starting Gemy anyway)." -ForegroundColor Yellow
    }
}

$py = "/home/root/sl2610-examples/.venv/bin/python3"
$opts = "--sensitivity $Sensitivity --cooldown 3 --pc-start"
if ($NoSpeech) { $opts += " --no-speech" }
if ($NoVision) { $opts += " --no-vision" }
if ($NoGemmaMood) {
    $opts += " --no-gemma-mood"
} else {
    $opts += " --gemma-mood"
}
if ($GemmaMoodSerial) {
    Write-Host "  Note: -GemmaMoodSerial is ignored (causes NPU freezes). Using keyword moods." -ForegroundColor Yellow
}
if ($GemmaMoodSync) { $opts += " --gemma-mood-sync" }
$cmd = "$py -u /home/root/greeter.py $opts"

Write-Step "Starting Gemy on the board..."
if ($NoVision) {
    Write-Host "  Voice only (no camera). Say Gemy, hello, jokes, compliments, or insults."
} else {
    Write-Host "  Wave / hand-up / voice. Say Gemy, hello, jokes, compliments, or insults."
}
Write-Host "  Wait for [ears] listening (~15s). Yes/no, jokes, nice/mean/sad -> beeps/LEDs; Gemma helps if unclear."
if (-not $NoGemmaMood) {
    Write-Host "  Gemma assist ON (long unclear phrases only; 5s cap; NPU freed each listen)."
    Write-Host "  Session heartbeat ON; listen capped at 60s (mic auto-reset if hung)."
}
Write-Host "  Say Gemy turn off to stop."
Write-Host "  Short hello beep, then listening."
Write-Host "  [diag] lines every 20s + each listen/react (copy log if it freezes)." -ForegroundColor DarkGray
Write-Host ""

& adb shell -t $cmd
exit $LASTEXITCODE
