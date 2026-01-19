#!/usr/bin/env python3
"""
Script de debug para diagnosticar problemas na extração de PDFs
"""
import pdfplumber
import re
import io
from pathlib import Path

def parse_brl_decimal(s: str) -> float:
    """Converte valor brasileiro para float."""
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def debug_pdf_extraction(pdf_path: str):
    """Debug completo da extração de PDF."""
    print(f"\n{'='*80}")
    print(f"DEBUGANDO PDF: {pdf_path}")
    print(f"{'='*80}\n")
    
    # Abrir PDF
    with pdfplumber.open(pdf_path) as pdf:
        print(f"📄 Total de páginas: {len(pdf.pages)}")
        
        texto_completo = ""
        for i, page in enumerate(pdf.pages, 1):
            texto_pagina = page.extract_text()
            texto_completo += texto_pagina + "\n"
            
            print(f"\n--- PÁGINA {i} ---")
            print(f"Caracteres extraídos: {len(texto_pagina)}")
            
            # Mostrar primeiras e últimas linhas
            linhas = texto_pagina.split('\n')
            print(f"Total de linhas: {len(linhas)}")
            
            if linhas:
                print("\n🔝 Primeiras 5 linhas:")
                for linha in linhas[:5]:
                    print(f"  {linha}")
                
                print("\n🔽 Últimas 5 linhas:")
                for linha in linhas[-5:]:
                    print(f"  {linha}")
    
    # Procurar padrões de eventos
    print(f"\n{'='*80}")
    print("PROCURANDO EVENTOS (CÓDIGO DE 3 DÍGITOS)")
    print(f"{'='*80}\n")
    
    eventos_encontrados = 0
    for i, linha in enumerate(texto_completo.split('\n'), 1):
        # Ignorar linhas de cabeçalho
        linha_lower = linha.lower()
        if any(palavra in linha_lower for palavra in [
            'total de', 'adicionais / descontos', 'codigo', 'ativos',
            'demitidos', 'afastados', 'valores pagos', 'tipo processo',
            'resumo geral', 'empresa', 'periodo', 'cnpj', 'endereco',
            'total líquido', 'total de funcionários', 'total de sócios'
        ]):
            continue
        
        # Tentar vários padrões de regex
        patterns = [
            r'^(\d{3})\s+(.+?)\s+([\d.,]+(?:\s+[\d.,]+)*)\s*$',  # Padrão original
            r'(\d{3})\s+(.+?)\s+([\d.,]+)',  # Padrão mais simples
            r'^(\d{3})\s',  # Apenas código
        ]
        
        for idx, pattern in enumerate(patterns):
            match = re.search(pattern, linha.strip())
            if match:
                if eventos_encontrados < 10:  # Mostrar apenas os primeiros 10
                    print(f"✅ Linha {i} (Pattern {idx+1}): {linha.strip()}")
                    print(f"   Código: {match.group(1)}")
                    if len(match.groups()) >= 3:
                        valores_str = match.group(3)
                        valores = re.findall(r'[\d.,]+', valores_str)
                        if valores:
                            print(f"   Valores encontrados: {valores}")
                            print(f"   Último valor (TOTAL): {valores[-1]} = {parse_brl_decimal(valores[-1])}")
                eventos_encontrados += 1
                break
    
    print(f"\n📊 TOTAL DE EVENTOS ENCONTRADOS: {eventos_encontrados}")
    
    # Mostrar algumas linhas que NÃO matchearam
    print(f"\n{'='*80}")
    print("LINHAS QUE NÃO MATCHEARAM (primeiras 20):")
    print(f"{'='*80}\n")
    
    linhas_nao_match = []
    for linha in texto_completo.split('\n'):
        linha = linha.strip()
        if not linha:
            continue
            
        linha_lower = linha.lower()
        if any(palavra in linha_lower for palavra in [
            'total de', 'adicionais / descontos', 'codigo', 'ativos',
            'demitidos', 'afastados', 'valores pagos', 'tipo processo',
            'resumo geral', 'empresa', 'periodo', 'cnpj', 'endereco',
            'total líquido', 'total de funcionários', 'total de sócios'
        ]):
            continue
        
        match = re.search(r'^(\d{3})\s+(.+?)\s+([\d.,]+(?:\s+[\d.,]+)*)\s*$', linha.strip())
        if not match:
            linhas_nao_match.append(linha)
    
    for i, linha in enumerate(linhas_nao_match[:20], 1):
        print(f"{i}. {linha}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python debug_pdf.py <caminho_do_pdf>")
        print("\nPDFs disponíveis no diretório pai:")
        parent_dir = Path(__file__).resolve().parent.parent
        for pdf in parent_dir.glob("*.pdf"):
            print(f"  - {pdf.name}")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    debug_pdf_extraction(pdf_path)
