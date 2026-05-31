# Coralboard Control Center — launch demos from one window.
#   windows\hub\coralboard-hub.ps1   or   .\coralboard-hub.ps1 from repo root

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

. (Join-Path $PSScriptRoot "..\lib\Repo.ps1")
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
$adb = "adb"

function Start-GuiScript([string[]]$RelPath) {
    $path = Join-RobotPath @RelPath
    Start-Process powershell -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-STA", "-File", $path)
}
function Start-TermScript([string[]]$RelPath, [string[]]$extra) {
    $path = Join-RobotPath @RelPath
    $a = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $path) + $extra
    Start-Process powershell -ArgumentList $a
}
function Start-Shell {
    Start-Process powershell -ArgumentList @(
        "-NoProfile", "-NoExit", "-Command",
        "`$env:Path += ';' + [Environment]::GetEnvironmentVariable('Path','Machine'); adb shell")
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Coralboard Control Center"
$form.Size = New-Object System.Drawing.Size(440, 720)
$form.StartPosition = "CenterScreen"
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$form.BackColor = [System.Drawing.Color]::FromArgb(247, 249, 252)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Coralboard Control Center"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(40, 60, 110)
$title.Location = New-Object System.Drawing.Point(20, 14)
$title.Size = New-Object System.Drawing.Size(400, 30)
$form.Controls.Add($title)

$status = New-Object System.Windows.Forms.Label
$status.Location = New-Object System.Drawing.Point(20, 46)
$status.Size = New-Object System.Drawing.Size(400, 22)
$status.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($status)

$cleanBtn = New-Object System.Windows.Forms.Button
$cleanBtn.Text = "0.  Clean up board (stop old demos, free camera)"
$cleanBtn.Location = New-Object System.Drawing.Point(20, 72)
$cleanBtn.Size = New-Object System.Drawing.Size(390, 40)
$cleanBtn.FlatStyle = "Flat"
$cleanBtn.BackColor = [System.Drawing.Color]::FromArgb(180, 70, 50)
$cleanBtn.ForeColor = [System.Drawing.Color]::White
$cleanBtn.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$cleanBtn.Add_Click({
    $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
    $cleanBtn.Enabled = $false
    try {
        $cleanup = Join-RobotPath "windows", "setup", "cleanup-board.ps1"
        $log = @()
        & powershell -NoProfile -ExecutionPolicy Bypass -File $cleanup 2>&1 | ForEach-Object { $log += "$_" }
        $msg = if ($log.Count) { ($log -join "`n") } else { "Done." }
        [System.Windows.Forms.MessageBox]::Show($msg, "Board cleanup", "OK", "Information") | Out-Null
        Update-Status
    } catch {
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "Cleanup failed", "OK", "Error") | Out-Null
    } finally {
        $cleanBtn.Enabled = $true
        $form.Cursor = [System.Windows.Forms.Cursors]::Default
    }
})
$form.Controls.Add($cleanBtn)

$cleanHint = New-Object System.Windows.Forms.Label
$cleanHint.Text = "Kills wave_detect/greeter, releases camera, buzzer+LEDs off. Do this before #3."
$cleanHint.Location = New-Object System.Drawing.Point(24, 112)
$cleanHint.Size = New-Object System.Drawing.Size(386, 28)
$cleanHint.ForeColor = [System.Drawing.Color]::FromArgb(90, 100, 120)
$cleanHint.Font = New-Object System.Drawing.Font("Segoe UI", 8)
$form.Controls.Add($cleanHint)

$y = 142
function Add-Action($text, $desc, $color, $onClick) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.Location = New-Object System.Drawing.Point(20, $script:y)
    $b.Size = New-Object System.Drawing.Size(390, 44)
    $b.FlatStyle = "Flat"
    $b.BackColor = $color
    $b.ForeColor = [System.Drawing.Color]::White
    $b.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $b.TextAlign = "MiddleLeft"
    $b.Padding = New-Object System.Windows.Forms.Padding(12, 0, 0, 0)
    $b.Add_Click($onClick)
    $form.Controls.Add($b)
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $desc
    $l.Location = New-Object System.Drawing.Point(24, ($script:y + 44))
    $l.Size = New-Object System.Drawing.Size(386, 16)
    $l.ForeColor = [System.Drawing.Color]::FromArgb(90, 100, 120)
    $l.Font = New-Object System.Drawing.Font("Segoe UI", 8)
    $form.Controls.Add($l)
    $script:y += 70
}

