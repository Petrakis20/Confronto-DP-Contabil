#!/usr/bin/env python3
"""
Sistema Moderno de Processamento de Resumos DP
------------------------------------------------
Processa diferentes tipos de resumos:
- Resumo 13º → Categoria "13ª parcela"
- Resumo Adiantamento → Categoria "Adiantamento"
- Resumo Férias → Categoria "Férias"
- Resumo Folha → Categoria "Folha"
- Resumo Rescisão → Categoria "Rescisão"
- Resumo Geral → Extrai impostos consolidados

Realiza confronto entre eventos extraídos dos PDFs e lançamentos do TXT contábil.

Uso: python3 processar_resumos_modernos.py [arquivo.txt]
"""

import pdfplumber
import pandas as pd
import re
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ==================== CONFIGURAÇÕES ====================

PDF_FOLDER = Path(__file__).parent
OUTPUT_EXCEL = PDF_FOLDER / f"confronto_dp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
MAPEAMENTO_JSON = PDF_FOLDER.parent / "mapeamento_dp.json"

# Aceitar arquivo TXT como argumento
TXT_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else None


# ==================== FUNÇÕES AUXILIARES ====================

def normalize_text(s: str) -> str:
    """Remove acentos e normaliza texto."""
    if not s:
        return ""
    subs = {
        "ç": "c", "Ç": "C",
        "á": "a", "à": "a", "ä": "a", "â": "a", "ã": "a",
        "Á": "A", "À": "A", "Ä": "A", "Â": "A", "Ã": "A",
        "é": "e", "ê": "e", "É": "E", "Ê": "E",
        "í": "i", "î": "i", "Í": "I", "Î": "I",
        "ó": "o", "ô": "o", "ö": "o", "õ": "o",
        "Ó": "O", "Ô": "O", "Ö": "O", "Õ": "O",
        "ú": "u", "ü": "u", "Ú": "U", "Ü": "U",
    }
    for k, v in subs.items():
        s = s.replace(k, v)
    return s.lower().strip()


