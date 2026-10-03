import subprocess
import time
import webbrowser
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
PYTHON = PROJECT / ".venv" / "Scripts" / "python.exe"

# Ollama
subprocess.Popen(
    ["ollama", "serve"],
    creationflags=subprocess.CREATE_NO_WINDOW
)

time.sleep(2)

# FastAPI backend
subprocess.Popen(
    [
        str(PYTHON),
        "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ],
    cwd=PROJECT,
    creationflags=subprocess.CREATE_NO_WINDOW
)

time.sleep(2)

# Streamlit dashboard
subprocess.Popen(
    [
        str(PYTHON),
        "-m", "streamlit",
        "run",
        "frontend/app.py"
    ],
    cwd=PROJECT,
    creationflags=subprocess.CREATE_NO_WINDOW
)

time.sleep(4)

webbrowser.open("http://localhost:8501")