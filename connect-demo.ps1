# Convenience launcher (repo root). Implementation: windows\demos\connect-demo.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\connect-demo.ps1"
& $target @args
exit $LASTEXITCODE
