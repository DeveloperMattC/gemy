# Convenience launcher (repo root). Implementation: windows\setup\bind-ncm.ps1
$target = Join-Path $PSScriptRoot "windows\\setup\\bind-ncm.ps1"
& $target @args
exit $LASTEXITCODE
