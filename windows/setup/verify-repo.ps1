# Quick sanity check after repo reorganize.
. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")

$root = Get-RobotRepoRoot
$ok = $true
$checks = @(
    @("board\python\greeter.py"),
    @("board\python\hat.py"),
    @("board\python\gemy-watcher.py"),
    @("board\shell\gemy-boot.sh"),
    @("board\systemd\gemy-watcher.service"),
    @("windows\hub\coralboard-hub.ps1"),
    @("windows\hub\HubServer.ps1"),
    @("windows\hub\HubApi.ps1"),
    @("windows\hub\www\index.html"),
    @("windows\hub\assets\gemy.ico"),
    @("windows\hub\test-hub-api.ps1"),
    @("windows\lib\BoardHealth.ps1"),
    @("windows\lib\GemyFeatures.ps1"),
    @("windows\demos\greet-demo.ps1"),
    @("windows\demos\hat-gui.ps1"),
    @("windows\setup\cleanup-board.ps1"),
    @("windows\setup\test-gemy.ps1"),
    @("board\python\test_gemy_unit.py"),
    @("board\python\gemy_smoke_test.py"),
    @("drivers\ncm\coral-ncm-drv\coral-ncm.inf"),
    @("docs\CORALBOARD-GUIDE.md")
)

Write-Host "Repo root: $root"
foreach ($parts in $checks) {
    $p = Join-RobotPath @parts
    $exists = Test-Path $p
    if (-not $exists) { $ok = $false }
    Write-Host ("  [{0}] {1}" -f $(if ($exists) { "OK" } else { "MISSING" }), ($parts -join "\"))
}

# Root launchers
@("greet-demo.ps1", "hat-gui.ps1", "coralboard-hub.ps1", "cleanup-board.ps1") | ForEach-Object {
    $stub = Join-Path $root $_
    $exists = Test-Path $stub
    if (-not $exists) { $ok = $false }
    Write-Host ("  [{0}] root\{1}" -f $(if ($exists) { "OK" } else { "MISSING" }), $_)
}

if ($ok) {
    Write-Host "`nAll checks passed."
    exit 0
} else {
    Write-Host "`nSome checks FAILED."
    exit 1
}
