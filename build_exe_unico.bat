@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%CD%\build_exe_unico.log"
set "VENV=%CD%\.venv-build"
set "VENV_PY=%VENV%\Scripts\python.exe"

echo ==================================================
echo  Gestao Financeira V12.1.3 - Gerar EXE unico
echo ==================================================
echo.
echo Para uso diario, prefira build_exe.bat (modo pasta).
echo O log completo sera salvo em build_exe_unico.log.
echo.

> "%LOG%" echo ===== BUILD ONEFILE GESTAO FINANCEIRA =====
>> "%LOG%" echo Pasta: %CD%
>> "%LOG%" echo Data: %DATE% %TIME%

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; print(sys.executable)" >> "%LOG%" 2>&1
    if not errorlevel 1 (
        set "PY_KIND=launcher"
        goto :python_ok
    )
)
where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; print(sys.executable)" >> "%LOG%" 2>&1
    if not errorlevel 1 (
        set "PY_KIND=python"
        goto :python_ok
    )
)

echo ERRO: Python nao foi encontrado.
goto :erro

:python_ok
if "%PY_KIND%"=="launcher" (
    if not exist "%VENV_PY%" py -3 -m venv "%VENV%" >> "%LOG%" 2>&1
) else (
    if not exist "%VENV_PY%" python -m venv "%VENV%" >> "%LOG%" 2>&1
)
if errorlevel 1 goto :erro

"%VENV_PY%" -c "import tkinter; print('Tkinter OK')" >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

"%VENV_PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 goto :erro
"%VENV_PY%" -m pip install -r requirements-build.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

if exist build_unico rmdir /s /q build_unico >> "%LOG%" 2>&1
if exist dist_unico rmdir /s /q dist_unico >> "%LOG%" 2>&1
if exist GestaoFinanceira.spec del /q GestaoFinanceira.spec >> "%LOG%" 2>&1

echo Gerando o executavel unico...
"%VENV_PY%" -m PyInstaller --noconfirm --clean --windowed --onefile ^
  --name GestaoFinanceira ^
  --distpath dist_unico ^
  --workpath build_unico ^
  --specpath build_unico ^
  --paths "%CD%" ^
  main.py >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

if not exist "%CD%\dist_unico\GestaoFinanceira.exe" goto :erro

echo.
echo EXE unico criado com sucesso em:
echo %CD%\dist_unico\GestaoFinanceira.exe
echo.
pause
exit /b 0

:erro
echo.
echo FALHA AO GERAR O EXECUTAVEL.
echo Ultimas linhas do erro:
echo ------------------------------------------------
powershell -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content -Path '%LOG%' -Tail 35 }" 2>nul
if errorlevel 1 type "%LOG%"
echo ------------------------------------------------
echo Log completo: %LOG%
echo Envie esse arquivo se ainda houver falha.
pause
exit /b 1
