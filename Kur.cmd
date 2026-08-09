@echo off
setlocal EnableExtensions
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-Pala.ps1" -Mode Install
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo [Pala] Kurulum basarisiz. Ustteki mesaji okuyun; ag/hook otomatik calismaz.
  exit /b %EXITCODE%
)

echo.
echo Sonraki 3 adim (Codex Work):
echo 1^) Plugins'te Pala gorunuyor mu kontrol edin.
echo 2^) /hooks ile Pala hook guvenini ^(trust^) verin.
echo 3^) Yeni bir sohbet acin.
exit /b 0
