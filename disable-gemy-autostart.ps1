# Convenience launcher (repo root). Implementation: windows\setup\disable-gemy-autostart.ps1
$target = Join-Path $PSScriptRoot "windows\setup\disable-gemy-autostart.ps1"
& $target @args
exit $LASTEXITCODE
