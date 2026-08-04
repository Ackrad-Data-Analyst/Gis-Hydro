@echo off
setlocal

set "REPO=%~dp0.."
set "TOOLBOX=%REPO%\toolboxes\site_hydrology_workflow.pyt"

if not exist "%TOOLBOX%" (
  echo.
  echo SITE HYDROLOGY TOOLBOX CANNOT START
  echo.
  echo The release is probably still open inside the ZIP file. Windows runs a
  echo command opened from a ZIP in a temporary folder, without the toolbox files.
  echo.
  echo 1. Close this window.
  echo 2. In File Explorer, return to the downloaded ZIP.
  echo 3. Click "Extract all" and choose a permanent local folder.
  echo 4. Open the extracted Gis-Hydro folder.
  echo 5. Double-click tools\Open Site Hydrology Toolbox.cmd again.
  echo.
  echo Expected toolbox location after extraction:
  echo %TOOLBOX%
  pause
  exit /b 1
)

start "" explorer.exe /select,"%TOOLBOX%"

set "ARCGIS_PRO=%ProgramFiles%\ArcGIS\Pro\bin\ArcGISPro.exe"
if exist "%ARCGIS_PRO%" (
  start "" "%ARCGIS_PRO%"
  exit /b 0
)

echo The toolbox folder is open, but ArcGIS Pro was not found in its usual location.
echo Open ArcGIS Pro normally, then add this folder connection:
echo %REPO%
pause
exit /b 0
