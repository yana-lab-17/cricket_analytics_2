@echo off
title 3D Cricket Fielding Simulator Game
echo ======================================================================
echo   3D Cricket Fielding & Bowling Simulation Game
echo ======================================================================
cd /d "%~dp0"

echo [1/2] Starting Game Physics & Web Server...
start "Cricket Game Engine" cmd /k "python -m backend.game_server"

timeout /t 2 /nobreak > nul

echo [2/2] Opening 3D Game in Browser (http://localhost:8080)...
start http://localhost:8080

echo.
echo ======================================================================
echo Game is ONLINE!
echo - 3D WebGL Game: http://localhost:8080
echo - WebSocket Server: ws://localhost:8765
echo ======================================================================
pause
