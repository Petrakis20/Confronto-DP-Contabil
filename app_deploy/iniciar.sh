#!/bin/bash
# Script de inicialização rápida para a aplicação de processamento de resumos DP

echo "🚀 Iniciando Sistema de Processamento de Resumos DP..."
echo ""

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale o Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Verificar se as dependências estão instaladas
echo "📦 Verificando dependências..."
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️  Dependências não encontradas. Instalando..."
    pip3 install -r requirements.txt
else
    echo "✅ Dependências já instaladas"
fi

echo ""
echo "🌟 Iniciando aplicação Streamlit..."
echo "📍 A aplicação abrirá em: http://localhost:8501"
echo ""

# Iniciar a aplicação
streamlit run app_resumos.py
