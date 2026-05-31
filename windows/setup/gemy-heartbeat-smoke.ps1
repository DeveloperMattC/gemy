# Heartbeat + memory liveness smoke on the Coralboard (via adb).
#   powershell -ExecutionPolicy Bypass -File windows\setup\gemy-heartbeat-smoke.ps1
#   ... -Seconds 60
#   ... -WithGemma        # heavier (optional)
#   ... -WithSpeech       # needs HAT mic (optional)
#   ... -NoPush           # skip adb push

param(
    [int]$Seconds = 45,
    [switch]$WithGemma,
    [switch]$WithSpeech,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")

function Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

$devs = & adb devices 2>&1 | Out-String
if ($devs -notmatch "`tdevice") {
    Write-Host "ERROR: No Coralboard on ADB." -ForegroundColor Red
    exit 1
}

if (-not $NoPush) {
    Step "Push Gemy scripts"
    & adb wait-for-device | Out-Null
    $files = @(
        "greeter.py", "hat.py", "gemma_mood.py", "gemma_mood_worker.py",
        "gemy_math.py", "gemy_qa.py", "gemy_stability.py", "gemy_diag.py",
        "gemy_heartbeat_smoke.py", "gemy_smoke_test.py"
    )
    foreach ($f in $files) {
        $local = Join-RobotPath "board", "python", $f
        if (-not (Test-Path -LiteralPath $local)) { throw "Missing $local" }
        & adb push $local "/home/root/$f" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "adb push failed: $f" }
        Write-Host "  OK  $f" -ForegroundColor DarkGreen
    }
}

Step "Cleanup stale greeter"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-RobotPath "windows", "setup", "cleanup-board.ps1")

Step "Heartbeat + memory smoke ($Seconds s)"
$py = "/home/root/sl2610-examples/.venv/bin/python3"
$boardArgs = "--seconds $Seconds"
if ($WithGemma) { $boardArgs = "--with-gemma $boardArgs" }
if ($WithSpeech) { $boardArgs = "--with-speech $boardArgs" }
$cmd = "GEMY_SMOKE_MONITOR=1 $py -u /home/root/gemy_heartbeat_smoke.py $boardArgs"
Write-Host "  adb shell $cmd" -ForegroundColor DarkGray
& adb shell $cmd
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Heartbeat smoke FAILED." -ForegroundColor Red
    Write-Host "Look for: listen_once hung, STUCK, low MemAvailable, missing heartbeat pulse" -ForegroundColor Yellow
    exit $LASTEXITCODE
}
Write-Host ""
Write-Host "Heartbeat smoke PASSED." -ForegroundColor Green
exit 0
