@echo off
setlocal

set "REPO=%~dp0.."
set "TOOLBOX=%REPO%\toolboxes\site_hydrology_workflow.pyt"

if not exist "%TOOLBOX%" (
  echo Site Hydrology toolbox not found:
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
