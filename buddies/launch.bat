@echo off
title Buddies - Your AI Companion
echo Starting Buddies...
python -m buddies
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Could not start Buddies.
    echo Make sure Python 3.11+ is installed and you've run setup.bat first.
    echo.
    pause
)
