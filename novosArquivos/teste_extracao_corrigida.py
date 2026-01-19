#!/usr/bin/env python3
"""
Teste rápido para validar a função de extração corrigida
"""
import pdfplumber
import re
import io
import pandas as pd
from pathlib import Path

def parse_brl_decimal(s: str) -> float:
    """Converte valor brasileiro para float."""
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def extrair_eventos_resumo_simples_corrigido(pdf_bytes: bytes) -> pd.DataFrame:
    """Extrai APENAS código e total de resumos específicos - VERSÃO CORRIGIDA."""
    eventos = []
    linhas_processadas = 0
    linhas_matcheadas = 0

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    print(f"\nProcessando PDF...")
    print(f"Total de caracteres extraídos: {len(texto_completo)}")
    
    for linha in texto_completo.split('\n'):
        linhas_processadas += 1
        
        # Ignorar linhas de cabeçalho e totais
        linha_lower = linha.lower()
        if any(palavra in linha_lower for palavra in [
            'total', 'adicionais', 'descontos', 'codigo', 'ativos',
            'demitidos', 'afastados', 'valores pagos', 'tipo processo',
            'resumo geral', 'empresa', 'periodo', 'cnpj', 'endereco',
            'líquido', 'funcionários', 'sócios', 'base inss', 'base irrf',
            'base fgts', 'evento', 'quantidade', 'valor', 'página', 'emissão'
        ]):
            continue

        # Novo padrão: linhas começam com +/- seguido de código de 3 dígitos
        match = re.search(r'^[+\-]\s+(\d{3})\s+(.+?)\s+([\d.,]+)\s+(\d+)\s*$', linha.strip())

        if match:
            codigo = match.group(1)
            descricao = match.group(2)
            valor_str = match.group(3)
            num_func = match.group(4)
            
            total = parse_brl_decimal(valor_str)

            if total > 0:
                eventos.append({
                    "Codigo": codigo,
                    "Total": abs(total),
                    "Descricao": descricao[:30],  # Truncar para exibição
                    "NumFunc": num_func
                })
                linhas_matcheadas += 1
                
                # Mostrar primeiros 5 eventos como exemplo
                if linhas_matcheadas <= 5:
                    print(f"  ✅ Evento {linhas_matcheadas}: Código {codigo} | Valor: R$ {total:,.2f} | Desc: {descricao[:30]}...")

    print(f"\n📊 ESTATÍSTICAS:")
    print(f"  - Linhas processadas: {linhas_processadas}")
    print(f"  - Linhas matcheadas: {linhas_matcheadas}")
    print(f"  - Eventos extraídos: {len(eventos)}")
    
    return pd.DataFrame(eventos)

if __name__ == "__main__":
    pdf_path = Path(__file__).parent.parent / "Resumo Folha.pdf"
    
    if not pdf_path.exists():
        print(f"❌ PDF não encontrado: {pdf_path}")
        exit(1)
    
    print(f"🔍 Testando extração corrigida em: {pdf_path.name}\n")
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    df = extrair_eventos_resumo_simples_corrigido(pdf_bytes)
    
    print(f"\n📋 RESULTADO FINAL:")
    if df.empty:
        print("❌ Nenhum evento extraído!")
    else:
        print(f"✅ {len(df)} eventos extraídos com sucesso!")
        print(f"\nPrimeiros 10 eventos:")
        print(df.head(10).to_string(index=False))
        
        print(f"\n💰 Soma total dos valores: R$ {df['Total'].sum():,.2f}")
