@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG=%CD%\build_exe.log"
set "VENV=%CD%\.venv-build"
set "VENV_PY=%VENV%\Scripts\python.exe"

echo ===============================================
echo  Gestao Financeira V12.1.3 - Gerar EXE (pasta)
echo ===============================================
echo.
echo A pasta gerada em dist\GestaoFinanceira e a opcao recomendada.
echo O log completo sera salvo em build_exe.log.
echo.

> "%LOG%" echo ===== BUILD GESTAO FINANCEIRA =====
>> "%LOG%" echo Pasta: %CD%
>> "%LOG%" echo Data: %DATE% %TIME%

rem Localiza uma instalacao REAL do Python.
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

echo ERRO: Python nao foi encontrado ou o atalho do Windows nao aponta para uma instalacao real.
echo Instale Python 3 pelo site oficial python.org e marque "Add python.exe to PATH".
echo.
goto :erro_sem_log

:python_ok
if "%PY_KIND%"=="launcher" (
    py -3 --version
    if not exist "%VENV_PY%" py -3 -m venv "%VENV%" >> "%LOG%" 2>&1
) else (
    python --version
    if not exist "%VENV_PY%" python -m venv "%VENV%" >> "%LOG%" 2>&1
)
if errorlevel 1 goto :erro

if not exist "%VENV_PY%" (
    echo ERRO: o ambiente de compilacao nao foi criado.
    goto :erro
)

rem Confirma que esta instalacao do Python possui Tkinter/Tcl-Tk.
"%VENV_PY%" -c "import tkinter; print('Tkinter OK')" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo ERRO: esta instalacao do Python nao possui Tkinter funcionando.
    echo Veja build_exe.log para detalhes.
    goto :erro
)

echo Preparando PyInstaller...
"%VENV_PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
if errorlevel 1 goto :erro
"%VENV_PY%" -m pip install -r requirements-build.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

if exist build (
    rmdir /s /q build >> "%LOG%" 2>&1
    if exist build (
        echo ERRO: nao foi possivel apagar a pasta build. Feche arquivos/programas que estejam usando essa pasta.
        goto :erro
    )
)
if exist dist (
    rmdir /s /q dist >> "%LOG%" 2>&1
    if exist dist (
        echo ERRO: nao foi possivel apagar a pasta dist. Feche GestaoFinanceira.exe antes de compilar novamente.
        goto :erro
    )
)
if exist GestaoFinanceira.spec del /q GestaoFinanceira.spec >> "%LOG%" 2>&1

echo Gerando o executavel...
rem Nao usamos --version-file no build principal. Metadados de versao sao opcionais
rem e nao devem impedir a criacao do programa.
"%VENV_PY%" -m PyInstaller --noconfirm --clean --windowed --onedir ^
  --name GestaoFinanceira ^
  --paths "%CD%" ^
  main.py >> "%LOG%" 2>&1
if errorlevel 1 goto :erro

if not exist "%CD%\dist\GestaoFinanceira\GestaoFinanceira.exe" (
    echo ERRO: o PyInstaller terminou sem criar o arquivo esperado.
    goto :erro
)

echo.
echo ===============================================
echo  EXE CRIADO COM SUCESSO
echo ===============================================
echo.
echo Arquivo:
echo %CD%\dist\GestaoFinanceira\GestaoFinanceira.exe
echo.
echo IMPORTANTE: copie a pasta GestaoFinanceira INTEIRA para o PC da empresa.
echo Os dados continuam em %%APPDATA%%\GestaoEmpresasLocal.
echo.
pause
exit /b 0

:erro
echo.
echo ===============================================
echo  FALHA AO GERAR O EXECUTAVEL
echo ===============================================
echo.
echo Ultimas linhas do erro:
echo ------------------------------------------------
powershell -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content -Path '%LOG%' -Tail 35 }" 2>nul
if errorlevel 1 type "%LOG%"
echo ------------------------------------------------
echo.
echo Log completo salvo em:
echo %LOG%
echo.
echo Se precisar de ajuda, envie o arquivo build_exe.log.
pause
exit /b 1

:erro_sem_log
echo.
echo Log parcial salvo em:
echo %LOG%
pause
exit /b 1
