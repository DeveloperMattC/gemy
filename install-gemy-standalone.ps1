# Convenience launcher (repo root). Implementation: windows\setup\install-gemy-standalone.ps1
$target = Join-Path $PSScriptRoot "windows\\setup\\install-gemy-standalone.ps1"
& $target @args
exit $LASTEXITCODE
