@echo off
chcp 65001 > nul
echo ========================================
echo 68 Keypoints Annotation Tool - Build Script
echo ========================================
echo.

echo [1/4] Finding Python environment...
set PYTHON_EXE=
set PYINSTALLER_EXE=

REM Try to find conda environments
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo Searching for video-player environment via conda...
    for /f "delims=" %%i in ('conda env list ^| findstr "video-player"') do (
        for /f "tokens=1,*" %%a in ("%%i") do (
            if exist "%%b\python.exe" (
                set "PYTHON_EXE=%%b\python.exe"
                set "PYINSTALLER_EXE=%%b\Scripts\pyinstaller.exe"
                echo Found: %%b
                goto :check_pyinstaller
            )
        )
    )
)

REM Fallback: use current Python
echo Trying current Python environment...
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python
    set PYINSTALLER_EXE=pyinstaller
    echo Using current Python
    goto :check_pyinstaller
)

echo ERROR: No Python environment found!
pause
exit /b 1

:check_pyinstaller
echo.
echo [2/4] Checking PyInstaller...
"%PYTHON_EXE%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    "%PYTHON_EXE%" -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller!
        pause
        exit /b 1
    )
)
echo PyInstaller ready

echo.
echo [3/4] Cleaning old files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist KeypointAnnotationTool.exe del /q KeypointAnnotationTool.exe

echo.
echo [4/4] Building executable...
"%PYINSTALLER_EXE%" --clean build_exe.spec

if exist dist\KeypointAnnotationTool.exe (
    echo.
    echo ========================================
    echo BUILD SUCCESSFUL!
    echo ========================================
    echo.
    echo Output: dist\KeypointAnnotationTool.exe
    dir dist\KeypointAnnotationTool.exe | findstr "KeypointAnnotationTool.exe"
    echo.
    echo Moving to current directory...
    move dist\KeypointAnnotationTool.exe .
    echo.
    echo Cleaning temporary files...
    rmdir /s /q build 2>nul
    rmdir /s /q dist 2>nul
    del /q KeypointAnnotationTool.spec 2>nul
    echo.
    echo ========================================
    echo DONE! Run: KeypointAnnotationTool.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo BUILD FAILED! Check errors above
    echo ========================================
)

pause
