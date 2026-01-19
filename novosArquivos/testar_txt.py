#!/usr/bin/env python3
"""
Script de teste para verificar formato do arquivo TXT
Uso: python3 testar_txt.py arquivo.txt
"""

import sys
from pathlib import Path

def testar_txt(arquivo_path):
    """Testa e exibe informações sobre o arquivo TXT."""
    print("=" * 80)
    print("TESTE DE FORMATO DO ARQUIVO TXT")
    print("=" * 80)
    print(f"\nArquivo: {arquivo_path}")

    # Ler arquivo
    with open(arquivo_path, 'r', encoding='utf-8', errors='ignore') as f:
        linhas = f.readlines()

    print(f"Total de linhas: {len(linhas)}")
    print("\n" + "=" * 80)
    print("PRIMEIRAS 10 LINHAS:")
    print("=" * 80)

    for i, linha in enumerate(linhas[:10], 1):
        print(f"\n--- Linha {i} ---")
        print(f"Conteúdo: {linha[:100]}{'...' if len(linha) > 100 else ''}")

        # Detectar separador
        if ';' in linha:
            separador = ';'
            partes = linha.split(';')
        elif '\t' in linha:
            separador = 'TAB'
            partes = linha.split('\t')
        elif ',' in linha:
            separador = ','
            partes = linha.split(',')
        else:
            print("❌ Nenhum separador detectado")
            continue

        print(f"Separador detectado: '{separador}'")
        print(f"Número de colunas: {len(partes)}")

        if len(partes) >= 4:
            col_1 = partes[0].strip()[:30]
            col_2 = partes[1].strip()[:30]  # Código LA
            col_3 = partes[2].strip()[:30]
            col_4 = partes[3].strip()[:30]  # Valor

            print(f"  Coluna 1 (índice 0): '{col_1}'")
            print(f"  Coluna 2 (índice 1) [CÓDIGO LA]: '{col_2}' → Numérico: {partes[1].strip().isdigit()}, Tam: {len(partes[1].strip())}")
            print(f"  Coluna 3 (índice 2): '{col_3}'")
            print(f"  Coluna 4 (índice 3) [VALOR]: '{col_4}'")

            # Validar código LA
            codigo_la = partes[1].strip()
            if codigo_la.isdigit() and len(codigo_la) >= 4:
                print(f"  ✅ Código LA válido: {codigo_la}")
            else:
                print(f"  ❌ Código LA inválido (precisa ser numérico com 4+ dígitos)")
        else:
            print(f"  ❌ Número insuficiente de colunas (esperado: >= 4, encontrado: {len(partes)})")

    print("\n" + "=" * 80)
    print("ANÁLISE GERAL:")
    print("=" * 80)

    # Contar linhas válidas
    linhas_validas = 0
    separadores = {';': 0, ',': 0, '\t': 0}

    for linha in linhas:
        if not linha.strip():
            continue

        # Detectar separador
        if ';' in linha:
            separadores[';'] += 1
            partes = linha.split(';')
        elif '\t' in linha:
            separadores['\t'] += 1
            partes = linha.split('\t')
        elif ',' in linha:
            separadores[','] += 1
            partes = linha.split(',')
        else:
            continue

        if len(partes) < 4:
            continue

        codigo_la = partes[1].strip()
        if codigo_la.isdigit() and len(codigo_la) >= 4:
            linhas_validas += 1

    print(f"Linhas válidas encontradas: {linhas_validas}")
    print(f"Separadores detectados:")
    for sep, count in separadores.items():
        sep_name = 'TAB' if sep == '\t' else sep
        if count > 0:
            print(f"  - '{sep_name}': {count} linhas")

    if linhas_validas == 0:
        print("\n❌ PROBLEMA: Nenhuma linha válida encontrada!")
        print("\n🔍 Verifique:")
        print("  1. O separador está correto? (deve ser ;, , ou TAB)")
        print("  2. A coluna 2 (índice 1) contém códigos LA numéricos com 4+ dígitos?")
        print("  3. A coluna 4 (índice 3) contém os valores?")
        print("  4. O arquivo tem pelo menos 4 colunas?")
    else:
        print(f"\n✅ Arquivo parece estar no formato correto!")
        print(f"   {linhas_validas} lançamentos podem ser extraídos")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 testar_txt.py arquivo.txt")
        sys.exit(1)

    arquivo = Path(sys.argv[1])

    if not arquivo.exists():
        print(f"❌ Arquivo não encontrado: {arquivo}")
        sys.exit(1)

    testar_txt(arquivo)
