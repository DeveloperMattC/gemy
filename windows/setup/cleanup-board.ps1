# Stop leftover demos on the Coralboard and release camera / buzzer / LEDs.
# Use before starting the greeting robot (hub button or manual).
#
#   powershell -ExecutionPolicy Bypass -File cleanup-board.ps1

param([switch]$Quiet)

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

function Say($msg) { if (-not $Quiet) { Write-Host $msg } }

Say "Waiting for board..."
& adb wait-for-device 2>$null | Out-Null

Say "Stopping old demos (wave_detect, greeter, webrtc)..."
& adb shell "pkill -9 -f wave_detect.py 2>/dev/null; pkill -9 -f /home/root/greeter.py 2>/dev/null; pkill -9 -f webrtc-stream.sh 2>/dev/null; true" 2>$null | Out-Null
Start-Sleep -Seconds 2

$fuserOut = (& adb shell "fuser /dev/video0 2>/dev/null" 2>$null | Out-String).Trim()
if ($fuserOut) {
    Say "Releasing camera (was held by PID $fuserOut)..."
    foreach ($procId in ($fuserOut -split '\s+')) {
        if ($procId -match '^\d+$') {
            & adb shell "kill -9 $procId 2>/dev/null" 2>$null | Out-Null
        }
    }
    Start-Sleep -Seconds 1
}

Say "Buzzer off, LEDs off..."
& adb shell "gpioset gpiochip0 6=1 2>/dev/null; python3 /home/root/hat.py led all off 2>/dev/null; true" 2>$null | Out-Null

$cam = (& adb shell "fuser /dev/video0 2>/dev/null || echo free" 2>$null | Out-String).Trim()
$procs = (& adb shell "ps -ef 2>/dev/null | grep -E 'wave_detect|greeter.py' | grep -v grep || true" 2>$null | Out-String).Trim()

$ok = ($cam -eq "free" -or $cam -eq "") -and [string]::IsNullOrWhiteSpace($procs)

if ($ok) {
    Say "Board clean - camera free, no greeter/wave demos running."
} else {
    Say "Cleanup done (check below if something still looks wrong):"
    if ($procs) { Say "  Still running: $procs" }
    if ($cam -and $cam -ne "free") { Say "  Camera still held: $cam" }
}

if ($ok) { exit 0 } else { exit 1 }
