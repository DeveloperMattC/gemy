# Convenience launcher (repo root). Implementation: windows\demos\push-gui.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\push-gui.ps1"
& $target @args
exit $LASTEXITCODE
