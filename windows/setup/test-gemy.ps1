# Push latest Gemy scripts, run PC unit tests + on-board smoke test.
#   powershell -ExecutionPolicy Bypass -File windows\setup\test-gemy.ps1
#   ... -Quick          # skip on-board Gemma load (faster)
#   ... -StartGemy      # after tests, launch greet-demo voice-only

param(
    [switch]$Quick,
    [switch]$StartGemy,
    [switch]$NoPush,
    [switch]$HeartbeatSmoke
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User")

function Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

Step "PC tests (black-box classify first, then unit/wiring)"
foreach ($testScript in @(
        "test_gemy_blackbox.py",
        "test_gemy_classify_integration.py",
        "test_gemy_wiring.py",
        "test_gemy_unit.py", "test_gemy_math.py", "test_gemy_qa.py",
        "test_gemy_phrase_buffer.py", "test_gemy_empathy.py", "test_gemy_fallback.py",
        "test_gemy_perf.py", "test_gemy_stability.py",
        "test_gemy_heartbeat_smoke.py", "test_gemy_reactions.py"
    )) {
    $unit = Join-RobotPath "board", "python", $testScript
    python $unit
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Write-Host "  All PC unit + perf tests passed." -ForegroundColor Green

Step "Waiting for board (up to 45s)"
$found = $false
for ($i = 0; $i -lt 15; $i++) {
    $devs = & adb devices 2>&1 | Out-String
    if ($devs -match "`tdevice") { $found = $true; break }
    Start-Sleep -Seconds 3
}
if (-not $found) {
    $devs = & adb devices 2>&1 | Out-String
}
if ($devs -notmatch "`tdevice") {
    Write-Host ""
    Write-Host "Board not on ADB - skipping on-board smoke test." -ForegroundColor Yellow
    Write-Host "Plug in USB-C and re-run for full validation." -ForegroundColor Yellow
    if ($StartGemy) {
        & (Join-RobotPath "windows", "demos", "greet-demo.ps1") -NoVision
    }
    exit 0
}

if (-not $NoPush) {
    Step "Push scripts to board"
    & adb wait-for-device | Out-Null
    $files = @(
        "greeter.py", "hat.py", "gemma_mood.py", "gemma_mood_worker.py",
        "gemy_math.py", "gemy_qa.py", "gemy_empathy.py", "gemy_fallback.py",
        "gemy_classify.py", "gemy_phrase_buffer.py", "gemy_reactions.py",
        "gemy_stability.py", "gemy_diag.py", "gemy_trace.py", "gemy_smoke_test.py", "gemy_heartbeat_smoke.py"
    )
    foreach ($f in $files) {
        $local = Join-RobotPath "board", "python", $f
        if (-not (Test-Path -LiteralPath $local)) { throw "Missing $local" }
        & adb push $local "/home/root/$f" 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "adb push failed: $f" }
        Write-Host "  pushed $f" -ForegroundColor DarkGreen
    }
    $boot = Join-RobotPath "board", "shell", "gemy-boot.sh"
    & adb push $boot "/home/root/gemy-boot.sh" 2>&1 | Out-Null
    Write-Host "  pushed gemy-boot.sh" -ForegroundColor DarkGreen
}

Step "Cleanup board (stop stale greeter, buzzer off)"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-RobotPath "windows", "setup", "cleanup-board.ps1")

Step "On-board smoke test"
$py = "/home/root/sl2610-examples/.venv/bin/python3"
$quickArg = if ($Quick) { " --quick" } else { "" }
$cmd = "$py -u /home/root/gemy_smoke_test.py$quickArg"
Write-Host "  $cmd" -ForegroundColor DarkGray
& adb shell $cmd
$smoke = $LASTEXITCODE
if ($smoke -ne 0) {
    Write-Host ""
    Write-Host "Smoke test FAILED (exit $smoke). See output above." -ForegroundColor Red
    exit $smoke
}
Write-Host ""
Write-Host "Smoke test PASSED." -ForegroundColor Green

if ($HeartbeatSmoke) {
    Step "Heartbeat + memory liveness (on board)"
    $hbArgs = @()
    if ($Quick) { $hbArgs += "-Seconds", "35" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File `
        (Join-RobotPath "windows", "setup", "gemy-heartbeat-smoke.ps1") `
        @hbArgs -NoPush
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($StartGemy) {
    Step "Starting Gemy (voice only)"
    & (Join-RobotPath "windows", "demos", "greet-demo.ps1") -NoVision -SkipCleanup
}

exit 0
