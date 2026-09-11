@echo off
rem ============================================================
rem XAU_AI_PRO - BUILD LIGHTWEIGHT (.exe ~50 MB em vez de 185 MB)
rem ============================================================
rem
rem Remove libs pesadas de IA que NAO fazem parte da GUI:
rem   streamlit, altair, uvicorn, fastapi, catboost, lightgbm,
rem   xgboost, scikit-learn, scipy, plotly, huggingface_hub
rem
rem Mantem apenas o essencial para a Trading Desk:
rem   tkinter, MetaTrader5, Pillow, matplotlib, requests
rem ============================================================

echo === Criando venv limpo ===
if exist .venv_light rmdir /s /q .venv_light
python -m venv .venv_light

echo === Instalando apenas o essencial ===
.venv_light\Scripts\python -m pip install --upgrade pip
.venv_light\Scripts\pip install ^
    MetaTrader5==5.0.6147 ^
    Pillow==12.3.0 ^
    matplotlib==3.11.1 ^
    requests==2.34.2 ^
    python-dotenv==1.2.3 ^
    sentry-sdk==2.68.1 ^
    pyinstaller==6.22.2

echo === Verificando tamanho ===
.venv_light\Scripts\pip list

echo === Build PyInstaller (launcher.spec) ===
.venv_light\Scripts\python -m PyInstaller --noconfirm launcher.spec

echo === Build completo ===
dir /b dist\*.exe
