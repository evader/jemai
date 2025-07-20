@echo off
cd /d "%~dp0"
echo Installing Electron...
call npm install -g electron
if exist env.bat call env.bat
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install edge-tts openai
echo Starting JEMAI Desktop...
start electron .
