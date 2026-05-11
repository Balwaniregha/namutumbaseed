@echo off
cd /d %~dp0
echo Installing requirements...
python -m pip install -r requirements.txt
echo Starting Namutumba SMS...
start http://127.0.0.1:5000
python app.py
pause
