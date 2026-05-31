# One-time push to github.com/DeveloperMattC/gemy (avoids broken login popup).
# Run from repo root. You will be prompted for a PAT — paste it at the password prompt.
# Do NOT paste the PAT as a PowerShell command.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$git = "C:\Program Files\Git\bin\git.exe"
if (-not (Test-Path $git)) {
    $git = (Get-Command git -ErrorAction SilentlyContinue).Source
    if (-not $git) { throw "Git not found. Install: winget install Git.Git" }
}

Write-Host ""
Write-Host "Push to https://github.com/DeveloperMattC/gemy"
Write-Host ""
Write-Host "You need a Classic PAT with the 'repo' scope (full)."
Write-Host "Create one: https://github.com/settings/tokens/new"
Write-Host ""
Write-Host "When Git asks:"
Write-Host "  Username: DeveloperMattC"
Write-Host "  Password: paste your PAT (starts with github_pat_ or ghp_)"
Write-Host "  (Nothing will show while you paste — that is normal.)"
Write-Host ""

& $git push -u origin main
exit $LASTEXITCODE
