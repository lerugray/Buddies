@echo off
title Buddies - First Time Setup
echo ============================================
echo   BUDDIES - First Time Setup
echo ============================================
echo.

echo [1/3] Installing Buddies...
pip install -e . >nul 2>&1
if %errorlevel% neq 0 (
    echo FAILED: Could not install. Make sure Python 3.11+ and pip are installed.
    pause
    exit /b 1
)
echo       Done!

echo [2/3] Registering Claude Code hooks...
python -m buddies.setup_hooks >nul 2>&1
if %errorlevel% neq 0 (
    echo       Skipped - Claude Code hooks not available (install Claude Code first)
) else (
    echo       Done!
)

echo [3/3] Registering MCP tools...
python -m buddies.setup_mcp >nul 2>&1
if %errorlevel% neq 0 (
    echo       Skipped - MCP setup not available
) else (
    echo       Done!
)

echo.
echo ============================================
echo   Setup complete! Double-click launch.bat
echo   to start Buddies anytime.
echo ============================================
echo.
echo TIP: To connect a local AI model, install Ollama
echo from https://ollama.com and run:
echo   ollama pull llama3.2:3b
echo.
pause
