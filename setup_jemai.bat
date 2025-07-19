@echo off
REM ==== JEMAI AGI OS Super-Installer ====
cd /d %~dp0
echo [JEMAI] Creating folders...
mkdir plugins
mkdir old
mkdir wiki
mkdir hub
mkdir davesort
REM === Download jemai.py if not present ===
if not exist jemai.py (
    echo [JEMAI] Downloading latest jemai.py...
    powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/evader/jemai/main/jemai.py' -OutFile 'jemai.py'"
)
REM === Python check ===
where python >nul 2>nul || (echo You need Python 3.9+ in PATH! && pause && exit /b)
echo [JEMAI] Installing Python dependencies...
python -m pip install --user flask flask_socketio requests pyttsx3 edge-tts psutil
REM === Plugins (sample) ===
if not exist plugins\vertex.py (
    echo [JEMAI] Creating sample plugins...
    echo. > plugins\vertex.py
    echo. > plugins\chatgpt.py
)
REM === Start JEMAI ===
echo [JEMAI] Launching OS...
start python jemai.py
echo [JEMAI] JEMAI AGI OS Ready!
pause
REM === AUTO-PULL jemai.py FROM GITHUB ===
REM (Replace 'evader/jemai/main/jemai.py' with your actual path if you fork)
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/evader/jemai/main/jemai.py' -OutFile 'jemai.py'"
python jemai.py
