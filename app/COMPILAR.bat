@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist requirements.txt (
  echo  Arquivos nao encontrados. Descompacte o ZIP inteiro antes
  echo  ^(botao direito no ZIP ^> Extrair tudo^) e rode o .bat de dentro da pasta.
  pause
  exit /b 1
)
title Compilar Printer's 3D Utility
echo.
echo  === Compilando o Printer's 3D Utility ===
echo.
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if not defined PY ( python --version >nul 2>nul && set PY=python )
if not defined PY (
  echo  O Python nao esta instalado neste PC.
  echo.
  echo  1. Baixe em https://www.python.org/downloads/
  echo  2. Na primeira tela da instalacao, marque "Add python.exe to PATH"
  echo  3. Feche esta janela e rode o COMPILAR.bat de novo
  echo.
  start https://www.python.org/downloads/
  pause
  exit /b 1
)
echo  Usando: %PY%
%PY% -m pip install --upgrade pip
%PY% -m pip install pyinstaller -r requirements.txt
if errorlevel 1 ( echo Falha ao instalar dependencias. & pause & exit /b 1 )
%PY% -m PyInstaller --noconfirm Printers3DUtility.spec
if errorlevel 1 ( echo Falha na compilacao. & pause & exit /b 1 )
copy /Y src\modelos_extra.json dist\ >nul
copy /Y src\diagnosticos.json dist\ >nul
echo.
echo  Pronto! O programa esta em: dist\Printers3DUtility.exe
echo  Leve junto o modelos_extra.json (mesma pasta do .exe).
explorer dist
pause
