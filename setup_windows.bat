@echo off
setlocal
cd /d "%~dp0"
echo MAYA TIME - local setup
py -3.12 -m venv .venv
if errorlevel 1 (
  echo Python 3.12 was not found. Trying Python 3.11...
  py -3.11 -m venv .venv
)
if errorlevel 1 goto error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto error
pip install -r requirements.txt
if errorlevel 1 goto error
set MAYA_TIME_STORAGE=local
python -m streamlit run app.py
if errorlevel 1 goto error
goto end
:error
echo.
echo Setup or launch failed. Confirm Python 3.11 or 3.12 is installed and available through the Python launcher.
pause
:end
endlocal
