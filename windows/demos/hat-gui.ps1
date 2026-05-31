# Coralboard Sensor-HAT test panel: buzzer, LEDs, Gemy sequences, camera.
# Run from hub button 2 or:  powershell -STA -ExecutionPolicy Bypass -File hat-gui.ps1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

$adb       = "adb"
$hatPy     = "/home/root/hat.py"
$hatLocal  = Join-RobotPath "board", "python", "hat.py"
$venvPy    = "/home/root/sl2610-examples/.venv/bin/python3"
$remotePic = "/home/root/hat_photo.jpg"
$localPic  = Join-Path $env:TEMP "hat_photo.jpg"

$form = New-Object System.Windows.Forms.Form
$form.Text = "Coralboard Sensor-HAT - test panel"
$form.Size = New-Object System.Drawing.Size(720, 780)
$form.StartPosition = "CenterScreen"
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$status = New-Object System.Windows.Forms.Label
$status.Dock = "Top"
$status.Height = 26
$status.TextAlign = "MiddleCenter"
$status.Text = "Checking board..."
$form.Controls.Add($status)

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ReadOnly = $true
$log.ScrollBars = "Vertical"
$log.Dock = "Bottom"
$log.Height = 110
$log.Font = New-Object System.Drawing.Font("Consolas", 9)
$form.Controls.Add($log)

function Write-Log($msg) {
    $log.AppendText(("{0}  {1}`r`n" -f (Get-Date -Format "HH:mm:ss"), $msg))
    $log.SelectionStart = $log.Text.Length
    $log.ScrollToCaret()
}

function Invoke-AdbShell([string]$cmd, [string]$label) {
    Write-Log "$label ..."
    $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
    $form.Refresh()
    try {
        $out = & $adb shell $cmd 2>&1
        if ($out) { Write-Log ($out -join "  ") }
    } catch {
        Write-Log "ERROR: $_"
    } finally {
        $form.Cursor = [System.Windows.Forms.Cursors]::Default
    }
}

function Hat([string]$hatArgs, [string]$label) {
    Invoke-AdbShell "python3 $hatPy $hatArgs" $label
}

function Force-BuzzerOff {
    Write-Log "Buzzer OFF (GPIO + hat force_all_off) ..."
    Invoke-AdbShell "gpioset gpiochip0 6=1 2>/dev/null; gpioset gpiochip0 6=1 2>/dev/null; python3 $hatPy force-off 2>/dev/null; true" "Emergency stop"
    foreach ($k in @("red", "green", "blue")) {
        $ledState[$k] = $false
        Update-LedButton $k
    }
}

function Push-HatPy {
    if (-not (Test-Path -LiteralPath $hatLocal)) {
        Write-Log "Missing local hat.py: $hatLocal"
        return
    }
    Write-Log "Pushing hat.py ..."
    $out = & $adb push $hatLocal "/home/root/hat.py" 2>&1
    if ($LASTEXITCODE -eq 0) { Write-Log "hat.py pushed." }
    else { Write-Log ("push failed: " + ($out -join " ")) }
}

function New-Button($text, $x, $y, $w, $h, $onClick) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.Location = New-Object System.Drawing.Point($x, $y)
    $b.Size = New-Object System.Drawing.Size($w, $h)
    $b.Add_Click($onClick)
    return $b
}

# ---- Buzzer ----------------------------------------------------------------
$gbBuzz = New-Object System.Windows.Forms.GroupBox
$gbBuzz.Text = "Buzzer  (active buzzer = one pitch; patterns vary rhythm)"
$gbBuzz.Location = New-Object System.Drawing.Point(12, 32)
$gbBuzz.Size = New-Object System.Drawing.Size(680, 120)
$form.Controls.Add($gbBuzz)

$gbBuzz.Controls.Add((New-Button "Beep" 15 25 90 34 { Hat "beep" "Beep" }))
$gbBuzz.Controls.Add((New-Button "Beep x3" 115 25 90 34 { Hat "beep 3" "Beep x3" }))
$gbBuzz.Controls.Add((New-Button "Tone" 215 25 90 34 {
    Hat ("buzz {0}" -f [int]$toneMs.Value) ("Tone {0}ms" -f [int]$toneMs.Value)
}))
$toneMs = New-Object System.Windows.Forms.NumericUpDown
$toneMs.Location = New-Object System.Drawing.Point(310, 31)
$toneMs.Size = New-Object System.Drawing.Size(70, 24)
$toneMs.Minimum = 50; $toneMs.Maximum = 2000; $toneMs.Increment = 50; $toneMs.Value = 400
$gbBuzz.Controls.Add($toneMs)
$lblMs = New-Object System.Windows.Forms.Label
$lblMs.Text = "ms"; $lblMs.Location = New-Object System.Drawing.Point(384, 34)
$lblMs.AutoSize = $true
$gbBuzz.Controls.Add($lblMs)

