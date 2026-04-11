@echo off
setlocal

set "ROOT_DIR=D:\Gradua_pro_code-spring\Vehic_Insur_Claim"
set "SPRINGBOOT_DIR=%ROOT_DIR%\springboot"
set "MLP_DIR=%ROOT_DIR%\MLP"
set "VUE_DIR=%ROOT_DIR%\vue"

set "SPRING_TITLE=Vehic_Insur_Claim - Spring Boot"
set "FASTAPI_TITLE=Vehic_Insur_Claim - FastAPI"
set "VUE_TITLE=Vehic_Insur_Claim - Vue"
set "MYSQL_SERVICE=MySQL"

set "CONDA_BAT=D:\Anaconda3\condabin\conda.bat"

if not defined CONDA_BAT (
    echo [ERROR] Unable to find conda.bat. Please update CONDA_BAT in this script.
    pause
    exit /b 1
)

if not exist "%CONDA_BAT%" (
    echo [ERROR] conda.bat was not found at: %CONDA_BAT%
    pause
    exit /b 1
)

taskkill /FI "WINDOWTITLE eq %SPRING_TITLE%" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq %FASTAPI_TITLE%" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq %VUE_TITLE%" /T /F >nul 2>&1

echo ==========================================
echo Vehic_Insur_Claim one-click startup
echo ==========================================
echo [1/4] Checking MySQL service...
sc query "%MYSQL_SERVICE%" | find "RUNNING" >nul
if errorlevel 1 (
    echo MySQL is not running. Trying to start %MYSQL_SERVICE%...
    net start "%MYSQL_SERVICE%" >nul 2>&1
    sc query "%MYSQL_SERVICE%" | find "RUNNING" >nul
    if errorlevel 1 (
        echo [WARN] Failed to start MySQL automatically. Please start it manually if needed.
    ) else (
        echo [OK] MySQL service started.
    )
) else (
    echo [OK] MySQL service is already running.
)

echo [2/4] Opening Spring Boot window...
start "%SPRING_TITLE%" cmd /k "cd /d ""%SPRINGBOOT_DIR%"" && mvn spring-boot:run"

timeout /t 2 /nobreak >nul

echo [3/4] Opening FastAPI window...
start "%FASTAPI_TITLE%" cmd /k ""%CONDA_BAT%" activate gra && cd /d "%MLP_DIR%" && python FastAPIApp.py"

timeout /t 2 /nobreak >nul

echo [4/4] Opening Vue window...
start "%VUE_TITLE%" cmd /k "cd /d ""%VUE_DIR%"" && npm run dev"

echo [DONE] All three windows have been opened.
exit /b 0
