@echo off
setlocal
REM === Set your agent shell name (update if you want a different file to KEEP) ===
set "AGENT=jemai.py"
set "HUBDIR=C:\jemai_hub"
set "BACKUPDIR=%HUBDIR%\old_parser_files"

REM --- Make backup dir ---
if not exist "%BACKUPDIR%" mkdir "%BACKUPDIR%"

REM --- Move all jemai*.py except jemai.py into backup ---
for %%f in ("%HUBDIR%\jemai*.py") do (
    if /I not "%%~nxf"=="%AGENT%" (
        echo Moving %%f to %BACKUPDIR%\
        move "%%f" "%BACKUPDIR%\" >nul
    )
)

REM --- Done ---
echo All parser scripts moved to %BACKUPDIR%.
echo Only %AGENT% should remain in %HUBDIR%.
echo.
dir "%HUBDIR%\jemai*.py"
echo.
echo If you want to restore any files, look in %BACKUPDIR%.
pause
endlocal