$blue   = [System.Drawing.Color]::FromArgb(60, 110, 200)
$green  = [System.Drawing.Color]::FromArgb(50, 160, 90)
$purple = [System.Drawing.Color]::FromArgb(120, 80, 180)
$teal   = [System.Drawing.Color]::FromArgb(40, 150, 160)
$orange = [System.Drawing.Color]::FromArgb(210, 130, 40)
$gray   = [System.Drawing.Color]::FromArgb(90, 100, 120)

Add-Action "1.  Connect / fix internet sharing" `
    "Re-arm USB internet sharing (run first each session; needs admin)." `
    $orange { Start-TermScript @("windows", "setup", "install-ncm-signed.ps1") }

Add-Action "2.  Sensor HAT control panel" `
    "Buttons for buzzer, LEDs, and camera photo." `
    $blue { Start-GuiScript @("windows", "demos", "hat-gui.ps1") }

Add-Action "3.  Gemy (wave / hand / voice)" `
    "Say 'Gemy' for its signature hello; also funny, nice, mean, neutral." `
    $teal { Start-TermScript @("windows", "demos", "greet-demo.ps1") }

Add-Action "4.  Live video in browser (WebRTC)" `
    "Stream the test pattern to your browser (no monitor)." `
    $purple { Start-TermScript @("windows", "demos", "webrtc-view.ps1") @("test") }

Add-Action "5.  Upload images to the board" `
    "Drag-and-drop pictures into the demo samples folder." `
    $green { Start-GuiScript @("windows", "demos", "push-gui.ps1") }

Add-Action "6.  Image classification (terminal)" `
    "Run the NPU image-classification demo." `
    $blue { Start-TermScript @("windows", "demos", "connect-demo.ps1") }

Add-Action "7.  Gemma 3 voice translation" `
    "Speak English; get Spanish/French/Italian (HAT mic)." `
    $purple { Start-TermScript @("windows", "demos", "connect-gemma.ps1") }

Add-Action "8.  Open a shell on the board" `
    "Interactive root Linux prompt over adb." `
    $gray { Start-Shell }

$refresh = New-Object System.Windows.Forms.Button
$refresh.Text = "Refresh connection"
$refresh.Location = New-Object System.Drawing.Point(20, $y)
$refresh.Size = New-Object System.Drawing.Size(390, 30)
$form.Controls.Add($refresh)

function Update-Status {
    try {
        $devs = & $adb devices 2>&1 | Select-Object -Skip 1 | Where-Object { $_ -match "\tdevice" }
        if ($devs) {
            $ipLine = & $adb shell "ip addr show usb0 2>/dev/null | sed -n 's/.*inet \([0-9.]*\).*/\1/p' | head -n 1" 2>$null
            $ip = ($ipLine | Select-Object -First 1)
            if ($ip) { $ip = $ip.Trim() }
            $status.Text = if ($ip) { "Board connected  (usb0 = $ip)" } else { "Board connected" }
            $status.ForeColor = [System.Drawing.Color]::FromArgb(40, 140, 70)
        } else {
            $status.Text = "No board detected - plug in the USB-C cable, then Refresh."
            $status.ForeColor = [System.Drawing.Color]::FromArgb(190, 60, 60)
        }
    } catch {
        $status.Text = "adb error: $($_.Exception.Message)"
        $status.ForeColor = [System.Drawing.Color]::FromArgb(190, 60, 60)
    }
}
$refresh.Add_Click({ Update-Status })

Update-Status
[void]$form.ShowDialog()
