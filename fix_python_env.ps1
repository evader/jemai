# fix_python_env.ps1
$ErrorActionPreference = "Stop"

function Write-Log($msg) {
    Write-Host "[INFO] $msg"
}

function PythonVersionExists($version) {
    try {
        $out = & python --version 2>&1
        if ($out -match "Python $version") {
            return $true
        }
    } catch { }
    return $false
}

function FindPythonExecutable() {
    $candidates = @("python3.10", "python3.11", "python")

    foreach ($exe in $candidates) {
        try {
            $ver = & $exe --version 2>&1
            if ($ver -match "^Python 3\.(10|11)\.") {
                Write-Log "Found Python: $ver using executable '$exe'"
                return $exe
            }
        } catch {}
    }

    # Try checking common install locations on Windows for Python 3.11
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles(x86)\Python311\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            try {
                $ver = & $path --version 2>&1
                if ($ver -match "^Python 3\.(10|11)\.") {
                    Write-Log "Found Python: $ver at path $path"
                    # Add to PATH for current session
                    $env:PATH = "$([System.IO.Path]::GetDirectoryName($path));$env:PATH"
                    return $path
                }
            } catch {}
        }
    }

    return $null
}

function DownloadPythonInstaller($version) {
    $baseUrl = "https://www.python.org/ftp/python"
    $installerName = "python-$version-amd64.exe"
    $url = "$baseUrl/$version/$installerName"
    $tempPath = "$env:TEMP\$installerName"
    if (-Not (Test-Path $tempPath)) {
        Write-Log "Downloading Python $version installer..."
        Invoke-WebRequest -Uri $url -OutFile $tempPath
    } else {
        Write-Log "Python installer already downloaded at $tempPath"
    }
    return $tempPath
}

function InstallPythonSilently($installerPath) {
    Write-Log "Installing Python silently..."
    $args = "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
    $proc = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Python installer failed with exit code $($proc.ExitCode)"
    }
    Write-Log "Python installed successfully."
}

function CreateVenvAndInstallDeps($pythonExe) {
    Write-Log "Creating virtual environment with $pythonExe..."
    & $pythonExe -m venv venv
    if (-not (Test-Path "venv/Scripts/activate.ps1")) {
        throw "Failed to create virtual environment"
    }
    Write-Log "Upgrading pip, setuptools, and wheel..."
    & .\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

    $requirementsContent = @"
chromadb==0.4.24
chroma-hnswlib
numpy==1.24.3
sentence-transformers
python-dotenv
Flask
Flask-SocketIO
gevent
gevent-websocket
gunicorn
openai
playsound==1.2.2
psutil
pystray
pyperclip
pynput
pyttsx3
requests
watchdog
ollama
"@

    $reqFile = "requirements.txt"
    $requirementsContent | Out-File -FilePath $reqFile -Encoding utf8

    try {
        Write-Log "Installing requirements from requirements.txt..."
        & .\venv\Scripts\python.exe -m pip install -r $reqFile
    } catch {
        Write-Log "Failed to install numpy 1.24.3, attempting numpy 1.25.2 instead..."
        (Get-Content $reqFile) -replace "numpy==1.24.3", "numpy==1.25.2" | Set-Content $reqFile
        & .\venv\Scripts\python.exe -m pip install -r $reqFile
    }
}

# Main logic
try {
    $pyExe = FindPythonExecutable

    if (-not $pyExe) {
        Write-Log "Python 3.10 or 3.11 not found, installing Python 3.11..."
        $installer = DownloadPythonInstaller "3.11.5"
        InstallPythonSilently $installer

        # Wait a bit for environment to settle
        Write-Log "Waiting 10 seconds for PATH updates..."
        Start-Sleep -Seconds 10

        # Retry finding python after install
        $pyExe = FindPythonExecutable

        if (-not $pyExe) {
            Write-Log "Retry failed: Could not find python in PATH, checking common install locations..."
            # This is already done in FindPythonExecutable, but try again forcibly
            $commonLocations = @(
                "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
                "$env:ProgramFiles\Python311\python.exe",
                "$env:ProgramFiles(x86)\Python311\python.exe",
                "C:\Python311\python.exe"
            )
            foreach ($loc in $commonLocations) {
                if (Test-Path $loc) {
                    Write-Log "Found Python at $loc"
                    $env:PATH = "$([System.IO.Path]::GetDirectoryName($loc));$env:PATH"
                    $pyExe = $loc
                    break
                }
            }
        }
    } else {
        Write-Log "Using existing Python executable: $pyExe"
    }

    if (-not $pyExe) {
        throw "Python installation failed or python not in PATH after install."
    }

    CreateVenvAndInstallDeps $pyExe

    Write-Log "Setup complete! Activate your virtualenv with: .\venv\Scripts\Activate.ps1"

} catch {
    Write-Error "Setup failed: $_"
    exit 1
}
