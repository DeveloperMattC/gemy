# Gemy - Coralboard Control Center (web dashboard)
# Opens http://127.0.0.1:8765/ in your browser. Keep this window open while using it.

param(
    [int]$Port = 0,
    [switch]$NoBrowser
)

$server = Join-Path $PSScriptRoot "HubServer.ps1"
if (-not (Test-Path -LiteralPath $server)) {
    Write-Host "Missing HubServer.ps1" -ForegroundColor Red
    exit 1
}

$args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $server)
if ($Port -gt 0) { $args += "-Port"; $args += $Port }
if ($NoBrowser) { $args += "-NoBrowser" }

& powershell @args
exit $LASTEXITCODE
