# Smoke-test Gemy Control Center HTTP API (hub must be running).
param([string]$BaseUrl = "http://127.0.0.1:8767")

$ErrorActionPreference = "Stop"
$failed = 0
$passed = 0

function Test-Case([string]$name, [scriptblock]$body) {
    try {
        & $body
        Write-Host "[OK]   $name" -ForegroundColor Green
        $script:passed++
    } catch {
        Write-Host "[FAIL] $name" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor DarkRed
        $script:failed++
    }
}

Write-Host ""
Write-Host "Gemy Hub API tests -> $BaseUrl" -ForegroundColor Cyan
Write-Host ""

Test-Case "GET / (index.html)" {
    $r = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -ne 200) { throw "status $($r.StatusCode)" }
    if ($r.Content -notmatch "Gemy Control Center") { throw "missing page title text" }
}

Test-Case "GET /styles.css" {
    $r = Invoke-WebRequest -Uri "$BaseUrl/styles.css" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -ne 200 -or $r.Content.Length -lt 100) { throw "bad css" }
}

Test-Case "GET /app.js" {
    $r = Invoke-WebRequest -Uri "$BaseUrl/app.js" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -ne 200 -or $r.Content -notmatch "refreshAll") { throw "bad js" }
}

Test-Case "GET /favicon.ico" {
    $r = Invoke-WebRequest -Uri "$BaseUrl/favicon.ico" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -ne 200 -or $r.RawContentLength -lt 100) { throw "bad favicon" }
}

Test-Case "GET /api/health" {
    $h = Invoke-RestMethod -Uri "$BaseUrl/api/health" -TimeoutSec 90
    if (-not $h.ok) { throw "ok=false" }
    if (-not $h.health.checks) { throw "no checks" }
    Write-Host "       status=$($h.health.status) board=$($h.health.boardConnected) boot=$($h.health.bootAutostart)" -ForegroundColor DarkGray
}

Test-Case "GET /api/activity" {
    $a = Invoke-RestMethod -Uri "$BaseUrl/api/activity" -TimeoutSec 10
    if (-not $a.ok) { throw "ok=false" }
    if ($null -eq $a.activity) { throw "no activity array" }
}

Test-Case "POST /api/refresh" {
    $ref = Invoke-RestMethod -Uri "$BaseUrl/api/refresh" -Method POST -TimeoutSec 120
    if (-not $ref.health) { throw "no health in response" }
    $boot = ($ref.health.checks | Where-Object { $_.id -eq "boot" } | Select-Object -First 1)
    Write-Host "       boot check: $($boot.detail)" -ForegroundColor DarkGray
}

Test-Case "GET /api/board-log" {
    $log = Invoke-RestMethod -Uri "$BaseUrl/api/board-log?lines=20" -TimeoutSec 45
    if ($log.ok -and $log.lines.Count -gt 0) {
        Write-Host "       log lines: $($log.lines.Count)" -ForegroundColor DarkGray
    } elseif (-not $log.ok) {
        Write-Host "       $($log.message) (acceptable if board offline)" -ForegroundColor DarkGray
    }
}

Test-Case "GET /api/board-processes" {
    $p = Invoke-RestMethod -Uri "$BaseUrl/api/board-processes" -TimeoutSec 45
    if ($p.ok) {
        Write-Host "       processes: $($p.processes.Count)" -ForegroundColor DarkGray
    }
}

# Boot autostart should be OFF per feature flag when board connected
Test-Case "boot autostart disabled on board (feature flag)" {
    $h = Invoke-RestMethod -Uri "$BaseUrl/api/health" -TimeoutSec 90
    if (-not $h.health.boardConnected) {
        Write-Host "       (skipped - board not connected)" -ForegroundColor DarkGray
        return
    }
    if ($h.health.bootAutostart -eq $true) {
        throw "bootAutostart still true - run disable-gemy-autostart.ps1"
    }
    $boot = $h.health.checks | Where-Object { $_.id -eq "boot" }
    if ($boot.detail -notmatch "OFF|disabled|feature flag|Will enable") {
        Write-Host "       note: boot detail=$($boot.detail)" -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "Passed: $passed  Failed: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host ""
if ($failed -gt 0) { exit 1 }
exit 0
