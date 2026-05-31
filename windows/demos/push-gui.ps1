# Drag-and-drop GUI to copy images from this PC to the Coralboard samples folder.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Make sure adb is on PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

$remoteDir = "/home/root/sl2610-examples/samples"
$adb = "adb"

$form = New-Object System.Windows.Forms.Form
$form.Text = "Coralboard - Drop images to upload"
$form.Size = New-Object System.Drawing.Size(560, 460)
$form.StartPosition = "CenterScreen"
$form.AllowDrop = $true

$header = New-Object System.Windows.Forms.Label
$header.Text = "Target on board:`n$remoteDir"
$header.AutoSize = $false
$header.Dock = "Top"
$header.Height = 50
$header.TextAlign = "MiddleCenter"
$header.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$form.Controls.Add($header)

$drop = New-Object System.Windows.Forms.Panel
$drop.Dock = "Top"
$drop.Height = 160
$drop.BackColor = [System.Drawing.Color]::FromArgb(245, 248, 255)
$drop.BorderStyle = "FixedSingle"
$drop.AllowDrop = $true

$dropLabel = New-Object System.Windows.Forms.Label
$dropLabel.Text = "Drag image files here`n(jpg, png, etc.)"
$dropLabel.Dock = "Fill"
$dropLabel.TextAlign = "MiddleCenter"
$dropLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$dropLabel.ForeColor = [System.Drawing.Color]::FromArgb(70, 90, 140)
$dropLabel.AllowDrop = $true
$drop.Controls.Add($dropLabel)
$form.Controls.Add($drop)

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ReadOnly = $true
$log.ScrollBars = "Vertical"
$log.Dock = "Fill"
$log.Font = New-Object System.Drawing.Font("Consolas", 9)
$form.Controls.Add($log)
$log.BringToFront()

function Write-Log($msg) {
    $log.AppendText(("{0}  {1}`r`n" -f (Get-Date -Format "HH:mm:ss"), $msg))
}

# Check device on startup
try {
    $devs = & $adb devices 2>&1 | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice" }
    if ($devs) { Write-Log "Board connected: $($devs -join ', ')" }
    else { Write-Log "WARNING: no board detected. Plug in USB-C and reopen." }
} catch { Write-Log "ERROR running adb: $_" }

$onDragEnter = {
    param($s, $e)
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::Copy
    } else {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
    }
}

$onDragDrop = {
    param($s, $e)
    $files = $e.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)
    foreach ($f in $files) {
        if (Test-Path $f -PathType Leaf) {
            $name = Split-Path $f -Leaf
            Write-Log "Uploading $name ..."
            $form.Refresh()
            $out = & $adb push "$f" "$remoteDir/" 2>&1
            Write-Log ($out -join " ")
        } else {
            Write-Log "Skipped (not a file): $f"
        }
    }
    Write-Log "Done. Files now in $remoteDir on the board."
}

$form.Add_DragEnter($onDragEnter)
$form.Add_DragDrop($onDragDrop)
$drop.Add_DragEnter($onDragEnter)
$drop.Add_DragDrop($onDragDrop)
$dropLabel.Add_DragEnter($onDragEnter)
$dropLabel.Add_DragDrop($onDragDrop)

[void]$form.ShowDialog()
