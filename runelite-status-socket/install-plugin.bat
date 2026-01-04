@echo off
echo ========================================
echo RuneLite Status Socket Plugin Installer
echo ========================================
echo.

REM Create externalplugins directory if it doesn't exist
if not exist "%USERPROFILE%\.runelite\externalplugins" (
    echo Creating externalplugins directory...
    mkdir "%USERPROFILE%\.runelite\externalplugins"
)

REM Copy plugin JAR
echo Copying plugin to RuneLite...
copy /Y "build\libs\runelite-status-socket-1.0.0.jar" "%USERPROFILE%\.runelite\externalplugins\"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Installation successful!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Restart RuneLite
    echo 2. Enable "Status Socket" plugin in settings
    echo 3. Log into OSRS
    echo 4. Check that file exists:
    echo    %USERPROFILE%\.runelite\live_data.json
    echo.
    echo Plugin installed to:
    echo %USERPROFILE%\.runelite\externalplugins\runelite-status-socket-1.0.0.jar
    echo.
) else (
    echo.
    echo ========================================
    echo Installation failed!
    echo ========================================
    echo.
    echo Make sure you built the plugin first:
    echo    cd runelite-status-socket
    echo    gradle-7.6\bin\gradle build
    echo.
)

pause
