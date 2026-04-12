@echo off
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM caddy.exe 2>nul