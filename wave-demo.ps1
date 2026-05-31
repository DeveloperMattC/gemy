# Convenience launcher (repo root). Implementation: windows\demos\wave-demo.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\wave-demo.ps1"
& $target @args
exit $LASTEXITCODE
