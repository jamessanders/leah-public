@echo off
cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
) else (
    call venv\Scripts\activate
)

REM Always install/update requirements
pip install -r requirements.txt

set PYTHONPATH=%PYTHONPATH%;%CD%
python src\leah_server.py --listen