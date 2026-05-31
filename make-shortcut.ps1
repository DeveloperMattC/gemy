# Convenience launcher (repo root). Implementation: windows\hub\make-shortcut.ps1
$target = Join-Path $PSScriptRoot "windows\\hub\\make-shortcut.ps1"
& $target @args
exit $LASTEXITCODE
