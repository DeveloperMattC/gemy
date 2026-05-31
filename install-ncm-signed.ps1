# Convenience launcher (repo root). Implementation: windows\setup\install-ncm-signed.ps1
$target = Join-Path $PSScriptRoot "windows\\setup\\install-ncm-signed.ps1"
& $target @args
exit $LASTEXITCODE
