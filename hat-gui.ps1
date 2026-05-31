# Convenience launcher (repo root). Implementation: windows\demos\hat-gui.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\hat-gui.ps1"
& $target @args
exit $LASTEXITCODE
