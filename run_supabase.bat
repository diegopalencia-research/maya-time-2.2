@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist ".streamlit\secrets.toml" (
  echo Copy .streamlit\secrets.toml.example to .streamlit\secrets.toml and add your Supabase URL and publishable key.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set MAYA_TIME_STORAGE=supabase
python -m streamlit run app.py
endlocal
