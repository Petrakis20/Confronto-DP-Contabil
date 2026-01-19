#!/usr/bin/env python3
"""
Extrator e Processador Completo de PDFs de Folha de Pagamento
--------------------------------------------------------------
Este script executa todo o processo de extração e organização:
1. Extrai dados dos PDFs (eventos e impostos detalhados)
2. Organiza em formato estruturado
3. Gera um único Excel consolidado

Uso: python3 processar_folha_completo.py
"""

import pdfplumber
import camelot
import pandas as pd
import re
from pathlib import Path
from datetime import datetime
import unicodedata

# Configurações
PDF_FOLDER = Path(__file__).parent
OUTPUT_FILE = PDF_FOLDER / f"dados_folha_completos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"


# ==================== FUNÇÕES DE EXTRAÇÃO DE IMPOSTOS ====================

def extrair_valor(texto, padrao):
    """Extrai valor numérico após um padrão específico."""
    match = re.search(padrao + r'\s*:?\s*([\d.,]+)', texto, re.IGNORECASE)
    if match:
        valor_str = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(valor_str)
        except:
            return 0.0
    return 0.0


def extrair_impostos_inss(texto):
    """Extrai todos os valores de INSS do texto."""
    impostos = {}
    impostos['INSS_Empregados'] = extrair_valor(texto, r'Empregados')
    impostos['INSS_Socios'] = extrair_valor(texto, r'Sócios')
    impostos['INSS_Autonomos'] = extrair_valor(texto, r'Autônomos')
    impostos['INSS_Empresa_Funcionarios'] = extrair_valor(texto, r'Empresa Funcionários')
    
    # RAT Emp - captura o valor antes de DARF
    match_rat = re.search(r'RAT Emp.*?%\)\s*:\s*([\d.,]+)', texto, re.IGNORECASE)
    impostos['INSS_RAT_Emp'] = float(match_rat.group(1).replace('.', '').replace(',', '.')) if match_rat else 0.0
    
    impostos['INSS_RAT_Agentes_Nocivos'] = extrair_valor(texto, r'RAT - Agentes Nocivos')
    impostos['INSS_Empresa_Socios'] = extrair_valor(texto, r'Empresa Sócios')
    impostos['INSS_Empresa_Autonomos'] = extrair_valor(texto, r'Empresa Autônomos')
    impostos['INSS_Cooperativas'] = extrair_valor(texto, r'Cooperativas')
    impostos['INSS_Residuo_Mes_Anterior'] = extrair_valor(texto, r'Resíduo Mês Anterior')
    impostos['INSS_Deducoes_FPAS'] = extrair_valor(texto, r'Deduções de FPAS')
    impostos['INSS_Valor_Retido'] = extrair_valor(texto, r'Valor Retido')
    impostos['INSS_SubTotal'] = extrair_valor(texto, r'Sub-Total')
    impostos['INSS_Terceiros_Carreteiro'] = extrair_valor(texto, r'Terceiros Carreteiro')
    impostos['INSS_Residuo_Terceiros'] = extrair_valor(texto, r'Resíduo Terceiros')
    impostos['INSS_Terceiros_580'] = extrair_valor(texto, r'Terceiros.*?5,80\s*%')
    impostos['INSS_Total_Liquido'] = extrair_valor(texto, r'Total Líquido')
    return impostos


def extrair_impostos_fgts(texto):
    """Extrai todos os valores de FGTS do texto."""
    impostos = {}
    impostos['FGTS_sem_13'] = extrair_valor(texto, r'FGTS sem 13º salário s/CS')
    impostos['FGTS_sobre_13'] = extrair_valor(texto, r'FGTS sobre 13º salário s/CS')
    impostos['FGTS_Total_Apurado'] = extrair_valor(texto, r'Total FGTS apurado recibos s/CS')
    impostos['FGTS_Base_Calc_sem_13'] = extrair_valor(texto, r'Base de calc\. FGTS sem 13º')
    impostos['FGTS_Base_Calc_13'] = extrair_valor(texto, r'Base de calc\. FGTS 13º')
    impostos['FGTS_Base_Calc_GRRF'] = extrair_valor(texto, r'Base de calc\. FGTS GRRF')
    impostos['FGTS_Base_Calc_Multa_GRRF'] = extrair_valor(texto, r'Base de calc\. Multa FGTS GRRF')
    impostos['FGTS_Base_Calc_Mes_Anterior'] = extrair_valor(texto, r'Base de calc\. FGTS M\.Anterior')
    impostos['FGTS_Total_Recolhido'] = extrair_valor(texto, r'Total FGTS recolhido s/CS')
    impostos['FGTS_Total_Mes_Anterior'] = extrair_valor(texto, r'Total FGTS Mês Anterior s/CS')
    return impostos


