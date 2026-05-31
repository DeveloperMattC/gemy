# Opens an interactive shell on the Coralboard, in the image demo folder,
# with the Python virtual environment already activated.

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Connecting to Coralboard..." -ForegroundColor Cyan
adb wait-for-device
adb devices

Write-Host ""
Write-Host "You are now in: /home/root/sl2610-examples/Image_classification" -ForegroundColor Green
Write-Host "Virtual env (.venv) is active. Run the demo with:" -ForegroundColor Green
Write-Host ""
Write-Host '  python3 classification.py --model ../models/mbv2.vmfb --image ../samples/cat.jpg --labels labels.json --device torq' -ForegroundColor Yellow
Write-Host ""
Write-Host "Type 'exit' to leave the board shell." -ForegroundColor DarkGray
Write-Host "----------------------------------------------------------------"

adb shell -t "cd /home/root/sl2610-examples && . .venv/bin/activate && cd Image_classification && exec bash -i"
