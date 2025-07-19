@echo off
REM ==== JEMAI AGI OS Handoff Automator ====
setlocal enabledelayedexpansion

REM Date and Time
for /f "delims=" %%a in ('wmic OS Get localdatetime ^| find "."') do set dt=%%a
set "YYYY=!dt:~0,4!"
set "MM=!dt:~4,2!"
set "DD=!dt:~6,2!"
set "HH=!dt:~8,2!"
set "MI=!dt:~10,2!"
set "SS=!dt:~12,2!"
set "STAMP=!YYYY!!MM!!DD!-!HH!!MI!!SS!"

REM Handoff Folder
set "HANDOFF=C:\JEMAI_HUB\handoff_!STAMP!"
mkdir "!HANDOFF!"
mkdir "!HANDOFF!\plugins"
mkdir "!HANDOFF!\overlays"
mkdir "!HANDOFF!\old_versions"

REM Copy main file
copy /y "C:\JEMAI_HUB\jemai.py" "!HANDOFF!\jemai.py"

REM Copy plugins
xcopy /y "C:\JEMAI_HUB\plugins\*.py" "!HANDOFF!\plugins\" >nul

REM Copy overlays/listeners
for %%F in (synapz_overlay_v*.py synapz_listener_v*.py) do (
  if exist "C:\JEMAI_HUB\OLD%%F" copy /y "C:\JEMAI_HUB\%%F" "!HANDOFF!\overlays\"
)

REM Copy all jemai.py versions
xcopy /y "C:\JEMAI_HUB\old\Versions\*.py" "!HANDOFF!\old_versions\" >nul

REM Write handoff instructions (for pasting into LLM/Vertex)
set "TXTFILE=!HANDOFF!\handoff.txt"
(
echo JEMAI AGI OS HANDOFF PACKAGE - !STAMP!
echo.
echo Files included:
echo - jemai.py (main superfile)
echo - plugins\*.py
echo - overlays\*.py
echo - old_versions\*.py (full history)
echo.
echo INSTRUCTIONS:
echo 1. Paste the contents of jemai.py into your next AI session.
echo 2. List all plugins/overlays.
echo 3. Include this handoff.txt and reference it for ultra-handoff context.
echo 4. Go wild. Build the best AGI OS ever.
echo.
) > "!TXTFILE!"

REM Zip everything for email/cloud transfer
REM (Requires 7-Zip or replace with your favorite zipper)
if exist "C:\Program Files\7-Zip\7z.exe" (
  "C:\Program Files\7-Zip\7z.exe" a -tzip "!HANDOFF!.zip" "!HANDOFF!\*"
  echo Zipped handoff to !HANDOFF!.zip
)

echo ===========================================================
echo Handoff Package Complete!
echo Folder: !HANDOFF!
echo Ready for copy-paste or LLM upload!
echo ===========================================================
pause