def extrair_impostos_pis(texto):
    """Extrai todos os valores de PIS do texto."""
    return {
        'PIS_Base': extrair_valor(texto, r'Base PIS Folha'),
        'PIS_Folha': extrair_valor(texto, r'PIS Folha')
    }


def extrair_impostos_irrf(texto):
    """Extrai todos os valores de IRRF do texto."""
    impostos = {}
    
    # Procura pela seção DARF IRRF especificamente
    # Isso evita pegar os valores da tabela de eventos
    match_secao_darf = re.search(r'DARF IRRF.*?OUTRAS INFORMAÇÕES', texto, re.DOTALL | re.IGNORECASE)
    
    if match_secao_darf:
        secao_darf = match_secao_darf.group(0)
        
        # Extrai valores da seção DARF
        impostos['IRRF_Folha'] = extrair_valor(secao_darf, r'IRRF Folha')
        impostos['IRRF_Ferias'] = extrair_valor(secao_darf, r'IRRF Férias')
        impostos['IRRF_Rescisao'] = extrair_valor(secao_darf, r'IRRF Rescisão')
        impostos['IRRF_Socio'] = extrair_valor(secao_darf, r'IRRF Sócio')
        impostos['IRRF_Autonomo'] = extrair_valor(secao_darf, r'IRRF Autônomo')
    else:
        # Se não encontrar a seção, tenta buscar no texto todo (fallback)
        # mas com padrão mais específico (com ":")
        impostos['IRRF_Folha'] = extrair_valor(texto, r'IRRF Folha\s*:')
        impostos['IRRF_Ferias'] = extrair_valor(texto, r'IRRF Férias\s*:')
        impostos['IRRF_Rescisao'] = extrair_valor(texto, r'IRRF Rescisão\s*:')
        impostos['IRRF_Socio'] = extrair_valor(texto, r'IRRF Sócio\s*:')
        impostos['IRRF_Autonomo'] = extrair_valor(texto, r'IRRF Autônomo\s*:')
    
    return impostos


def extrair_outras_contribuicoes(texto):
    """Extrai outras contribuições."""
    return {
        'Contrib_Confederativa': extrair_valor(texto, r'Contrib\. Confederativa'),
        'Contrib_Sindical': extrair_valor(texto, r'Contrib\. Sindical'),
        'Contrib_Assistencial': extrair_valor(texto, r'Contrib\. Assistencial'),
        'Contrib_Social_FGTS': extrair_valor(texto, r'Contrib\. Social s/ FGTS')
    }


