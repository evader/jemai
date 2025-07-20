# === JEMAI OS AGENT SETUP SCRIPT ===
# Run as admin PowerShell

$repo = "https://github.com/evader/jemai_os_agent.git"
$installDir = "C:\JEMAI_HUB\jemai_os_agent"
$py = "python"
$venvDir = "$installDir\.venv"

# Ensure JEMAI_HUB exists
if (-not (Test-Path "C:\JEMAI_HUB")) { New-Item -ItemType Directory -Path "C:\JEMAI_HUB" }

# Clone or update repo
if (Test-Path $installDir) {
    Write-Host "[*] Updating JemAI OS Agent..." -ForegroundColor Yellow
    cd $installDir
    git pull
} else {
    Write-Host "[*] Cloning JemAI OS Agent repo..." -ForegroundColor Green
    git clone $repo $installDir
    cd $installDir
}

# Create venv
if (-not (Test-Path $venvDir)) {
    & $py -m venv .venv
}
$venvPy = "$venvDir\Scripts\python.exe"
$venvPip = "$venvDir\Scripts\pip.exe"

# Install requirements
& $venvPip install --upgrade pip
& $venvPip install -r requirements.txt

# Install Electron app (for tray/menu/logs)
if (Test-Path "$installDir/desktop_app") {
    cd "$installDir/desktop_app"
    npm install
    npm run build
}

# Register startup (autostart at login)
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\JemAI Agent.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($lnk)
$shortcut.TargetPath = "$venvPy"
$shortcut.Arguments = "`"$installDir\main.py`""
$shortcut.WorkingDirectory = $installDir
$shortcut.Save()

# One-time config: voice/keys/settings
if (-not (Test-Path "$installDir\jemai_settings.json")) {
    Copy-Item "$installDir\sample_settings.json" "$installDir\jemai_settings.json"
}

Write-Host "`n[✓] JEMAI AGI OS Agent installed!"
Write-Host " > System Tray, Context Menu, Hotkeys, Logs, Voice, VSCode/Chrome hooks"
Write-Host " > Launching now..."

# Start the agent
Start-Process $venvPy "$installDir\main.py"