$gbBuzz.Controls.Add((New-Button "Siren" 420 25 90 34 { Hat "siren" "Siren" }))
$btnStop = New-Button "STOP" 530 25 130 34 { Force-BuzzerOff }
$btnStop.BackColor = [System.Drawing.Color]::FromArgb(220, 70, 70)
$btnStop.ForeColor = [System.Drawing.Color]::White
$btnStop.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$gbBuzz.Controls.Add($btnStop)

$gbBuzz.Controls.Add((New-Button "R2D2" 15 64 120 34 { Hat "r2d2" "R2D2" }))
$gbBuzz.Controls.Add((New-Button "Warble" 145 64 120 34 { Hat "warble" "Warble" }))
$gbBuzz.Controls.Add((New-Button "Chirp" 275 64 120 34 { Hat "chirp" "Chirp" }))
$gbBuzz.Controls.Add((New-Button "Alarm" 405 64 120 34 { Hat "alarm" "Alarm" }))
$gbBuzz.Controls.Add((New-Button "SOS" 535 64 125 34 { Hat "sos" "SOS" }))

# ---- LEDs ------------------------------------------------------------------
$gbLed = New-Object System.Windows.Forms.GroupBox
$gbLed.Text = "LEDs"
$gbLed.Location = New-Object System.Drawing.Point(12, 162)
$gbLed.Size = New-Object System.Drawing.Size(680, 130)
$form.Controls.Add($gbLed)

$ledState = @{ red = $false; green = $false; blue = $false }
$ledButtons = @{}
$ledColors = @{
    red   = [System.Drawing.Color]::FromArgb(210, 60, 60)
    green = [System.Drawing.Color]::FromArgb(60, 170, 80)
    blue  = [System.Drawing.Color]::FromArgb(70, 110, 210)
}

function Update-LedButton($color) {
    $b = $ledButtons[$color]
    if ($ledState[$color]) {
        $b.BackColor = $ledColors[$color]
        $b.ForeColor = [System.Drawing.Color]::White
        $b.Text = ("{0}: ON" -f $color.ToUpper())
    } else {
        $b.BackColor = [System.Drawing.SystemColors]::Control
        $b.ForeColor = [System.Drawing.Color]::Black
        $b.Text = ("{0}: off" -f $color.ToUpper())
    }
}

$lx = 15
foreach ($c in @("red", "green", "blue")) {
    $color = $c
    $btn = New-Button ("{0}: off" -f $color.ToUpper()) $lx 25 120 38 {}
    $btn.Add_Click({
        param($s, $e)
        $col = $s.Tag
        $ledState[$col] = -not $ledState[$col]
        $stateWord = if ($ledState[$col]) { "on" } else { "off" }
        Hat ("led {0} {1}" -f $col, $stateWord) ("LED {0} {1}" -f $col, $stateWord)
        Update-LedButton $col
    })
    $btn.Tag = $color
    $ledButtons[$color] = $btn
    $gbLed.Controls.Add($btn)
    $lx += 130
}

$gbLed.Controls.Add((New-Button "All ON" 405 25 120 38 {
    foreach ($k in @("red", "green", "blue")) { $ledState[$k] = $true; Update-LedButton $k }
    Hat "led all on" "LED all on"
}))
$gbLed.Controls.Add((New-Button "All OFF" 535 25 120 38 {
    foreach ($k in @("red", "green", "blue")) { $ledState[$k] = $false; Update-LedButton $k }
    Hat "led all off" "LED all off"
}))
$gbLed.Controls.Add((New-Button "Blink Blue x5" 15 73 160 38 {
    Hat "blink blue 5" "Blink blue x5"
    $ledState["blue"] = $false; Update-LedButton "blue"
}))
$gbLed.Controls.Add((New-Button "Rainbow" 185 73 160 38 {
    Hat "rainbow" "Rainbow"
    foreach ($k in @("red", "green", "blue")) { $ledState[$k] = $false; Update-LedButton $k }
}))

# ---- Gemy sequences (same as greeter reactions) ----------------------------
$gbGemy = New-Object System.Windows.Forms.GroupBox
$gbGemy.Text = "Gemy sequences  (run cleanup before Gemy demo if camera is busy)"
$gbGemy.Location = New-Object System.Drawing.Point(12, 300)
$gbGemy.Size = New-Object System.Drawing.Size(680, 130)
$form.Controls.Add($gbGemy)

