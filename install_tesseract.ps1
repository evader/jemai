# Download & Install Tesseract-OCR 5.3.3 (or latest stable)
$installerUrl = "https://github.com/tesseract-ocr/tesseract/releases/download/5.3.3/tesseract-5.3.3.20230925-win64.exe"
$destPath = "$env:TEMP\tesseract-installer.exe"

Write-Host "Downloading Tesseract-OCR installer..."
Invoke-WebRequest -Uri $installerUrl -OutFile $destPath

Write-Host "Running Tesseract-OCR installer (silent)..."
Start-Process -FilePath $destPath -ArgumentList "/SILENT" -Wait

# Default install path
$tessPath = "C:\Program Files\Tesseract-OCR"

if (-not (Test-Path $tessPath)) {
    Write-Host "Tesseract-OCR was not found at expected location! Please check install." -ForegroundColor Red
    exit 1
}

# Add to PATH for current user
$envPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($envPath -notlike "*$tessPath*") {
    [Environment]::SetEnvironmentVariable("PATH", "$envPath;$tessPath", "User")
    Write-Host "Tesseract-OCR path added to User PATH."
} else {
    Write-Host "Tesseract-OCR path already in PATH."
}

Write-Host "Tesseract-OCR install complete! You may need to restart apps/terminal to see the new PATH." -ForegroundColor Green
