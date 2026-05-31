# Shared repo-root resolution for Windows launchers.
# Dot-source from any script under windows/:  . (Join-Path $PSScriptRoot "..\lib\Repo.ps1")

function Get-RobotRepoRoot {
    param([string]$StartDir = $PSScriptRoot)
    $d = $StartDir
    for ($i = 0; $i -lt 8; $i++) {
        if (Test-Path (Join-Path $d "board\python")) {
            return (Resolve-Path $d).Path
        }
        $parent = Split-Path $d -Parent
        if (-not $parent -or $parent -eq $d) { break }
        $d = $parent
    }
    throw "Robot repo root not found (expected board\python). Started from: $StartDir"
}

function Join-RobotPath {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Parts)
    $p = Get-RobotRepoRoot
    foreach ($part in $Parts) {
        $p = Join-Path $p $part
    }
    return $p
}

function Import-RobotRepo {
    param([string]$ScriptRoot = $PSScriptRoot)
    $script:RobotRepoRoot = Get-RobotRepoRoot -StartDir $ScriptRoot
}
