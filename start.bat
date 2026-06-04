@echo off
echo Asset Management System Startup Script
echo =======================================
echo.

echo Please select an option:
echo 1. Start system (default)
echo 2. Start system after clearing all asset data
echo 3. Exit
echo.
set /p choice=Enter your choice (1-3): 

if "%choice%"=="1" goto start
if "%choice%"=="2" goto init_start
if "%choice%"=="3" goto exit
echo Invalid selection, please run the script again
pause
goto exit

:init_start
echo.
echo Clearing all asset data...
cd backend
python init_data.py
cd ..
echo.

:start
echo.
echo Starting service...
cd backend
start "Asset Management" cmd /k "pip install -r requirements.txt && python app.py"
cd ..

echo.
echo System startup completed!
echo.
echo Access URL: http://localhost:5000
echo.
echo Default credentials: admin / admin
echo.
echo Press any key to exit this window...
pause > nul

:exit