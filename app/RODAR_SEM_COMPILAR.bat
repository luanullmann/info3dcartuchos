@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist requirements.txt (
  echo  Arquivos nao encontrados. Descompacte o ZIP inteiro antes
  echo  ^(botao direito no ZIP ^> Extrair tudo^) e rode o .bat de dentro da pasta.
  pause
  exit /b 1
)
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if not defined PY ( python --version >nul 2>nul && set PY=python )
if not defined PY ( echo Instale o Python em python.org marcando "Add python.exe to PATH". & pause & exit /b 1 )
%PY% -m pip install -r requirements.txt
%PY% src\printers3d.py
