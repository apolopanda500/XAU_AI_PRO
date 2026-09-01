@echo off
cd /d C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO
.venv\Scripts\python.exe -m py_compile app/main.py
if %errorlevel% equ 0 (
  echo [OK] main.py compila sem erros
) else (
  echo [ERRO] main.py tem problemas de sintaxe
)