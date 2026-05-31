# Opens the interactive Gemma 3 voice-translation demo on the Coralboard.
# Speak English; it transcribes (Moonshine) and translates (Gemma 3) to Spanish/French.

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Connecting to Coralboard for the Gemma 3 voice demo..." -ForegroundColor Cyan
adb wait-for-device

Write-Host ""
Write-Host "When prompted:" -ForegroundColor Green
Write-Host "  - Pick the audio input device (the hat PDM mic is the 'klamath'/dmic card, usually 0)." -ForegroundColor Green
Write-Host "  - Press 1 for Spanish or 2 for French, then speak a short English phrase." -ForegroundColor Green
Write-Host "  - Ctrl+C to exit." -ForegroundColor DarkGray
Write-Host "----------------------------------------------------------------"

adb shell -t "cd /home/root/sl2610-examples && . .venv/bin/activate && cd gemma_translate && python3 cli_translate.py"
