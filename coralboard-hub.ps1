# Convenience launcher (repo root). Implementation: windows\hub\coralboard-hub.ps1
$target = Join-Path $PSScriptRoot "windows\\hub\\coralboard-hub.ps1"
& $target @args
exit $LASTEXITCODE