$gbGemy.Controls.Add((New-Button "Hello intro" 15 28 180 38 { Hat "gemy-intro" "Gemy hello intro" }))
$gbGemy.Controls.Add((New-Button "Ge-my!" 205 28 120 38 { Hat "gemy-name" "Gemy name ack" }))
$gbGemy.Controls.Add((New-Button "Goodbye" 335 28 120 38 { Hat "gemy-goodbye" "Gemy goodbye" }))
$gbGemy.Controls.Add((New-Button "Yes" 15 78 100 38 { Hat "gemy-yes" "Yes (rising chirps + green)" }))
$gbGemy.Controls.Add((New-Button "No" 125 78 100 38 { Hat "gemy-no" "No (descending + red)" }))
$gbGemy.Controls.Add((New-Button "Push hat.py" 465 28 100 38 { Push-HatPy }))

# ---- Camera ----------------------------------------------------------------
$gbCam = New-Object System.Windows.Forms.GroupBox
$gbCam.Text = "Camera"
$gbCam.Location = New-Object System.Drawing.Point(12, 438)
$gbCam.Size = New-Object System.Drawing.Size(680, 150)
$form.Controls.Add($gbCam)

$pic = New-Object System.Windows.Forms.PictureBox
$pic.Location = New-Object System.Drawing.Point(15, 22)
$pic.Size = New-Object System.Drawing.Size(200, 115)
$pic.BorderStyle = "FixedSingle"
$pic.SizeMode = "Zoom"
$pic.BackColor = [System.Drawing.Color]::FromArgb(245, 245, 245)
$gbCam.Controls.Add($pic)

$lblGain = New-Object System.Windows.Forms.Label
$lblGain.Text = "Gain (16-1023, lower if too bright):"
$lblGain.Location = New-Object System.Drawing.Point(235, 28)
$lblGain.AutoSize = $true
$gbCam.Controls.Add($lblGain)

$gain = New-Object System.Windows.Forms.NumericUpDown
$gain.Location = New-Object System.Drawing.Point(235, 50)
$gain.Size = New-Object System.Drawing.Size(90, 24)
$gain.Minimum = 16; $gain.Maximum = 1023; $gain.Increment = 50; $gain.Value = 1023
$gbCam.Controls.Add($gain)

function Take-Photo {
    $g = [int]$gain.Value
    Invoke-AdbShell ("{0} {1} photo {2} --gain {3}" -f $venvPy, $hatPy, $remotePic, $g) ("Photo (gain {0})" -f $g)
    if ($pic.Image) { $old = $pic.Image; $pic.Image = $null; $old.Dispose() }
    if (Test-Path $localPic) { Remove-Item $localPic -Force -ErrorAction SilentlyContinue }
    $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
    & $adb pull $remotePic "$localPic" 2>&1 | Out-Null
    $form.Cursor = [System.Windows.Forms.Cursors]::Default
    if (Test-Path $localPic) {
        $bytes = [System.IO.File]::ReadAllBytes($localPic)
        $ms = New-Object System.IO.MemoryStream(,$bytes)
        $pic.Image = [System.Drawing.Image]::FromStream($ms)
        Write-Log "Photo updated."
    } else {
        Write-Log "Could not pull photo from board."
    }
}

$btnPhoto = New-Button "Take Photo" 235 82 150 42 { Take-Photo }
$btnPhoto.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$gbCam.Controls.Add($btnPhoto)

$gbCam.Controls.Add((New-Button "Open in viewer" 395 82 150 42 {
    if (Test-Path $localPic) { Start-Process $localPic }
    else { Write-Log "Take a photo first." }
}))

# ---- Startup ---------------------------------------------------------------
try {
    $devs = & $adb devices 2>&1 | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice" }
    if ($devs) {
        $status.Text = "Board connected: " + ($devs -join ", ")
        $status.BackColor = [System.Drawing.Color]::FromArgb(225, 245, 225)
        Write-Log "Ready. Pushing latest hat.py ..."
        Push-HatPy
    } else {
        $status.Text = "WARNING: no board - plug in USB-C; buttons will fail until connected."
        $status.BackColor = [System.Drawing.Color]::FromArgb(250, 230, 210)
        Write-Log "No board on ADB."
    }
} catch {
    $status.Text = "ERROR running adb: $_"
    $status.BackColor = [System.Drawing.Color]::FromArgb(250, 215, 215)
}

[void]$form.ShowDialog()
