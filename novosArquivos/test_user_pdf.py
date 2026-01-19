#!/usr/bin/env python3
"""
Teste com o PDF real do usuário (formato novo com múltiplos valores)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app_resumos import extrair_eventos_resumo_simples
import pandas as pd

def test_user_pdf():
    """Testa o formato real do usuário"""
    print("\n" + "="*80)
    print("TESTE: Formato REAL do Usuário (múltiplos valores)")
    print("="*80)
    
    pdf_path = Path(__file__).parent / "Resumo_de_folha_00861_2025-11.pdf"
    
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
    print(f"\nPrimeiros 10 eventos:")
    print(df.head(10).to_string(index=False))
    
    print(f"\n💰 Soma total dos valores: R$ {df['Total'].sum():,.2f}")
    
    # Verificar alguns eventos específicos
    if '001' in df['Codigo'].values:
        valor_001 = df[df['Codigo'] == '001']['Total'].iloc[0]
        print(f"\n✅ Código 001 (Salário Base): R$ {valor_001:,.2f}")
        
        # Deve ser próximo de 197.791,51
        if abs(valor_001 - 197791.51) < 1.0:
            print("   ✅ Valor correto!")
            return True
        else:
            print(f"   ❌ Valor esperado: R$ 197.791,51, obtido: R$ {valor_001:,.2f}")
            return False
    
    return True

if __name__ == "__main__":
    success = test_user_pdf()
    exit(0 if success else 1)