def extrair_pro_labore_autonomos(texto):
    """Extrai informações de Pró-Labore e Autônomos do Resumo Geral."""
    resultado = {
        'ProLabore_Bruto_Socios': 0.0,
        'ProLabore_Bruto_Autonomos': 0.0,
        'ProLabore_INSS_Socios': 0.0,
        'ProLabore_INSS_Autonomos': 0.0,
        'ProLabore_Liquido_Socios': 0.0,
        'ProLabore_Liquido_Autonomos': 0.0
    }

    # Procurar pela seção "Valores pagos aos Sócios / Autônomos"
    match_secao = re.search(
        r'Valores pagos aos Sócios.*?TOTAL DE SÓCIOS',
        texto,
        re.DOTALL | re.IGNORECASE
    )

    if match_secao:
        secao = match_secao.group(0)

        # Buscar linha "003 PRO LABORE"
        match_prolabore = re.search(r'003\s+PRO LABORE\s+([\d.,]+)\s+([\d.,]+)', secao)
        if match_prolabore:
            resultado['ProLabore_Bruto_Socios'] = float(match_prolabore.group(1).replace('.', '').replace(',', '.'))
            resultado['ProLabore_Bruto_Autonomos'] = float(match_prolabore.group(2).replace('.', '').replace(',', '.'))

        # Buscar linha "013 INSS"
        match_inss = re.search(r'013\s+INSS\s+([\d.,]+)\s+([\d.,]+)', secao)
        if match_inss:
            resultado['ProLabore_INSS_Socios'] = float(match_inss.group(1).replace('.', '').replace(',', '.'))
            resultado['ProLabore_INSS_Autonomos'] = float(match_inss.group(2).replace('.', '').replace(',', '.'))

        # Calcular líquidos
        resultado['ProLabore_Liquido_Socios'] = resultado['ProLabore_Bruto_Socios'] - resultado['ProLabore_INSS_Socios']
        resultado['ProLabore_Liquido_Autonomos'] = resultado['ProLabore_Bruto_Autonomos'] - resultado['ProLabore_INSS_Autonomos']

    return resultado


# ==================== FUNÇÕES DE EXTRAÇÃO DE EVENTOS ====================

def limpar_valor(valor_str):
    """Converte valores tipo '1.234,56' para float 1234.56"""
    if pd.isna(valor_str) or valor_str == 'NaN':
        return 0.0
    valor_str = str(valor_str).strip()
    try:
        return float(valor_str)
    except:
        pass
    valor_str = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(valor_str)
    except:
        return 0.0


def extrair_tabelas_camelot(pdf_path):
    """Extrai tabelas usando Camelot."""
    todas_tabelas = []
    try:
        tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')
        if len(tables) == 0:
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='stream')
        
        for i, table in enumerate(tables, 1):
            df = table.df
            df.insert(0, 'Arquivo', pdf_path.name)
            df.insert(1, 'Página', table.page)
            df.insert(2, 'Tabela_Num', i)
            todas_tabelas.append(df)
    except Exception as e:
        print(f"  ⚠️  Erro ao extrair tabelas (Camelot): {e}")
    
    return todas_tabelas


def extrair_eventos_de_tabelas(df_tabelas, arquivo_pdf):
    """Extrai eventos de folha das tabelas."""
    df_arquivo = df_tabelas[df_tabelas['Arquivo'] == arquivo_pdf].copy()
    
    df_eventos = df_arquivo[
        df_arquivo[0].notna() & 
        df_arquivo[1].notna() &
        (df_arquivo[0] != 'ADICIONAIS / DESCONTOS') &
        (df_arquivo[0] != 'NaN')
    ].copy()
    
    df_eventos = df_eventos[
        ~df_eventos[1].astype(str).str.contains('TOTAL|Valores pagos|Resumo Geral', case=False, na=False)
    ]
    
    eventos_limpos = []
    for _, row in df_eventos.iterrows():
        codigo = str(row[0]).strip()
        descricao = str(row[1]).strip()
        
        # Ignora se não tiver código válido
        if codigo == 'nan' or not codigo or descricao == 'nan' or descricao == 'NaN':
            continue
        
        # Ignora totais e categorias
        if any(palavra in codigo for palavra in ['TOTAL', 'Total', 'Empregados', 'Sócios', 'Autônomos', 'Funcionários', 'LÍQUIDO', 'Líquido']):
            continue
        
        # Ignora cabeçalhos e informações da empresa
        if any(palavra in codigo for palavra in ['Empresa', 'Endereço', 'Período', 'Tipo', 'RAT', 'Terceiros', 'Sub-Total', 'Resíduo', 'Deduções', 'Valor', 'Cooperativas']):
            continue
        
        # Ignora códigos de funcionários (6 dígitos)
        if len(codigo) == 6 and codigo.isdigit():
            continue
        
        # Só ignora se for número E não for um código válido de evento
        # (códigos válidos de evento podem ser de 001 até 999)
        try:
            codigo_num = int(codigo)
            # Não tem filtro aqui - todos os códigos numéricos são válidos
        except ValueError:
            # Se não for número, ignora linhas de cabeçalho
            if any(palavra in codigo for palavra in ['FUNCIONÁRIO', 'OCORRÊNCIA', 'BASES']):
                continue
        
        # Ignora se a descrição contém palavras de impostos/cabeçalhos
        desc_lower = descricao.lower()
        if any(palavra in desc_lower for palavra in ['funcionários na folha', 'galpão', 'cnpj', 'tat x fap']):
            continue
        
        eventos_limpos.append({
            'Codigo': codigo,
            'Descricao': descricao,
            'Ativos': limpar_valor(row[2]),
            'Demitidos': limpar_valor(row[3]),
            'Afastados': limpar_valor(row[4]),
            'Total': limpar_valor(row[5])
        })
    
    return pd.DataFrame(eventos_limpos) if eventos_limpos else pd.DataFrame(columns=['Codigo', 'Descricao', 'Ativos', 'Demitidos', 'Afastados', 'Total'])


