@echo off
REM Snowmaking Planner - one-step launcher for Windows.
REM Creates a local virtual environment, installs dependencies, and runs the app.
setlocal
cd /d "%~dp0"

if not exist ".venv" (
  echo Creating virtual environment (.venv)...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt

echo Starting Snowmaking Planner...
streamlit run app.py

endlocal
