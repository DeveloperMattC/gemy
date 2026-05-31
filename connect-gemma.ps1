# Convenience launcher (repo root). Implementation: windows\demos\connect-gemma.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\connect-gemma.ps1"
& $target @args
exit $LASTEXITCODE