# ==================== FUNÇÕES DE PROCESSAMENTO ====================

def processar_pdf(pdf_path):
    """Processa um PDF completo: eventos e impostos."""
    print(f"\n📄 Processando: {pdf_path.name}")
    
    resultado = {
        'arquivo': pdf_path.name,
        'eventos': None,
        'impostos': {}
    }
    
    # 1. Extrai tabelas para eventos
    print("  └─ Extraindo eventos...")
    tabelas = extrair_tabelas_camelot(pdf_path)
    
    if tabelas:
        df_tabelas = pd.concat(tabelas, ignore_index=True)
        resultado['eventos'] = extrair_eventos_de_tabelas(df_tabelas, pdf_path.name)
    
    # 2. Extrai texto para impostos
    print("  └─ Extraindo impostos detalhados...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto_completo = ""
            for page in pdf.pages:
                texto_completo += page.extract_text() + "\n"

            resultado['impostos'].update(extrair_impostos_inss(texto_completo))
            resultado['impostos'].update(extrair_impostos_fgts(texto_completo))
            resultado['impostos'].update(extrair_impostos_pis(texto_completo))
            resultado['impostos'].update(extrair_impostos_irrf(texto_completo))
            resultado['impostos'].update(extrair_outras_contribuicoes(texto_completo))
            resultado['impostos'].update(extrair_pro_labore_autonomos(texto_completo))
    except Exception as e:
        print(f"  ⚠️  Erro ao extrair impostos: {e}")

    return resultado


def formatar_impostos_para_padrao(impostos):
    """Transforma impostos em formato padronizado."""
    impostos_formatados = []
    
    # INSS
    itens_inss = [
        ('INSS_001', 'INSS - Empregados', impostos.get('INSS_Empregados', 0)),
        ('INSS_002', 'INSS - Sócios', impostos.get('INSS_Socios', 0)),
        ('INSS_003', 'INSS - Autônomos', impostos.get('INSS_Autonomos', 0)),
        ('INSS_004', 'INSS - Empresa Funcionários', impostos.get('INSS_Empresa_Funcionarios', 0)),
        ('INSS_005', 'INSS - RAT Emp (1,5%)', impostos.get('INSS_RAT_Emp', 0)),
        ('INSS_006', 'INSS - RAT Agentes Nocivos', impostos.get('INSS_RAT_Agentes_Nocivos', 0)),
        ('INSS_007', 'INSS - Empresa Sócios', impostos.get('INSS_Empresa_Socios', 0)),
        ('INSS_008', 'INSS - Empresa Autônomos', impostos.get('INSS_Empresa_Autonomos', 0)),
        ('INSS_009', 'INSS - Cooperativas', impostos.get('INSS_Cooperativas', 0)),
        ('INSS_010', 'INSS - Resíduo Mês Anterior', impostos.get('INSS_Residuo_Mes_Anterior', 0)),
        ('INSS_011', 'INSS - Deduções de FPAS', impostos.get('INSS_Deducoes_FPAS', 0)),
        ('INSS_012', 'INSS - Valor Retido', impostos.get('INSS_Valor_Retido', 0)),
        ('INSS_013', 'INSS - Sub-Total', impostos.get('INSS_SubTotal', 0)),
        ('INSS_014', 'INSS - Terceiros Carreteiro', impostos.get('INSS_Terceiros_Carreteiro', 0)),
        ('INSS_015', 'INSS - Resíduo Terceiros', impostos.get('INSS_Residuo_Terceiros', 0)),
        ('INSS_016', 'INSS - Terceiros 5,80%', impostos.get('INSS_Terceiros_580', 0)),
        ('INSS_TOTAL', 'INSS - Total Líquido', impostos.get('INSS_Total_Liquido', 0)),
    ]
    
    # FGTS
    itens_fgts = [
        ('FGTS_001', 'FGTS - sem 13º salário', impostos.get('FGTS_sem_13', 0)),
        ('FGTS_002', 'FGTS - sobre 13º salário', impostos.get('FGTS_sobre_13', 0)),
        ('FGTS_003', 'FGTS - Total Apurado Recibos', impostos.get('FGTS_Total_Apurado', 0)),
        ('FGTS_004', 'FGTS - Base Calc sem 13º', impostos.get('FGTS_Base_Calc_sem_13', 0)),
        ('FGTS_005', 'FGTS - Base Calc 13º', impostos.get('FGTS_Base_Calc_13', 0)),
        ('FGTS_006', 'FGTS - Base Calc GRRF', impostos.get('FGTS_Base_Calc_GRRF', 0)),
        ('FGTS_007', 'FGTS - Base Calc Multa GRRF', impostos.get('FGTS_Base_Calc_Multa_GRRF', 0)),
        ('FGTS_008', 'FGTS - Base Calc Mês Anterior', impostos.get('FGTS_Base_Calc_Mes_Anterior', 0)),
        ('FGTS_TOTAL', 'FGTS - Total Recolhido', impostos.get('FGTS_Total_Recolhido', 0)),
        ('FGTS_010', 'FGTS - Total Mês Anterior', impostos.get('FGTS_Total_Mes_Anterior', 0)),
    ]
    
    # PIS e IRRF
    itens_outros = [
        ('PIS_001', 'PIS - Base PIS Folha', impostos.get('PIS_Base', 0)),
        ('PIS_TOTAL', 'PIS - Folha', impostos.get('PIS_Folha', 0)),
        ('IRRF_001', 'IRRF - Folha', impostos.get('IRRF_Folha', 0)),
        ('IRRF_002', 'IRRF - Férias', impostos.get('IRRF_Ferias', 0)),
        ('IRRF_003', 'IRRF - Rescisão', impostos.get('IRRF_Rescisao', 0)),
        ('IRRF_004', 'IRRF - Sócio', impostos.get('IRRF_Socio', 0)),
        ('IRRF_005', 'IRRF - Autônomo', impostos.get('IRRF_Autonomo', 0)),
        ('CONTRIB_001', 'Contrib. Confederativa', impostos.get('Contrib_Confederativa', 0)),
        ('CONTRIB_002', 'Contrib. Sindical', impostos.get('Contrib_Sindical', 0)),
        ('CONTRIB_003', 'Contrib. Assistencial', impostos.get('Contrib_Assistencial', 0)),
        ('CONTRIB_004', 'Contrib. Social s/ FGTS', impostos.get('Contrib_Social_FGTS', 0)),
    ]

    # Pró-Labore e Autônomos
    itens_prolabore = [
        ('PROLABORE_001', 'Pró-Labore - Bruto Sócios', impostos.get('ProLabore_Bruto_Socios', 0)),
        ('PROLABORE_002', 'Pró-Labore - Bruto Autônomos', impostos.get('ProLabore_Bruto_Autonomos', 0)),
        ('PROLABORE_003', 'Pró-Labore - INSS Sócios', impostos.get('ProLabore_INSS_Socios', 0)),
        ('PROLABORE_004', 'Pró-Labore - INSS Autônomos', impostos.get('ProLabore_INSS_Autonomos', 0)),
        ('PROLABORE_TOTAL_SOCIOS', 'Pró-Labore - Líquido Sócios', impostos.get('ProLabore_Liquido_Socios', 0)),
        ('PROLABORE_TOTAL_AUTONOMOS', 'Pró-Labore - Líquido Autônomos', impostos.get('ProLabore_Liquido_Autonomos', 0)),
    ]

    # Combina todos os itens
    todos_itens = itens_inss + itens_fgts + itens_outros + itens_prolabore
    
    # Inclui TODOS os campos, independente do valor
    for codigo, descricao, valor in todos_itens:
        impostos_formatados.append({
            'Codigo': codigo,
            'Descricao': descricao,
            'Ativos': 0.0,
            'Demitidos': 0.0,
            'Afastados': 0.0,
            'Total': valor
        })
    
    return pd.DataFrame(impostos_formatados)


def normalizar_texto(texto):
    """Remove acentos para matching."""
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def obter_tipo_arquivo(nome_arquivo):
    """Identifica o tipo do arquivo."""
    nome_norm = normalizar_texto(nome_arquivo)
    if 'rescis' in nome_norm:
        return 'rescisão'
    elif 'folha' in nome_norm:
        return 'folha'
    elif 'ferias' in nome_norm:
        return 'férias'
    elif 'geral' in nome_norm:
        return 'Geral'
    return 'desconhecido'


# ==================== FUNÇÃO PRINCIPAL ====================

def main():
    """Função principal de processamento."""
    print("=" * 80)
    print("PROCESSADOR COMPLETO DE FOLHA DE PAGAMENTO")
    print("=" * 80)
    
    # Encontra PDFs
    pdf_files = list(PDF_FOLDER.glob("*.pdf"))
    if not pdf_files:
        print("❌ Nenhum PDF encontrado!")
        return
    
    print(f"\n📁 Encontrados {len(pdf_files)} arquivo(s) PDF")
    
    # Processa cada PDF
    resultados = []
    for pdf_path in pdf_files:
        resultado = processar_pdf(pdf_path)
        resultados.append(resultado)
        print(f"  ✅ Concluído!")
    
    # Gera Excel consolidado
    print("\n" + "=" * 80)
    print("💾 Gerando Excel consolidado...")
    
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # Resumo
        resumo_data = []
        for res in resultados:
            tipo = obter_tipo_arquivo(res['arquivo'])
            num_eventos = len(res['eventos']) if res['eventos'] is not None else 0
            df_impostos_temp = formatar_impostos_para_padrao(res['impostos'])
            
            resumo_data.append({
                'Arquivo': tipo,
                'Total_Eventos': num_eventos,
                'Total_Impostos': len(df_impostos_temp)
            })
        
        df_resumo = pd.DataFrame(resumo_data)
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
        print(f"  ✅ Aba 'Resumo'")
        
        # Para cada arquivo
        for res in resultados:
            tipo = obter_tipo_arquivo(res['arquivo'])
            
            # Eventos
            if res['eventos'] is not None and len(res['eventos']) > 0:
                aba_eventos = f"Eventos_{tipo}"
                res['eventos'].to_excel(writer, sheet_name=aba_eventos, index=False)
                print(f"  ✅ Aba '{aba_eventos}': {len(res['eventos'])} eventos")
            
            # Impostos
            df_impostos = formatar_impostos_para_padrao(res['impostos'])
            if len(df_impostos) > 0:
                aba_impostos = f"Impostos_{tipo}"
                df_impostos.to_excel(writer, sheet_name=aba_impostos, index=False)
                print(f"  ✅ Aba '{aba_impostos}': {len(df_impostos)} impostos")
    
    print("\n" + "=" * 80)
    print("✅ PROCESSAMENTO CONCLUÍDO!")
    print(f"📊 Arquivo gerado: {OUTPUT_FILE.name}")
    print(f"📁 Tamanho: {OUTPUT_FILE.stat().st_size / 1024:.2f} KB")
    print("=" * 80)


if __name__ == "__main__":
    main()
