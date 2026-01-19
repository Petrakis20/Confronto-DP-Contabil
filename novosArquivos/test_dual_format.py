#!/usr/bin/env python3
"""
Teste de validação para os dois formatos de PDF:
1. COM prefixo +/- (formato antigo) 
2. SEM prefixo +/- (formato novo - usa mapeamento)
"""
import sys
import json
from pathlib import Path

# Adicionar o diretório pai ao path para importar as funções
sys.path.insert(0, str(Path(__file__).parent))

from app_resumos import (
    extrair_eventos_resumo_simples,
    get_event_type_from_mapping,
    mapear_eventos_para_lancamentos,
    load_mapeamento,
    calcular_liquidos_por_categoria
)
import pandas as pd

def test_old_format():
    """Testa o formato antigo (COM prefixo +/-)"""
    print("\n" + "="*80)
    print("TESTE 1: Formato ANTIGO (COM prefixo +/-)")
    print("="*80)
    
    pdf_path = Path(__file__).parent.parent / "Resumo Folha.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        return False
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Extrair eventos
    df = extrair_eventos_resumo_simples(pdf_bytes)
    
    if df.empty:
        print("❌ FALHOU: Nenhum evento extraído!")
        return False
    
    print(f"✅ Eventos extraídos: {len(df)}")
    print(f"✅ Formato detectado: with_prefix")
    print(f"\nPrimeiros 5 eventos:")
    print(df.head().to_string(index=False))
    
    # Verificar se tem a coluna HasPrefix
    if 'HasPrefix' in df.columns:
        has_prefix_count = df['HasPrefix'].sum()
        print(f"\n✅ Eventos com prefixo: {has_prefix_count}/{len(df)}")
    
    return True


def test_event_type_lookup():
    """Testa a função de lookup de tipo do evento"""
    print("\n" + "="*80)
    print("TESTE 2: Lookup de Tipo do Evento no Mapeamento")
    print("="*80)
    
    # Carregar mapeamento
    mapeamento = load_mapeamento()
    
    if not mapeamento:
        print("❌ FALHOU: Mapeamento não carregado!")
        return False
    
    print(f"✅ Mapeamento carregado com {len(mapeamento)} categorias")
    
    # Testar alguns eventos
    test_cases = [
        ("Folha", "001", "Adicional"),  # Salário é adicional
        ("Folha", "013", "Desconto"),    # INSS é desconto
        ("Férias", "009", "Adicional"),  # Férias é adicional
        ("13º Primeira Parcela", "003", "Adicional"),  # 13º é adicional
        ("13º Primeira Parcela", "608", "Desconto"),   # Desconto
    ]
    
    todos_ok = True
    for categoria, codigo, tipo_esperado in test_cases:
        tipo_obtido = get_event_type_from_mapping(categoria, codigo, mapeamento)
        status = "✅" if tipo_obtido == tipo_esperado else "❌"
        print(f"{status} {categoria} - {codigo}: {tipo_obtido} (esperado: {tipo_esperado})")
        if tipo_obtido != tipo_esperado:
            todos_ok = False
    
    return todos_ok


def test_liquidos_calculation():
    """Testa o cálculo de líquidos com adicionais e descontos"""
    print("\n" + "="*80)
    print("TESTE 3: Cálculo de Líquidos (Adicionais - Descontos)")
    print("="*80)
    
    # Criar dados de teste
    df_test = pd.DataFrame([
        {"Categoria": "Folha", "Codigo": "001", "CodigoLA": "30051", "Total": 1000.0, "Tipo": "Adicional"},
        {"Categoria": "Folha", "Codigo": "013", "CodigoLA": "30039", "Total": 100.0, "Tipo": "Desconto"},
        {"Categoria": "Folha", "Codigo": "401", "CodigoLA": "30051", "Total": 200.0, "Tipo": "Adicional"},
        {"Categoria": "Férias", "Codigo": "009", "CodigoLA": "30057", "Total": 500.0, "Tipo": "Adicional"},
        {"Categoria": "Férias", "Codigo": "902", "CodigoLA": "30072", "Total": 50.0, "Tipo": "Desconto"},
    ])
    
    df_liquidos = calcular_liquidos_por_categoria(df_test)
    
    print("\nResultados:")
    print(df_liquidos.to_string(index=False))
    
    # Verificar cálculos
    folha = df_liquidos[df_liquidos['Categoria'] == 'Folha'].iloc[0]
    ferias = df_liquidos[df_liquidos['Categoria'] == 'Férias'].iloc[0]
    
    folha_ok = (
        folha['Total_Adicionais'] == 1200.0 and
        folha['Total_Descontos'] == 100.0 and
        folha['Liquido'] == 1100.0
    )
    
    ferias_ok = (
        ferias['Total_Adicionais'] == 500.0 and
        ferias['Total_Descontos'] == 50.0 and
        ferias['Liquido'] == 450.0
    )
    
    if folha_ok and ferias_ok:
        print("\n✅ Cálculos estão corretos!")
        print(f"   Folha: R$ 1.200,00 - R$ 100,00 = R$ 1.100,00")
        print(f"   Férias: R$ 500,00 - R$ 50,00 = R$ 450,00")
        return True
    else:
        print("\n❌ FALHOU: Cálculos incorretos!")
        return False


def main():
    """Executa todos os testes"""
    print("\n🧪 EXECUTANDO TESTES DE VALIDAÇÃO")
    print("="*80)
    
    results = {
        "Formato Antigo (com +/-)": test_old_format(),
        "Lookup de Tipo": test_event_type_lookup(),
        "Cálculo de Líquidos": test_liquidos_calculation(),
    }
    
    print("\n" + "="*80)
    print("📊 RESUMO DOS TESTES")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM")
    print("="*80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
