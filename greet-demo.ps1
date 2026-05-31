# Convenience launcher (repo root). Implementation: windows\demos\greet-demo.ps1
$target = Join-Path $PSScriptRoot "windows\\demos\\greet-demo.ps1"
& $target @args
exit $LASTEXITCODE
