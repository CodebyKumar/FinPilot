@echo off
start "Pocket CFO Backend" cmd /k "cd pocket-cfo-parser && .venv\Scripts\activate && uvicorn api.main:app --reload --port 8000"
start "Pocket CFO Frontend" cmd /k "python -m http.server 5500 --directory frontend"
start chrome http://localhost:5500
