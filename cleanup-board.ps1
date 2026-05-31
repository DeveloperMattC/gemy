# Convenience launcher (repo root). Implementation: windows\setup\cleanup-board.ps1
$target = Join-Path $PSScriptRoot "windows\\setup\\cleanup-board.ps1"
& $target @args
exit $LASTEXITCODE
