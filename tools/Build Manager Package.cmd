@echo off
setlocal

set "ROOT=%~dp0.."
set "PROPY=%ProgramFiles%\ArcGIS\Pro\bin\Python\Scripts\propy.bat"
set "BUILDER=%ROOT%\tools\build_manager_release.py"
set "OUTPUT=%USERPROFILE%\Downloads\Gis-Hydro-Manager-Package"

if not exist "%PROPY%" (
  echo ERROR: ArcGIS Pro Python was not found at:
  echo %PROPY%
  pause
  exit /b 1
)
if not exist "%BUILDER%" (
  echo ERROR: The release builder is missing from this copy of Gis-Hydro:
  echo %BUILDER%
  echo Download or update the complete repository before trying again.
  pause
  exit /b 1
)

call "%PROPY%" "%BUILDER%" --manager "Adolfo Espino" --author "Ackrad Seth Shimwense" --output "%OUTPUT%"
if errorlevel 1 (
  echo ERROR: The manager package was not created.
  pause
  exit /b 1
)
if not exist "%OUTPUT%\Gis-Hydro_Manager_Release_Adolfo_Espino.zip" (
  echo ERROR: Packaging returned without creating the expected ZIP.
  pause
  exit /b 1
)

echo.
echo PACKAGE CREATED SUCCESSFULLY
echo %OUTPUT%
start "" explorer.exe "%OUTPUT%"
pause
exit /b 0
