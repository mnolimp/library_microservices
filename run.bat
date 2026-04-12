@echo off
call .venv\Scripts\activate.bat
start "Main" cmd /k uvicorn server.root_server:app --host 127.0.0.1 --port 8001
start "WebSocket" cmd /k uvicorn server.web_socket_server:app --host 127.0.0.1 --port 8002
start "Client" cmd /k uvicorn client.client_server:app --host 127.0.0.1 --port 8003
start "Caddy" cmd /k caddy.exe run