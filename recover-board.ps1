# Emergency unfreeze: kill Gemy/Gemma + buzzer/LED off (skips slow boot-autostart step).
# Use when the board is stuck mid-Gemma load or adb still works.
#
#   .\recover-board.ps1
#
# If adb says "no devices": unplug USB-C, wait 15s, plug back in, run again.

$here = $PSScriptRoot
& (Join-Path $here "windows\setup\cleanup-board.ps1") -Quick @args
exit $LASTEXITCODE