def parse_brl_decimal(s: str) -> float:
    """Converte valor brasileiro para float."""
    s = (s or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


def load_mapeamento() -> dict:
    """Carrega o mapeamento de eventos para lançamentos."""
    if not MAPEAMENTO_JSON.exists():
        print(f"⚠️  Arquivo de mapeamento não encontrado: {MAPEAMENTO_JSON}")
        return {}

    with open(MAPEAMENTO_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_txt_lancamentos(txt_path: Path) -> pd.DataFrame:
    """
    Extrai lançamentos do arquivo TXT/CSV contábil.
    Formato esperado: coluna 2 = código LA, coluna 4 = valor
    Retorna DataFrame: [CodigoLA, Valor]
    """
    import csv

    if not txt_path or not txt_path.exists():
        return pd.DataFrame(columns=['CodigoLA', 'Valor'])

    lancamentos = []

    # Detectar separador lendo primeira linha
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        primeira_linha = f.readline()

    if primeira_linha.count(';') > primeira_linha.count(','):
        delimiter = ';'
    elif primeira_linha.count('\t') > 0:
        delimiter = '\t'
    else:
        delimiter = ','

    # Usar csv.reader para parsing correto de campos com aspas
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f, delimiter=delimiter, quotechar='"')

        for partes in reader:
            if not partes or len(partes) < 4:
                continue

            # Coluna 2 (índice 1): código LA
            # Coluna 4 (índice 3): valor
            codigo_la = partes[1].strip() if len(partes) > 1 else ""
            valor_str = partes[3].strip() if len(partes) > 3 else ""

            # Validar código LA (numérico, >= 4 dígitos)
            codigo_la = codigo_la.strip('"').strip("'").strip()

            if not codigo_la or not codigo_la.isdigit() or len(codigo_la) < 4:
                continue

            # Parsear valor (já vem sem aspas do csv.reader)
            try:
                valor = parse_brl_decimal(valor_str)
            except:
                continue

            if valor != 0:  # Incluir valores positivos e negativos
                lancamentos.append({
                    'CodigoLA': codigo_la,
                    'Valor': abs(valor)
                })

    return pd.DataFrame(lancamentos)


def mapear_eventos_para_lancamentos(df_eventos: pd.DataFrame, mapeamento: dict) -> pd.DataFrame:
    """
    Mapeia eventos do PDF para códigos de lançamento usando mapeamento_dp.json.

    Args:
        df_eventos: DataFrame com [Codigo, Total, Categoria]
        mapeamento: Dict carregado do mapeamento_dp.json

    Returns:
        DataFrame com [Categoria, Codigo, CodigoLA, Total, Tipo]
    """
    resultados = []

    for _, row in df_eventos.iterrows():
        categoria = row['Categoria']
        codigo_evento = str(row['Codigo']).zfill(3)  # Garantir 3 dígitos
        total = row['Total']

        # Buscar mapeamento para esta categoria
        if categoria not in mapeamento:
            # Evento sem categoria mapeada
            resultados.append({
                'Categoria': categoria,
                'Codigo': codigo_evento,
                'CodigoLA': None,
                'Total': total,
                'Tipo': 'Sem Mapeamento'
            })
            continue

        # Procurar evento no mapeamento da categoria
        eventos_categoria = mapeamento[categoria]
        encontrado = False

        for item in eventos_categoria:
            if item['evento'] == codigo_evento:
                resultados.append({
                    'Categoria': categoria,
                    'Codigo': codigo_evento,
                    'CodigoLA': item['codigo_lancamento'],
                    'Total': total,
                    'Tipo': item.get('tipo', 'Desconhecido')
                })
                encontrado = True
                break

        if not encontrado:
            # Evento não encontrado no mapeamento
            resultados.append({
                'Categoria': categoria,
                'Codigo': codigo_evento,
                'CodigoLA': None,
                'Total': total,
                'Tipo': 'Não Mapeado'
            })

    return pd.DataFrame(resultados)


def identificar_tipo_resumo(nome_arquivo: str) -> str:
    """
    Identifica o tipo de resumo pelo nome do arquivo.

    Returns:
        - "13ª parcela" para arquivos com 13º/13/13a
        - "Adiantamento" para arquivos com "adiantamento"
        - "Férias" para arquivos com "ferias"
        - "Folha" para arquivos com "folha"
        - "Rescisão" para arquivos com "rescisao"
        - "Geral" para arquivos com "geral"
    """
    nome_norm = normalize_text(nome_arquivo)

    if any(palavra in nome_norm for palavra in ["13", "decimo"]):
        return "13ª parcela"
    elif "adiantamento" in nome_norm:
        return "Adiantamento"
    elif "ferias" in nome_norm:
        return "Férias"
    elif "folha" in nome_norm and "geral" not in nome_norm:
        return "Folha"
    elif "rescisao" in nome_norm:
        return "Rescisão"
    elif "geral" in nome_norm:
        return "Geral"

    return "Desconhecido"


# ==================== EXTRAÇÃO DE RESUMOS ESPECÍFICOS ====================

def extrair_eventos_resumo_simples(pdf_path: Path) -> pd.DataFrame:
    """
    Extrai APENAS código e total de resumos específicos usando regex.
    Retorna DataFrame: [Codigo, Total]
    """
    eventos = []

    with pdfplumber.open(pdf_path) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # Padrão: código de 3 dígitos + descrição + valores + valor final
    # Exemplo: "001 Salário Base 197.791,51 0,00 0,00 197.791,51"
    # Captura: código (3 dígitos) e último valor (coluna TOTAL)

    for linha in texto_completo.split('\n'):
        # Ignorar linhas de cabeçalho e totais
        linha_lower = linha.lower()
        if any(palavra in linha_lower for palavra in [
            'total de', 'adicionais / descontos', 'codigo', 'ativos',
            'demitidos', 'afastados', 'valores pagos', 'tipo processo',
            'resumo geral', 'empresa', 'periodo', 'cnpj', 'endereco',
            'total líquido', 'total de funcionários', 'total de sócios'
        ]):
            continue

        # Procurar padrão: código (3 dígitos) seguido de texto e valores
        match = re.search(r'^(\d{3})\s+(.+?)\s+([\d.,]+(?:\s+[\d.,]+)*)\s*$', linha.strip())

        if match:
            codigo = match.group(1)
            valores_str = match.group(3)

            # Pegar o último valor (coluna TOTAL)
            valores = re.findall(r'[\d.,]+', valores_str)
            if valores:
                total_str = valores[-1]
                total = parse_brl_decimal(total_str)

                if total > 0:
                    eventos.append({
                        "Codigo": codigo,
                        "Total": abs(total)
                    })

    return pd.DataFrame(eventos)


# ==================== EXTRAÇÃO DO RESUMO GERAL ====================

def extrair_impostos_resumo_geral(pdf_path: Path) -> dict:
    """
    Extrai impostos consolidados do Resumo Geral:
    - INSS - Total Líquido
    - FGTS - Total apurado recibos s/CS
    - IRRF - Soma de (Folha + Férias + Rescisão + Sócio + Autônomo)
    - Pró-Labore Sócios (Líquido)
    - Pró-Labore Autônomos (Líquido)
    """
    impostos = {
        "INSS_Total_Liquido": 0.0,
        "FGTS_Total_Apurado": 0.0,
        "IRRF_Folha": 0.0,
        "IRRF_Ferias": 0.0,
        "IRRF_Rescisao": 0.0,
        "IRRF_Socio": 0.0,
        "IRRF_Autonomo": 0.0,
        "IRRF_Total": 0.0,
        "ProLabore_Socios_Liquido": 0.0,
        "ProLabore_Autonomos_Liquido": 0.0,
    }

    with pdfplumber.open(pdf_path) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # INSS - Total Líquido
    match = re.search(r'Total Líquido\s*:?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
    if match:
        impostos["INSS_Total_Liquido"] = parse_brl_decimal(match.group(1))

    # FGTS - Total apurado recibos s/CS
    match = re.search(r'Total FGTS apurado recibos s/CS\s*:?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
    if match:
        impostos["FGTS_Total_Apurado"] = parse_brl_decimal(match.group(1))

    # IRRF - Procurar na seção DARF IR
    match_darf = re.search(r'DARF IR.*?OUTRAS INFORMAÇÕES', texto_completo, re.DOTALL | re.IGNORECASE)
    if match_darf:
        secao_darf = match_darf.group(0)

        match_folha = re.search(r'IRRF Folha\s*:?\s*([\d.,]+)', secao_darf)
        if match_folha:
            impostos["IRRF_Folha"] = parse_brl_decimal(match_folha.group(1))

        match_ferias = re.search(r'IRRF Férias\s*:?\s*([\d.,]+)', secao_darf)
        if match_ferias:
            impostos["IRRF_Ferias"] = parse_brl_decimal(match_ferias.group(1))

        match_rescisao = re.search(r'IRRF Rescisão\s*:?\s*([\d.,]+)', secao_darf)
        if match_rescisao:
            impostos["IRRF_Rescisao"] = parse_brl_decimal(match_rescisao.group(1))

        match_socio = re.search(r'IRRF Sócio\s*:?\s*([\d.,]+)', secao_darf)
        if match_socio:
            impostos["IRRF_Socio"] = parse_brl_decimal(match_socio.group(1))

        match_autonomo = re.search(r'IRRF Autônomo\s*:?\s*([\d.,]+)', secao_darf)
        if match_autonomo:
            impostos["IRRF_Autonomo"] = parse_brl_decimal(match_autonomo.group(1))

    # Calcular IRRF Total
    impostos["IRRF_Total"] = sum([
        impostos["IRRF_Folha"],
        impostos["IRRF_Ferias"],
        impostos["IRRF_Rescisao"],
        impostos["IRRF_Socio"],
        impostos["IRRF_Autonomo"]
    ])

    # Pró-Labore - Seção Sócios/Autônomos
    match_secao = re.search(
        r'Valores pagos aos Sócios.*?TOTAL DE SÓCIOS',
        texto_completo,
        re.DOTALL | re.IGNORECASE
    )

    if match_secao:
        secao = match_secao.group(0)

        # Bruto
        match_prolabore = re.search(r'003\s+PRO LABORE\s+([\d.,]+)\s+([\d.,]+)', secao)
        pro_labore_bruto_socios = 0.0
        pro_labore_bruto_autonomos = 0.0

        if match_prolabore:
            pro_labore_bruto_socios = parse_brl_decimal(match_prolabore.group(1))
            pro_labore_bruto_autonomos = parse_brl_decimal(match_prolabore.group(2))

        # INSS
        match_inss = re.search(r'013\s+INSS\s+([\d.,]+)\s+([\d.,]+)', secao)
        inss_socios = 0.0
        inss_autonomos = 0.0

        if match_inss:
            inss_socios = parse_brl_decimal(match_inss.group(1))
            inss_autonomos = parse_brl_decimal(match_inss.group(2))

        # Calcular líquido
        impostos["ProLabore_Socios_Liquido"] = pro_labore_bruto_socios - inss_socios
        impostos["ProLabore_Autonomos_Liquido"] = pro_labore_bruto_autonomos - inss_autonomos

    return impostos


def realizar_confronto(df_eventos_mapeados: pd.DataFrame, df_lancamentos: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza confronto entre eventos mapeados (PDF) e lançamentos (TXT).

    Args:
        df_eventos_mapeados: DataFrame com [Categoria, Codigo, CodigoLA, Total, Tipo]
        df_lancamentos: DataFrame com [CodigoLA, Valor]

    Returns:
        DataFrame com [CodigoLA, Categoria, Total_PDF, Total_TXT, Diferenca, Status]
    """
    # Agrupar eventos por LA
    pdf_por_la = df_eventos_mapeados[df_eventos_mapeados['CodigoLA'].notna()].groupby('CodigoLA').agg({
        'Total': 'sum',
        'Categoria': lambda x: ', '.join(sorted(set(x)))
    }).reset_index()
    pdf_por_la.columns = ['CodigoLA', 'Categoria', 'Total_PDF']

    # Agrupar lançamentos por LA
    txt_por_la = df_lancamentos.groupby('CodigoLA')['Valor'].sum().reset_index()
    txt_por_la.columns = ['CodigoLA', 'Total_TXT']

    # Merge completo (outer join)
    confronto = pd.merge(pdf_por_la, txt_por_la, on='CodigoLA', how='outer')

    # Preencher NaN com 0
    confronto['Total_PDF'] = confronto['Total_PDF'].fillna(0)
    confronto['Total_TXT'] = confronto['Total_TXT'].fillna(0)
    confronto['Categoria'] = confronto['Categoria'].fillna('Sem Categoria')

    # Calcular diferença
    confronto['Diferenca'] = confronto['Total_PDF'] - confronto['Total_TXT']

    # Determinar status
    def determinar_status(row):
        if abs(row['Diferenca']) < 0.01:  # Tolerância de 1 centavo
            return 'OK'
        elif row['Total_PDF'] == 0:
            return 'Apenas no TXT'
        elif row['Total_TXT'] == 0:
            return 'Apenas no PDF'
        else:
            return 'Divergência'

    confronto['Status'] = confronto.apply(determinar_status, axis=1)

    # Ordenar por status (divergências primeiro)
    ordem_status = {'Divergência': 0, 'Apenas no PDF': 1, 'Apenas no TXT': 2, 'OK': 3}
    confronto['_ordem'] = confronto['Status'].map(ordem_status)
    confronto = confronto.sort_values('_ordem').drop('_ordem', axis=1)

    return confronto


# ==================== PROCESSAMENTO PRINCIPAL ====================

def processar_pdfs():
    """Processa todos os PDFs encontrados e realiza confronto com TXT."""
    print("=" * 80)
    print("SISTEMA MODERNO DE PROCESSAMENTO DE RESUMOS DP")
    print("=" * 80)

    # Encontrar PDFs
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("❌ Nenhum PDF encontrado!")
        return

    print(f"\n📁 Encontrados {len(pdf_files)} arquivo(s) PDF\n")

    # Estrutura para armazenar dados
    eventos_por_categoria = defaultdict(list)
    impostos_geral = None

    # Processar cada PDF
    for pdf_path in pdf_files:
        tipo = identificar_tipo_resumo(pdf_path.name)
        print(f"📄 {pdf_path.name}")
        print(f"  └─ Tipo identificado: {tipo}")

        if tipo == "Geral":
            # Extrair impostos do Resumo Geral
            impostos_geral = extrair_impostos_resumo_geral(pdf_path)
            print(f"  └─ ✅ Impostos extraídos")

        elif tipo != "Desconhecido":
            # Extrair eventos (código + total)
            df_eventos = extrair_eventos_resumo_simples(pdf_path)

            if not df_eventos.empty:
                # Adicionar categoria
                df_eventos["Categoria"] = tipo
                eventos_por_categoria[tipo].append(df_eventos)
                print(f"  └─ ✅ {len(df_eventos)} eventos extraídos")
            else:
                print(f"  └─ ⚠️  Nenhum evento extraído")
        else:
            print(f"  └─ ⚠️  Tipo desconhecido - ignorado")

        print()

    # ========== PROCESSAR TXT E REALIZAR CONFRONTO ==========
    df_confronto = None
    df_eventos_mapeados = None
    df_lancamentos = None
    eventos_nao_mapeados = None

    if TXT_FILE and TXT_FILE.exists():
        print("=" * 80)
        print(f"📄 Processando arquivo TXT: {TXT_FILE.name}")

        # Consolidar todos os eventos
        todos_eventos = []
        for tipo, dfs in eventos_por_categoria.items():
            todos_eventos.extend(dfs)

        if todos_eventos:
            df_eventos_consolidado = pd.concat(todos_eventos, ignore_index=True)

            # Carregar mapeamento
            mapeamento = load_mapeamento()
            print(f"  └─ Mapeamento carregado: {len(mapeamento)} categorias")

            # Mapear eventos para lançamentos
            df_eventos_mapeados = mapear_eventos_para_lancamentos(df_eventos_consolidado, mapeamento)
            print(f"  └─ {len(df_eventos_mapeados)} eventos mapeados")

            # Eventos não mapeados
            eventos_nao_mapeados = df_eventos_mapeados[df_eventos_mapeados['CodigoLA'].isna()]
            if not eventos_nao_mapeados.empty:
                print(f"  └─ ⚠️  {len(eventos_nao_mapeados)} eventos sem mapeamento")

            # Parsear TXT
            df_lancamentos = parse_txt_lancamentos(TXT_FILE)
            print(f"  └─ {len(df_lancamentos)} lançamentos extraídos do TXT")

            # Realizar confronto
            df_confronto = realizar_confronto(df_eventos_mapeados, df_lancamentos)

            # Estatísticas do confronto
            total_ok = len(df_confronto[df_confronto['Status'] == 'OK'])
            total_divergencia = len(df_confronto[df_confronto['Status'] == 'Divergência'])
            total_apenas_pdf = len(df_confronto[df_confronto['Status'] == 'Apenas no PDF'])
            total_apenas_txt = len(df_confronto[df_confronto['Status'] == 'Apenas no TXT'])

            print(f"\n  📊 Resultados do Confronto:")
            print(f"    ✅ OK: {total_ok}")
            print(f"    ⚠️  Divergências: {total_divergencia}")
            print(f"    📄 Apenas no PDF: {total_apenas_pdf}")
            print(f"    📝 Apenas no TXT: {total_apenas_txt}")

    # ========== GERAR EXCEL ==========
    print("\n" + "=" * 80)
    print("💾 Gerando Excel consolidado...")

    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        # ABA 1: Resumo
        resumo_data = []
        for tipo, dfs in eventos_por_categoria.items():
            total_eventos = sum([len(df) for df in dfs])
            resumo_data.append({
                "Categoria": tipo,
                "Total_Eventos": total_eventos
            })

        df_resumo = pd.DataFrame(resumo_data)
        df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
        print("  ✅ Aba 'Resumo'")

        # ABA 2: Eventos por categoria
        for tipo, dfs in eventos_por_categoria.items():
            df_consolidado = pd.concat(dfs, ignore_index=True)
            nome_aba = f"Eventos_{tipo.replace(' ', '_')[:25]}"
            df_consolidado.to_excel(writer, sheet_name=nome_aba, index=False)
            print(f"  ✅ Aba '{nome_aba}': {len(df_consolidado)} eventos")

        # ABA 3: Impostos do Resumo Geral
        if impostos_geral:
            df_impostos = pd.DataFrame([impostos_geral]).T
            df_impostos.columns = ["Valor"]
            df_impostos.index.name = "Imposto"
            df_impostos.to_excel(writer, sheet_name="Impostos_Geral")
            print(f"  ✅ Aba 'Impostos_Geral': {len(df_impostos)} impostos")

        # ABA 4: Confronto (se TXT fornecido)
        if df_confronto is not None:
            df_confronto.to_excel(writer, sheet_name="Confronto_PDF_TXT", index=False)
            print(f"  ✅ Aba 'Confronto_PDF_TXT': {len(df_confronto)} lançamentos")

        # ABA 5: Eventos Mapeados
        if df_eventos_mapeados is not None:
            df_eventos_mapeados.to_excel(writer, sheet_name="Eventos_Mapeados", index=False)
            print(f"  ✅ Aba 'Eventos_Mapeados': {len(df_eventos_mapeados)} eventos")

        # ABA 6: Eventos Não Mapeados
        if eventos_nao_mapeados is not None and not eventos_nao_mapeados.empty:
            eventos_nao_mapeados.to_excel(writer, sheet_name="Eventos_Nao_Mapeados", index=False)
            print(f"  ✅ Aba 'Eventos_Nao_Mapeados': {len(eventos_nao_mapeados)} eventos")

        # ABA 7: Lançamentos TXT
        if df_lancamentos is not None and not df_lancamentos.empty:
            df_lancamentos.to_excel(writer, sheet_name="Lancamentos_TXT", index=False)
            print(f"  ✅ Aba 'Lancamentos_TXT': {len(df_lancamentos)} lançamentos")

    print("\n" + "=" * 80)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print(f"📊 Arquivo gerado: {OUTPUT_EXCEL.name}")
    print(f"📁 Tamanho: {OUTPUT_EXCEL.stat().st_size / 1024:.2f} KB")
    print("=" * 80)


if __name__ == "__main__":
    processar_pdfs()
