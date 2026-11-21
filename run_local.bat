@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set MAYA_TIME_STORAGE=local
python -m streamlit run app.py
endlocal
