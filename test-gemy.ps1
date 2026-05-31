# Run Gemy test suite (PC unit tests + board smoke when connected).
& "$PSScriptRoot\windows\setup\test-gemy.ps1" @args
exit $LASTEXITCODE
