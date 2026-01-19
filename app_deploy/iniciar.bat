@echo off
REM Script de inicialização rápida para a aplicação de processamento de resumos DP (Windows)

echo 🚀 Iniciando Sistema de Processamento de Resumos DP...
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado. Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

echo ✅ Python encontrado
python --version
echo.

REM Verificar se as dependências estão instaladas
echo 📦 Verificando dependências...
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Dependências não encontradas. Instalando...
    pip install -r requirements.txt
) else (
    echo ✅ Dependências já instaladas
)

echo.
echo 🌟 Iniciando aplicação Streamlit...
echo 📍 A aplicação abrirá em: http://localhost:8501
echo.

REM Iniciar a aplicação
streamlit run app_resumos.py

pause
