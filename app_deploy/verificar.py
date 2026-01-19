#!/usr/bin/env python3
"""
Script de verificação do pacote de deploy
Verifica se todos os arquivos necessários estão presentes e válidos
"""

import os
import sys
import json
from pathlib import Path

def check_file(filepath, description):
    """Verifica se um arquivo existe e retorna informações"""
    if not filepath.exists():
        return False, f"❌ {description}: NÃO ENCONTRADO"
    
    size = filepath.stat().st_size
    size_kb = size / 1024
    return True, f"✅ {description}: OK ({size_kb:.1f} KB)"

def main():
    print("=" * 70)
    print("🔍 VERIFICAÇÃO DO PACOTE DE DEPLOY")
    print("=" * 70)
    print()
    
    # Diretório atual
    current_dir = Path.cwd()
    print(f"📁 Diretório: {current_dir}")
    print()
    
    # Lista de arquivos esperados
    arquivos_esperados = {
        "app_resumos.py": "Aplicação principal",
        "mapeamento_dp.json": "Arquivo de mapeamento",
        "requirements.txt": "Dependências Python",
        "README.md": "Documentação",
        "iniciar.sh": "Script de inicialização (Unix)",
        "iniciar.bat": "Script de inicialização (Windows)",
        "DEPLOY_INFO.md": "Informações de deploy"
    }
    
    print("📦 Verificando arquivos...")
    print("-" * 70)
    
    todos_ok = True
    for arquivo, descricao in arquivos_esperados.items():
        filepath = current_dir / arquivo
        ok, msg = check_file(filepath, descricao)
        print(msg)
        if not ok:
            todos_ok = False
    
    print("-" * 70)
    print()
    
    # Verificar conteúdo do mapeamento_dp.json
    mapeamento_path = current_dir / "mapeamento_dp.json"
    if mapeamento_path.exists():
        try:
            with open(mapeamento_path, 'r', encoding='utf-8') as f:
                mapeamento = json.load(f)
            
            print("📊 Conteúdo do mapeamento:")
            print(f"   ✅ Arquivo JSON válido")
            print(f"   ✅ Categorias encontradas: {len(mapeamento)}")
            print(f"   ✅ Categorias: {', '.join(mapeamento.keys())}")
            print()
        except Exception as e:
            print(f"   ⚠️  Erro ao ler mapeamento: {e}")
            print()
            todos_ok = False
    
    # Verificar Python
    print("🐍 Verificando Python:")
    print(f"   ✅ Versão: {sys.version.split()[0]}")
    python_version = sys.version_info
    if python_version.major >= 3 and python_version.minor >= 8:
        print(f"   ✅ Versão compatível (3.8+)")
    else:
        print(f"   ❌ Versão incompatível (necessário 3.8+)")
        todos_ok = False
    print()
    
    # Verificar dependências
    print("📦 Verificando dependências:")
    dependencias = ["streamlit", "pandas", "pdfplumber"]
    deps_ok = True
    for dep in dependencias:
        try:
            __import__(dep)
            print(f"   ✅ {dep}: instalado")
        except ImportError:
            print(f"   ⚠️  {dep}: NÃO instalado")
            deps_ok = False
    
    if not deps_ok:
        print()
        print("   💡 Para instalar dependências, execute:")
        print("      pip install -r requirements.txt")
    print()
    
    # Resultado final
    print("=" * 70)
    if todos_ok and deps_ok:
        print("✅ VERIFICAÇÃO COMPLETA - TUDO OK!")
        print()
        print("🚀 Você pode iniciar a aplicação com:")
        print("   ./iniciar.sh (Linux/Mac)")
        print("   iniciar.bat (Windows)")
        print("   OU")
        print("   streamlit run app_resumos.py")
    elif todos_ok and not deps_ok:
        print("⚠️  ARQUIVOS OK - INSTALE AS DEPENDÊNCIAS")
        print()
        print("Execute: pip install -r requirements.txt")
    else:
        print("❌ VERIFICAÇÃO FALHOU - ARQUIVOS FALTANDO")
        print()
        print("Certifique-se de que todos os arquivos estão no diretório.")
    print("=" * 70)

if __name__ == "__main__":
    main()
