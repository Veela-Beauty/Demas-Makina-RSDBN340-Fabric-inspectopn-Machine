@echo off
setlocal
cd /d "%~dp0"
set PYTHON=..\venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo.
    echo ERROR: %PYTHON% not found.
    echo Make sure venv\ exists in the project root.
    echo.
    pause
    exit /b 1
)

echo.
echo === [1/3] Cleaning previous build artifacts ===
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo === [2/3] Verifying Python version and architecture ===
%PYTHON% --version
%PYTHON% -c "import struct; bits=struct.calcsize('P')*8; assert bits==32, 'bad arch'; print(bits)"
if errorlevel 1 (
    echo ERROR: Must use 32-bit Python.
    echo.
    pause
    exit /b 1
)

echo.
echo === [3/4] Installing build deps (certifi needed by the spec's collect_all) ===
%PYTHON% -m pip install -r requirements.txt --quiet
%PYTHON% -c "import ssl, sqlite3, certifi; print('tunnel deps OK:', certifi.where())"
if errorlevel 1 (
    echo ERROR: ssl/sqlite3/certifi not importable in the build Python; the exe would fail TLS.
    echo.
    pause
    exit /b 1
)

echo.
echo === [4/4] Running PyInstaller from spec ===
%PYTHON% -m PyInstaller BRL305_Monitor.spec

if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo Reminder: on a BARE Windows 7 x86 box, install "VC++ 2015-2022 Redistributable x86"
echo once (UCRT). The app's startup preflight will name any missing DLL instead of crashing.
echo.
echo ============================================================
echo  BUILD COMPLETE: dist\BRL305_Monitor.exe
echo ============================================================
pause
