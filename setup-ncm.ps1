# Convenience launcher (repo root). Implementation: windows\setup\setup-ncm.ps1
$target = Join-Path $PSScriptRoot "windows\\setup\\setup-ncm.ps1"
& $target @args
exit $LASTEXITCODE
