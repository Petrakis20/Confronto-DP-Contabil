#!/usr/bin/env python3
"""
Interface Streamlit para Sistema Moderno de Processamento de Resumos DP
"""

import streamlit as st
import pandas as pd
import pdfplumber
import re
import json
import io
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ==================== CONFIGURAÇÕES ====================

st.set_page_config(
    page_title="Processamento Resumos DP",
    page_icon="📊",
    layout="wide"
)

# Tentar múltiplos locais para o arquivo de mapeamento
SCRIPT_DIR = Path(__file__).resolve().parent
MAPEAMENTO_JSON = SCRIPT_DIR.parent / "mapeamento_dp.json"

# Fallback: tentar na mesma pasta do script
if not MAPEAMENTO_JSON.exists():
    MAPEAMENTO_JSON = SCRIPT_DIR / "mapeamento_dp.json"

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


def money(valor: float) -> str:
    """Formata valor como moeda brasileira."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def load_mapeamento() -> dict:
    """Carrega o mapeamento de eventos para lançamentos."""
    if not MAPEAMENTO_JSON.exists():
        st.error(f"""
        ❌ **Arquivo de mapeamento não encontrado!**
        
        **Caminho esperado:** `{MAPEAMENTO_JSON.resolve()}`
        
        **Diretório atual do script:** `{SCRIPT_DIR.resolve()}`
        
        **Arquivos disponíveis na pasta pai:**
        """)
        try:
            arquivos = list(SCRIPT_DIR.parent.glob("*.json"))
            if arquivos:
                st.write("Arquivos JSON encontrados:")
                for arq in arquivos:
                    st.write(f"  - {arq.name}")
            else:
                st.write("Nenhum arquivo .json encontrado na pasta pai")
        except:
            pass
        return {}

    try:
        with open(MAPEAMENTO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Erro ao carregar mapeamento: {e}")
        return {}


def identificar_tipo_resumo(nome_arquivo: str) -> str:
    """Identifica o tipo de resumo pelo nome do arquivo."""
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


def get_event_type_from_mapping(categoria: str, codigo_evento: str, mapeamento: dict) -> str:
    """
    Busca o tipo do evento (Adicional/Desconto) no mapeamento.
    
    Args:
        categoria: Categoria do evento (ex: "Folha", "Férias")
        codigo_evento: Código do evento com 3 dígitos (ex: "001", "009")
        mapeamento: Dicionário do mapeamento_dp.json
    
    Returns:
        "Adicional" ou "Desconto" (default: "Adicional" se não encontrado)
    """
    if not mapeamento or categoria not in mapeamento:
        return "Adicional"  # Default
    
    # Garantir que código tem 3 dígitos com zeros à esquerda
    codigo_evento = str(codigo_evento).zfill(3)
    
    for item in mapeamento[categoria]:
        if item.get('evento') == codigo_evento:
            tipo = item.get('tipo', 'Adicional')
            # Normalizar tipo
            if normalize_text(tipo) in ['desconto', 'descontos']:
                return 'Desconto'
            else:
                return 'Adicional'
    
    return "Adicional"  # Default se não encontrado no mapeamento


def extrair_eventos_resumo_simples(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Extrai código e total de resumos específicos.
    
    Suporta DOIS formatos de PDF:
    1. Com prefixo +/- : "+ 009 Férias 358,35 1"
    2. Sem prefixo: "009 Férias 358,35 1"
    
    Quando sem prefixo, o tipo (Adicional/Desconto) será determinado
    posteriormente pelo mapeamento_dp.json.
    """
    eventos = []
    linhas_processadas = 0
    linhas_matcheadas = 0
    format_detected = None  # "with_prefix" ou "without_prefix"
    dentro_secao_ignorada = False  # Flag para ignorar seção inteira

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    for linha in texto_completo.split('\n'):
        linhas_processadas += 1
        
        linha_lower = linha.lower()
        
        # Detectar início da seção que deve ser ignorada
        if 'não influenciam' in linha_lower or 'não aparecem em folha' in linha_lower:
            dentro_secao_ignorada = True
            continue
        
        # Detectar fim da seção ignorada (TOTAL ou linha com traços/separadores)
        if dentro_secao_ignorada:
            # Se encontrar "TOTAL" seguido de palavras da seção, marca fim
            if 'total' in linha_lower and ('não aparecem' in linha_lower or 'não influenciam' in linha_lower):
                dentro_secao_ignorada = False
                continue
            # Se encontrar linha de separação (muitos traços ou underscores)
            if linha.strip().startswith('_' * 5) or linha.strip().startswith('-' * 5):
                dentro_secao_ignorada = False
                continue
            # Ignorar todas as linhas dentro da seção
            continue
        
        # Ignorar linhas de cabeçalho e totais normais
        if any(palavra in linha_lower for palavra in [
            'total', 'adicionais', 'descontos', 'codigo', 'ativos',
            'demitidos', 'afastados', 'valores pagos', 'tipo processo',
            'resumo geral', 'empresa', 'periodo', 'cnpj', 'endereco',
            'líquido', 'funcionários', 'sócios', 'base inss', 'base irrf',
            'base fgts', 'quantidade', 'valor', 'página', 'emissão'  # Removido 'evento'
        ]):
            continue

        # Tentar DOIS padrões: com e sem prefixo +/-
        match = None
        has_prefix = False
        descricao = ""
        
        # Padrão 1: COM prefixo +/- (formato antigo com 1 valor + num_funcionarios)
        # Formato: [+/-] [codigo] [descrição] [valor] [num_funcionarios]
        # Exemplo: + 009 Férias 358,35 1
        match = re.search(r'^[+\-]\s+(\d{3})\s+(.+?)\s+([\d.,]+)\s+(\d+)\s*$', linha.strip())
        
        if match:
            has_prefix = True
            if format_detected is None:
                format_detected = "with_prefix"
            
            descricao = match.group(2).strip()
            # Extrair valor (penúltimo campo)
            valor_str = match.group(3)
        else:
            # Padrão 2: SEM prefixo com MÚLTIPLOS VALORES (formato novo real)
            # Formato: [codigo] [descrição] [valor1] [valor2] [valor3] [valor_total]
            # Exemplo: 001 Salário Base 197.791,51 0,00 0,00 197.791,51
            # O último valor é o total que queremos
            match = re.search(r'^(\d{3})\s+(.+?)\s+((?:[\d.,]+\s+)+[\d.,]+)\s*$', linha.strip())
            
            if match:
                has_prefix = False
                if format_detected is None:
                    format_detected = "without_prefix"
                
                descricao = match.group(2).strip()
                # Extrair todos os valores e pegar o último (total)
                valores_str = match.group(3).strip()
                valores = re.findall(r'[\d.,]+', valores_str)
                if valores:
                    valor_str = valores[-1]  # Último valor é o total
                else:
                    continue
            else:
                # Padrão 3: SEM prefixo simples (formato intermediário)
                # Formato: [codigo] [descrição] [valor] [num_funcionarios]
                # Exemplo: 009 Férias 358,35 1
                match = re.search(r'^(\d{3})\s+(.+?)\s+([\d.,]+)\s+(\d+)\s*$', linha.strip())
                
                if match:
                    has_prefix = False
                    if format_detected is None:
                        format_detected = "without_prefix_simple"
                    
                    descricao = match.group(2).strip()
                    valor_str = match.group(3)
                else:
                    continue

        if match:
            codigo = match.group(1)
            
            total = parse_brl_decimal(valor_str)

            if total > 0:
                eventos.append({
                    "Codigo": codigo,
                    "Descricao": descricao,  # Adicionar descrição extraída do PDF
                    "Total": abs(total),
                    "HasPrefix": has_prefix  # Armazenar se tinha prefixo para debug
                })
                linhas_matcheadas += 1

    # Armazenar estatísticas para debug
    st.session_state['pdf_debug'] = {
        'linhas_processadas': linhas_processadas,
        'linhas_matcheadas': linhas_matcheadas,
        'eventos_extraidos': len(eventos),
        'formato_detectado': format_detected or 'unknown'
    }

    return pd.DataFrame(eventos)


def extrair_impostos_resumo_geral(pdf_bytes: bytes) -> dict:
    """Extrai impostos consolidados do Resumo Geral."""
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

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texto_completo = ""
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    # INSS - Total Líquido
    match = re.search(r'Total Líquido\s*:?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
    if match:
        impostos["INSS_Total_Liquido"] = parse_brl_decimal(match.group(1))

    # FGTS - Total apurado recibos s/CS (com ou sem "s/CS")
    match = re.search(r'Total FGTS apurado recibos s/CS\s*:?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
    if match:
        impostos["FGTS_Total_Apurado"] = parse_brl_decimal(match.group(1))
    else:
        # Tentar sem "s/CS" caso não encontre
        match = re.search(r'Total FGTS apurado recibos\s*:?\s*([\d.,]+)', texto_completo, re.IGNORECASE)
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


def parse_txt_lancamentos(txt_bytes: bytes) -> pd.DataFrame:
    """Extrai lançamentos do arquivo TXT/CSV contábil."""
    import csv
    import io

    lancamentos = []
    linhas_processadas = 0
    linhas_validas = 0

    # Decodificar bytes - tentar várias codificações
    texto = None
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            texto = txt_bytes.decode(encoding)
            break
        except:
            continue

    if texto is None:
        texto = txt_bytes.decode('utf-8', errors='ignore')

    # Detectar separador mais comum
    primeira_linha = texto.split('\n')[0] if texto else ''
    if primeira_linha.count(';') > primeira_linha.count(','):
        delimiter = ';'
    elif primeira_linha.count('\t') > 0:
        delimiter = '\t'
    else:
        delimiter = ','

    # Usar csv.reader para parsing correto de campos com aspas
    reader = csv.reader(io.StringIO(texto), delimiter=delimiter, quotechar='"')

    for partes in reader:
        if not partes or len(partes) < 4:
            continue

        linhas_processadas += 1

        # Coluna 2 (índice 1): código LA
        # Coluna 4 (índice 3): valor
        # Coluna 8 (índice 7): descrição
        codigo_la = partes[1].strip() if len(partes) > 1 else ""
        valor_str = partes[3].strip() if len(partes) > 3 else ""
        descricao = partes[7].strip() if len(partes) > 7 else ""

        # Validar código LA (numérico, >= 4 dígitos)
        # Remover possíveis aspas ou espaços
        codigo_la = codigo_la.strip('"').strip("'").strip()

        if not codigo_la or not codigo_la.isdigit():
            continue

        if len(codigo_la) < 4:
            continue

        # Parsear valor (já vem sem aspas do csv.reader)
        try:
            valor = parse_brl_decimal(valor_str)
        except:
            continue

        if valor != 0:  # Incluir valores positivos e negativos
            lancamentos.append({
                'CodigoLA': codigo_la,
                'Valor': abs(valor),
                'Descricao': descricao
            })
            linhas_validas += 1

    # Debug info via session_state para exibir ao usuário
    import streamlit as st
    st.session_state['txt_debug'] = {
        'linhas_processadas': linhas_processadas,
        'linhas_validas': linhas_validas,
        'lancamentos_extraidos': len(lancamentos)
    }

    return pd.DataFrame(lancamentos)


def mapear_eventos_para_lancamentos(df_eventos: pd.DataFrame, mapeamento: dict) -> pd.DataFrame:
    """Mapeia eventos do PDF para códigos de lançamento."""
    resultados = []

    for _, row in df_eventos.iterrows():
        categoria = row['Categoria']
        codigo_evento = str(row['Codigo']).zfill(3)
        total = row['Total']
        descricao = row.get('Descricao', '')  # Obter descrição se existir

        # Buscar mapeamento para esta categoria
        if categoria not in mapeamento:
            resultados.append({
                'Categoria': categoria,
                'Codigo': codigo_evento,
                'Descricao': descricao,  # Preservar descrição
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
                    'Descricao': descricao,  # Preservar descrição
                    'CodigoLA': item['codigo_lancamento'],
                    'Total': total,
                    'Tipo': item.get('tipo', 'Desconhecido')
                })
                encontrado = True
                break

        if not encontrado:
            resultados.append({
                'Categoria': categoria,
                'Codigo': codigo_evento,
                'Descricao': descricao,  # Preservar descrição
                'CodigoLA': None,
                'Total': total,
                'Tipo': 'Não Mapeado'
            })

    return pd.DataFrame(resultados)


def confrontar_inss(inss_resumo_geral: float, df_lancamentos: pd.DataFrame, mapeamento: dict) -> dict:
    """
    Calcula o confronto do INSS entre Resumo Geral e TXT.
    
    Fórmula:
    - INSS_Resumo_Geral - Soma_TXT
    - Onde Soma_TXT = Σ(Adicionais) - Σ(Descontos)
    - Valores do TXT são usados com valor absoluto  
    - Adicionais são somados, Descontos são subtraídos
    
    Args:
        inss_resumo_geral: INSS Total Líquido do Resumo Geral
        df_lancamentos: DataFrame com os lançamentos do TXT (colunas: CodigoLA, Valor)
        mapeamento: Dicionário de mapeamento com seção INSS
    
    Returns:
        dict com valores do resumo, TXT e diferença
    """
    if df_lancamentos.empty or 'INSS' not in mapeamento:
        return {
            'INSS_Resumo_Geral': inss_resumo_geral,
            'INSS_TXT_Total': 0.0,
            'INSS_Diferenca': inss_resumo_geral,
            'INSS_TXT_Adicionais': 0.0,
            'INSS_TXT_Descontos': 0.0,
            'debug_log': []
        }
    
    # Extrair códigos LA do mapeamento INSS
    codigos_inss = mapeamento['INSS']
    
    # Separar adicionais e descontos
    # Normalizar removendo zeros à esquerda para comparação
    adicionais_la = [str(int(item['codigo_lancamento'])) for item in codigos_inss if item['tipo'] == 'Adicional']
    descontos_la = [str(int(item['codigo_lancamento'])) for item in codigos_inss if item['tipo'] == 'Desconto']
    
    # Garantir que CodigoLA é string e normalizar (remover zeros à esquerda)
    df_lancamentos = df_lancamentos.copy()
    df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).apply(lambda x: str(int(x)) if x.isdigit() else x)
    
    # Filtrar lançamentos do TXT que são INSS
    inss_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_la + descontos_la)].copy()
    
    # LOG: Criar lista de debug
    debug_log = []
    debug_log.append(f"📋 Total de lançamentos no TXT: {len(df_lancamentos)}")
    debug_log.append(f"📋 Lançamentos INSS encontrados: {len(inss_lancamentos)}")
    debug_log.append(f"📋 Códigos LA Adicionais: {', '.join(adicionais_la)}")
    debug_log.append(f"📋 Códigos LA Descontos: {', '.join(descontos_la)}")
    debug_log.append("=" * 80)
    
    # Calcular soma: Adicionais (positivos), Descontos (negativos)
    # Usar valor absoluto e aplicar o sinal baseado no tipo
    total_adicionais = 0.0
    total_descontos = 0.0
    
    # Agrupar por código LA para log
    adicionais_por_la = {}
    descontos_por_la = {}
    
    for _, row in inss_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        # Usar o valor absoluto do TXT
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_la:
            # Adicionais: somar
            total_adicionais += valor
            if codigo_la not in adicionais_por_la:
                adicionais_por_la[codigo_la] = []
            adicionais_por_la[codigo_la].append(valor)
        elif codigo_la in descontos_la:
            # Descontos: somar (para exibir separado)
            total_descontos += valor
            if codigo_la not in descontos_por_la:
                descontos_por_la[codigo_la] = []
            descontos_por_la[codigo_la].append(valor)
    
    # LOG: Detalhamento dos adicionais
    debug_log.append("➕ ADICIONAIS:")
    for la, valores in sorted(adicionais_por_la.items()):
        total_la = sum(valores)
        debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        for i, v in enumerate(valores, 1):
            debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  TOTAL ADICIONAIS: R$ {total_adicionais:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append("=" * 80)
    
    # LOG: Detalhamento dos descontos
    debug_log.append("➖ DESCONTOS:")
    for la, valores in sorted(descontos_por_la.items()):
        total_la = sum(valores)
        debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        for i, v in enumerate(valores, 1):
            debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  TOTAL DESCONTOS: R$ {total_descontos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append("=" * 80)
    
    # Calcular soma total do TXT: Adicionais - Descontos
    soma_txt = total_adicionais - total_descontos
    
    # Diferença = Resumo Geral - TXT
    diferenca = inss_resumo_geral - soma_txt
    
    debug_log.append(f"💰 CÁLCULO FINAL:")
    debug_log.append(f"  INSS TXT Total = {total_adicionais:,.2f} - {total_descontos:,.2f} = {soma_txt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  Diferença = {inss_resumo_geral:,.2f} - {soma_txt:,.2f} = {diferenca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    return {
        'INSS_Resumo_Geral': inss_resumo_geral,
        'INSS_TXT_Total': soma_txt,
        'INSS_Diferenca': diferenca,
        'INSS_TXT_Adicionais': total_adicionais,
        'INSS_TXT_Descontos': total_descontos,
        'debug_log': debug_log
    }


def confrontar_fgts(fgts_resumo_geral: float, df_lancamentos: pd.DataFrame, mapeamento: dict) -> dict:
    """
    Calcula o confronto do FGTS entre Resumo Geral e TXT.
    
    Fórmula:
    - FGTS_Resumo_Geral - Soma_TXT
    - Onde Soma_TXT = Σ(Adicionais) - Σ(Descontos)
    - Valores do TXT são usados com valor absoluto  
    - Adicionais são somados, Descontos são subtraídos
    
    Args:
        fgts_resumo_geral: FGTS Total Apurado do Resumo Geral
        df_lancamentos: DataFrame com os lançamentos do TXT (colunas: CodigoLA, Valor)
        mapeamento: Dicionário de mapeamento com seção FGTS
    
    Returns:
        dict com valores do resumo, TXT e diferença
    """
    if df_lancamentos.empty or 'FGTS' not in mapeamento:
        return {
            'FGTS_Resumo_Geral': fgts_resumo_geral,
            'FGTS_TXT_Total': 0.0,
            'FGTS_Diferenca': fgts_resumo_geral,
            'FGTS_TXT_Adicionais': 0.0,
            'FGTS_TXT_Descontos': 0.0,
            'debug_log': []
        }
    
    # Extrair códigos LA do mapeamento FGTS
    codigos_fgts = mapeamento['FGTS']
    
    # Códigos de empréstimo que devem ser EXCLUÍDOS do cálculo do FGTS
    codigos_emprestimo = ['30074', '30075', '40045', '50035', '70044', '70045']
    
    # Separar adicionais e descontos, EXCLUINDO códigos de empréstimo
    # Normalizar removendo zeros à esquerda para comparação
    adicionais_la = [
        str(int(item['codigo_lancamento'])) 
        for item in codigos_fgts 
        if item['tipo'] == 'Adicional' and str(int(item['codigo_lancamento'])) not in codigos_emprestimo
    ]
    descontos_la = [
        str(int(item['codigo_lancamento'])) 
        for item in codigos_fgts 
        if item['tipo'] == 'Desconto' and str(int(item['codigo_lancamento'])) not in codigos_emprestimo
    ]
    
    # Garantir que CodigoLA é string e normalizar (remover zeros à esquerda)
    df_lancamentos = df_lancamentos.copy()
    df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).apply(lambda x: str(int(x)) if x.isdigit() else x)
    
    # Filtrar lançamentos do TXT que são FGTS
    fgts_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_la + descontos_la)].copy()
    
    # LOG: Criar lista de debug
    debug_log = []
    debug_log.append(f"📋 Total de lançamentos no TXT: {len(df_lancamentos)}")
    debug_log.append(f"📋 Lançamentos FGTS encontrados: {len(fgts_lancamentos)}")
    debug_log.append(f"📋 Códigos LA Adicionais: {', '.join(adicionais_la)}")
    debug_log.append(f"📋 Códigos LA Descontos: {', '.join(descontos_la)}")
    debug_log.append("=" * 80)
    
    # Calcular soma
    total_adicionais = 0.0
    total_descontos = 0.0
    
    # Agrupar por código LA para log
    adicionais_por_la = {}
    descontos_por_la = {}
    
    for _, row in fgts_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        # Usar o valor absoluto do TXT
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_la:
            # Adicionais: somar
            total_adicionais += valor
            if codigo_la not in adicionais_por_la:
                adicionais_por_la[codigo_la] = []
            adicionais_por_la[codigo_la].append(valor)
        elif codigo_la in descontos_la:
            # Descontos: somar (para exibir separado)
            total_descontos += valor
            if codigo_la not in descontos_por_la:
                descontos_por_la[codigo_la] = []
            descontos_por_la[codigo_la].append(valor)
    
    # LOG: Detalhamento dos adicionais
    debug_log.append("➕ ADICIONAIS:")
    for la, valores in sorted(adicionais_por_la.items()):
        total_la = sum(valores)
        debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        for i, v in enumerate(valores, 1):
            debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  TOTAL ADICIONAIS: R$ {total_adicionais:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append("=" * 80)
    
    # LOG: Detalhamento dos descontos
    debug_log.append("➖ DESCONTOS:")
    for la, valores in sorted(descontos_por_la.items()):
        total_la = sum(valores)
        debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        for i, v in enumerate(valores, 1):
            debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  TOTAL DESCONTOS: R$ {total_descontos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append("=" * 80)
    
    # Calcular soma total do TXT: Adicionais - Descontos
    soma_txt = total_adicionais - total_descontos
    
    # Diferença = Resumo Geral - TXT
    diferenca = fgts_resumo_geral - soma_txt
    
    debug_log.append(f"💰 CÁLCULO FINAL:")
    debug_log.append(f"  FGTS TXT Total = {total_adicionais:,.2f} - {total_descontos:,.2f} = {soma_txt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  Diferença = {fgts_resumo_geral:,.2f} - {soma_txt:,.2f} = {diferenca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    return {
        'FGTS_Resumo_Geral': fgts_resumo_geral,
        'FGTS_TXT_Total': soma_txt,
        'FGTS_Diferenca': diferenca,
        'FGTS_TXT_Adicionais': total_adicionais,
        'FGTS_TXT_Descontos': total_descontos,
        'debug_log': debug_log
    }


def calcular_emprestimos_fgts(df_lancamentos: pd.DataFrame) -> dict:
    """
    Calcula os valores de empréstimos FGTS separadamente.
    
    Códigos de empréstimo (não devem entrar no cálculo do FGTS líquido):
    - 30074 (Desconto)
    - 30075 (Adicional)
    - 40045 (Adicional)
    - 50035 (Adicional)
    - 70044 (Desconto)
    - 70045 (Adicional)
    
    Fórmula: Empréstimos Total = Σ(Adicionais) - Σ(Descontos)
    
    Args:
        df_lancamentos: DataFrame com os lançamentos do TXT (colunas: CodigoLA, Valor)
    
    Returns:
        dict com valores de adicionais, descontos e total líquido de empréstimos
    """
    if df_lancamentos.empty:
        return {
            'Emprestimos_Total': 0.0,
            'Emprestimos_Adicionais': 0.0,
            'Emprestimos_Descontos': 0.0
        }
    
    # Códigos de empréstimo
    # Normalizar removendo zeros à esquerda para comparação
    adicionais_la = ['30075', '40045', '50035', '70045']
    descontos_la = ['30074', '70044']
    
    # Garantir que CodigoLA é string e normalizar (remover zeros à esquerda)
    df_lancamentos = df_lancamentos.copy()
    df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).apply(lambda x: str(int(x)) if x.isdigit() else x)
    
    # Filtrar lançamentos do TXT que são empréstimos
    emprestimos_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_la + descontos_la)].copy()
    
    # Calcular soma
    total_adicionais = 0.0
    total_descontos = 0.0
    
    for _, row in emprestimos_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        # Usar o valor absoluto do TXT
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_la:
            # Adicionais: somar
            total_adicionais += valor
        elif codigo_la in descontos_la:
            # Descontos: somar (para exibir separado)
            total_descontos += valor
    
    # Calcular total líquido: Adicionais - Descontos
    total_liquido = total_adicionais - total_descontos
    
    return {
        'Emprestimos_Total': total_liquido,
        'Emprestimos_Adicionais': total_adicionais,
        'Emprestimos_Descontos': total_descontos
    }


def calcular_prolabore_txt(df_lancamentos: pd.DataFrame) -> dict:
    """
    Calcula os valores de Pró-Labore e Autônomos do TXT.
    
    Códigos de Pró-Labore Sócios:
    - 30003 (Adicional)
    - 30064 (Adicional)
    - 30067 (Desconto)
    - 30066 (Desconto)
    
    Códigos de Autônomos:
    - 30060 (Adicional)
    - 30069 (Adicional)
    - 30070 (Desconto)
    - 30071 (Desconto)
    
    Fórmula: Total = Σ(Adicionais) - Σ(Descontos)
    
    Args:
        df_lancamentos: DataFrame com os lançamentos do TXT (colunas: CodigoLA, Valor)
    
    Returns:
        dict com valores separados de Sócios e Autônomos
    """
    if df_lancamentos.empty:
        return {
            'ProLabore_TXT_Total': 0.0,
            'ProLabore_TXT_Adicionais': 0.0,
            'ProLabore_TXT_Descontos': 0.0,
            'Autonomos_TXT_Total': 0.0,
            'Autonomos_TXT_Adicionais': 0.0,
            'Autonomos_TXT_Descontos': 0.0
        }
    
    # Códigos de Pró-Labore Sócios
    adicionais_socios = ['30003', '30064']
    descontos_socios = ['30067', '30066']
    
    # Códigos de Autônomos
    adicionais_autonomos = ['30060', '30069']
    descontos_autonomos = ['30070', '30071']
    
    # Garantir que CodigoLA é string e normalizar (remover zeros à esquerda)
    df_lancamentos = df_lancamentos.copy()
    df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).apply(lambda x: str(int(x)) if x.isdigit() else x)
    
    # === CALCULAR PRÓ-LABORE SÓCIOS ===
    prolabore_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_socios + descontos_socios)].copy()
    
    total_adicionais_socios = 0.0
    total_descontos_socios = 0.0
    
    for _, row in prolabore_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_socios:
            total_adicionais_socios += valor
        elif codigo_la in descontos_socios:
            total_descontos_socios += valor
    
    total_liquido_socios = total_adicionais_socios - total_descontos_socios
    
    # === CALCULAR AUTÔNOMOS ===
    autonomos_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_autonomos + descontos_autonomos)].copy()
    
    total_adicionais_autonomos = 0.0
    total_descontos_autonomos = 0.0
    
    for _, row in autonomos_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_autonomos:
            total_adicionais_autonomos += valor
        elif codigo_la in descontos_autonomos:
            total_descontos_autonomos += valor
    
    total_liquido_autonomos = total_adicionais_autonomos - total_descontos_autonomos
    
    return {
        'ProLabore_TXT_Total': total_liquido_socios,
        'ProLabore_TXT_Adicionais': total_adicionais_socios,
        'ProLabore_TXT_Descontos': total_descontos_socios,
        'Autonomos_TXT_Total': total_liquido_autonomos,
        'Autonomos_TXT_Adicionais': total_adicionais_autonomos,
        'Autonomos_TXT_Descontos': total_descontos_autonomos
    }


def confrontar_irrf(irrf_resumo_geral: float, df_lancamentos: pd.DataFrame, mapeamento: dict) -> dict:
    """
    Calcula o confronto do IRRF entre Resumo Geral e TXT.
    
    Fórmula:
    - IRRF_Resumo_Geral - Soma_TXT
    - Onde Soma_TXT = Σ(Adicionais) (não há descontos)
    - Valores do TXT são usados com valor absoluto  
    
    Args:
        irrf_resumo_geral: IRRF Total do Resumo Geral
        df_lancamentos: DataFrame com os lançamentos do TXT (colunas: CodigoLA, Valor)
        mapeamento: Dicionário de mapeamento com seção IRRF
    
    Returns:
        dict com valores do resumo, TXT e diferença
    """
    if df_lancamentos.empty or 'IRRF' not in mapeamento:
        return {
            'IRRF_Resumo_Geral': irrf_resumo_geral,
            'IRRF_TXT_Total': 0.0,
            'IRRF_Diferenca': irrf_resumo_geral,
            'IRRF_TXT_Adicionais': 0.0,
            'IRRF_TXT_Descontos': 0.0,
            'debug_log': []
        }
    
    # Extrair códigos LA do mapeamento IRRF
    codigos_irrf = mapeamento['IRRF']
    
    # Separar adicionais e descontos
    # Normalizar removendo zeros à esquerda para comparação
    adicionais_la = [str(int(item['codigo_lancamento'])) for item in codigos_irrf if item['tipo'] == 'Adicional']
    descontos_la = [str(int(item['codigo_lancamento'])) for item in codigos_irrf if item['tipo'] == 'Desconto']
    
    # Garantir que CodigoLA é string e normalizar (remover zeros à esquerda)
    df_lancamentos = df_lancamentos.copy()
    df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).apply(lambda x: str(int(x)) if x.isdigit() else x)
    
    # Filtrar lançamentos do TXT que são IRRF
    irrf_lancamentos = df_lancamentos[df_lancamentos['CodigoLA'].isin(adicionais_la + descontos_la)].copy()
    
    # LOG: Criar lista de debug
    debug_log = []
    debug_log.append(f"📋 Total de lançamentos no TXT: {len(df_lancamentos)}")
    debug_log.append(f"📋 Lançamentos IRRF encontrados: {len(irrf_lancamentos)}")
    debug_log.append(f"📋 Códigos LA Adicionais: {', '.join(adicionais_la)}")
    if descontos_la:
        debug_log.append(f"📋 Códigos LA Descontos: {', '.join(descontos_la)}")
    else:
        debug_log.append(f"📋 Códigos LA Descontos: (nenhum)")
    debug_log.append("=" * 80)
    
    # Calcular soma
    total_adicionais = 0.0
    total_descontos = 0.0
    
    # Agrupar por código LA para log
    adicionais_por_la = {}
    descontos_por_la = {}
    
    for _, row in irrf_lancamentos.iterrows():
        codigo_la = str(row['CodigoLA'])
        # Usar o valor absoluto do TXT
        valor = abs(row['Valor'])
        
        if codigo_la in adicionais_la:
            # Adicionais: somar
            total_adicionais += valor
            if codigo_la not in adicionais_por_la:
                adicionais_por_la[codigo_la] = []
            adicionais_por_la[codigo_la].append(valor)
        elif codigo_la in descontos_la:
            # Descontos: somar (para exibir separado)
            total_descontos += valor
            if codigo_la not in descontos_por_la:
                descontos_por_la[codigo_la] = []
            descontos_por_la[codigo_la].append(valor)
    
    # LOG: Detalhamento dos adicionais
    debug_log.append("➕ ADICIONAIS:")
    for la, valores in sorted(adicionais_por_la.items()):
        total_la = sum(valores)
        debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        for i, v in enumerate(valores, 1):
            debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  TOTAL ADICIONAIS: R$ {total_adicionais:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append("=" * 80)
    
    # LOG: Detalhamento dos descontos (se houver)
    if descontos_por_la:
        debug_log.append("➖ DESCONTOS:")
        for la, valores in sorted(descontos_por_la.items()):
            total_la = sum(valores)
            debug_log.append(f"  LA {la}: {len(valores)} lançamento(s) = R$ {total_la:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            for i, v in enumerate(valores, 1):
                debug_log.append(f"    #{i}: R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        debug_log.append(f"  TOTAL DESCONTOS: R$ {total_descontos:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        debug_log.append("=" * 80)
    
    # Calcular soma total do TXT: Adicionais - Descontos
    soma_txt = total_adicionais - total_descontos
    
    # Diferença = Resumo Geral - TXT
    diferenca = irrf_resumo_geral - soma_txt
    
    debug_log.append(f"💰 CÁLCULO FINAL:")
    if total_descontos > 0:
        debug_log.append(f"  IRRF TXT Total = {total_adicionais:,.2f} - {total_descontos:,.2f} = {soma_txt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    else:
        debug_log.append(f"  IRRF TXT Total = {total_adicionais:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    debug_log.append(f"  Diferença = {irrf_resumo_geral:,.2f} - {soma_txt:,.2f} = {diferenca:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    
    return {
        'IRRF_Resumo_Geral': irrf_resumo_geral,
        'IRRF_TXT_Total': soma_txt,
        'IRRF_Diferenca': diferenca,
        'IRRF_TXT_Adicionais': total_adicionais,
        'IRRF_TXT_Descontos': total_descontos,
        'debug_log': debug_log
    }


def calcular_liquidos_por_categoria(df_eventos_mapeados: pd.DataFrame) -> pd.DataFrame:
    """Calcula o valor líquido por categoria usando Adicional (+) e Desconto (-)."""
    if df_eventos_mapeados.empty:
        return pd.DataFrame(columns=['Categoria', 'Total_Adicionais', 'Total_Descontos', 'Liquido'])
    
    # Filtrar apenas eventos mapeados
    df_mapeados = df_eventos_mapeados[df_eventos_mapeados['CodigoLA'].notna()].copy()
    
    if df_mapeados.empty:
        return pd.DataFrame(columns=['Categoria', 'Total_Adicionais', 'Total_Descontos', 'Liquido'])
    
    # Agrupar por categoria e tipo
    resumo = []
    
    for categoria in df_mapeados['Categoria'].unique():
        df_cat = df_mapeados[df_mapeados['Categoria'] == categoria]
        
        # Separar por tipo
        adicionais = df_cat[df_cat['Tipo'] == 'Adicional']['Total'].sum()
        descontos = df_cat[df_cat['Tipo'] == 'Desconto']['Total'].sum()
        
        # Calcular líquido: adicionais - descontos
        liquido = adicionais - descontos
        
        resumo.append({
            'Categoria': categoria,
            'Total_Adicionais': adicionais,
            'Total_Descontos': descontos,
            'Liquido': liquido
        })
    
    return pd.DataFrame(resumo)





def realizar_confronto(df_eventos_mapeados: pd.DataFrame, df_lancamentos: pd.DataFrame) -> pd.DataFrame:
    """Realiza confronto entre eventos mapeados (PDF) e lançamentos (TXT)."""
    # Validar DataFrames de entrada
    if df_eventos_mapeados.empty:
        return pd.DataFrame(columns=['CodigoLA', 'Categoria', 'Eventos_PDF', 'Descricao_Eventos_PDF', 'Descricao_TXT', 'Total_PDF', 'Total_TXT', 'Diferenca', 'Status'])

    # Debug: quantidade de eventos mapeados
    eventos_com_la = df_eventos_mapeados[df_eventos_mapeados['CodigoLA'].notna()]
    
    # Normalizar CodigoLA para string (remover .0, espaços, etc)
    eventos_com_la = eventos_com_la.copy()
    eventos_com_la['CodigoLA'] = eventos_com_la['CodigoLA'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    # Agrupar eventos por LA E Categoria (para separar eventos de categorias diferentes)
    if eventos_com_la.empty:
        pdf_por_la = pd.DataFrame(columns=['CodigoLA', 'Categoria', 'Eventos_PDF', 'Descricao_Eventos_PDF', 'Total_PDF'])
    else:
        pdf_por_la = eventos_com_la.groupby(['CodigoLA', 'Categoria']).agg({
            'Total': 'sum',
            'Codigo': lambda x: ', '.join(sorted(set(str(c).zfill(3) for c in x))),  # Códigos dos eventos
            'Descricao': lambda x: ', '.join(sorted(set(str(d) for d in x if d)))  # Descrições dos eventos
        }).reset_index()
        # Após groupby+reset_index, as colunas são: CodigoLA, Categoria, Total, Codigo, Descricao
        pdf_por_la.columns = ['CodigoLA', 'Categoria', 'Total_PDF', 'Eventos_PDF', 'Descricao_Eventos_PDF']
        # Garantir tipo numérico
        pdf_por_la['Total_PDF'] = pd.to_numeric(pdf_por_la['Total_PDF'], errors='coerce').fillna(0)
        
        # Reorganizar colunas para ordem esperada
        pdf_por_la = pdf_por_la[['CodigoLA', 'Categoria', 'Eventos_PDF', 'Descricao_Eventos_PDF', 'Total_PDF']]

    # Agrupar lançamentos por LA
    if df_lancamentos.empty or 'CodigoLA' not in df_lancamentos.columns:
        txt_por_la = pd.DataFrame({'CodigoLA': [], 'Total_TXT': [], 'Descricao_TXT': []}).astype({'Total_TXT': 'float64', 'Descricao_TXT': 'str'})
    else:
        # Normalizar CodigoLA do TXT também
        df_lancamentos = df_lancamentos.copy()
        df_lancamentos['CodigoLA'] = df_lancamentos['CodigoLA'].astype(str).str.replace('.0', '', regex=False).str.strip()
        
        # Agregar valores e descrições por CodigoLA
        txt_por_la = df_lancamentos.groupby('CodigoLA').agg({
            'Valor': 'sum',
            'Descricao': lambda x: ' | '.join(sorted(set(str(d) for d in x if d)))  # Agregar descrições únicas
        }).reset_index()
        txt_por_la.columns = ['CodigoLA', 'Total_TXT', 'Descricao_TXT']
        # Garantir tipo numérico
        txt_por_la['Total_TXT'] = pd.to_numeric(txt_por_la['Total_TXT'], errors='coerce').fillna(0)

    # Armazenar debug info
    import streamlit as st
    st.session_state['confronto_debug'] = {
        'eventos_total': len(df_eventos_mapeados),
        'eventos_com_la': len(eventos_com_la),
        'pdf_las_unicos': len(pdf_por_la),
        'txt_las_unicos': len(txt_por_la),
        'pdf_las_sample': list(pdf_por_la['CodigoLA'].head(5)) if not pdf_por_la.empty else [],
        'txt_las_sample': list(txt_por_la['CodigoLA'].head(5)) if not txt_por_la.empty else [],
    }

    # Merge completo (outer join)
    confronto = pd.merge(pdf_por_la, txt_por_la, on='CodigoLA', how='outer')

    # Preencher NaN com 0 e garantir tipo numérico
    confronto['Total_PDF'] = pd.to_numeric(confronto['Total_PDF'], errors='coerce').fillna(0)
    confronto['Total_TXT'] = pd.to_numeric(confronto['Total_TXT'], errors='coerce').fillna(0)
    confronto['Categoria'] = confronto['Categoria'].fillna('Sem Categoria')
    confronto['Eventos_PDF'] = confronto['Eventos_PDF'].fillna('-')  # Preencher eventos vazios com hífen
    confronto['Descricao_Eventos_PDF'] = confronto['Descricao_Eventos_PDF'].fillna('-')  # Preencher descrição de eventos vazia
    confronto['Descricao_TXT'] = confronto['Descricao_TXT'].fillna('-')  # Preencher descrição vazia com hífen

    # Calcular diferença (agora ambas as colunas são garantidamente float)
    confronto['Diferenca'] = confronto['Total_PDF'].astype(float) - confronto['Total_TXT'].astype(float)

    # Determinar status
    def determinar_status(row):
        if abs(row['Diferenca']) < 0.01:
            return '✅ OK'
        elif row['Total_PDF'] == 0:
            return '📝 Apenas no TXT'
        elif row['Total_TXT'] == 0:
            return '📄 Apenas no PDF'
        else:
            return '⚠️ Divergência'

    confronto['Status'] = confronto.apply(determinar_status, axis=1)
    
    # ========== FILTRAR CÓDIGOS INDESEJADOS ==========
    # Códigos para EXCLUIR da tabela de confronto
    codigos_excluir_inss = ['30072', '30073']  # INSS: crédito/débito trabalhador
    
    # FGTS: Manter APENAS códigos de empréstimo, remover todos os outros
    codigos_fgts_emprestimo = ['30074', '30075', '40045', '50035', '70044', '70045']
    codigos_fgts_todos = ['30051', '30059', '50026', '70015']  # Outros códigos FGTS do mapeamento
    codigos_excluir_fgts = codigos_fgts_todos  # Excluir todos EXCETO os de empréstimo
    
    # Normalizar CodigoLA para comparação
    confronto['CodigoLA_normalized'] = confronto['CodigoLA'].astype(str).apply(
        lambda x: str(int(x)) if x.replace('.', '').isdigit() else x
    )
    
    # Aplicar filtro: remover linhas com códigos indesejados
    mask_excluir = (
        confronto['CodigoLA_normalized'].isin(codigos_excluir_inss) |
        confronto['CodigoLA_normalized'].isin(codigos_excluir_fgts)
    )
    
    # Manter apenas as linhas que NÃO devem ser excluídas
    confronto = confronto[~mask_excluir].copy()
    
    # Remover coluna auxiliar
    confronto = confronto.drop('CodigoLA_normalized', axis=1)

    # Ordenar por status (divergências primeiro)
    ordem_status = {'⚠️ Divergência': 0, '📄 Apenas no PDF': 1, '📝 Apenas no TXT': 2, '✅ OK': 3}
    confronto['_ordem'] = confronto['Status'].map(ordem_status)
    confronto = confronto.sort_values('_ordem').drop('_ordem', axis=1)

    return confronto


# ==================== INTERFACE STREAMLIT ====================

def main():
    st.title("📊 Sistema Moderno de Processamento de Resumos DP")
    st.markdown("---")

    # Sidebar para uploads
    with st.sidebar:
        st.header("📁 Upload de Arquivos")

        # Upload de PDFs
        st.subheader("1️⃣ Resumos em PDF")
        pdf_files = st.file_uploader(
            "Selecione os resumos (13º, Adiantamento, Férias, Folha, Rescisão, Geral)",
            type=['pdf'],
            accept_multiple_files=True,
            help="Arraste ou selecione múltiplos arquivos PDF"
        )

        # Upload de TXT (opcional)
        st.subheader("2️⃣ Lançamentos TXT (Opcional)")
        txt_file = st.file_uploader(
            "Arquivo TXT/CSV contábil",
            type=['txt', 'csv'],
            help="Opcional: Para realizar confronto PDF x TXT"
        )

        st.markdown("---")

        # Botão de processar
        processar = st.button("🚀 Processar", type="primary", use_container_width=True)

    # Área principal
    if not pdf_files:
        st.info("👈 Faça upload dos arquivos PDF na barra lateral para começar")

        # Instruções
        with st.expander("📖 Instruções de Uso", expanded=True):
            st.markdown("""
            ### Como usar este sistema:

            **1. Upload de PDFs**
            - Faça upload de todos os resumos: 13º, Adiantamento, Férias, Folha, Rescisão e Geral
            - O sistema identifica automaticamente o tipo de cada resumo pelo nome do arquivo

            **2. Upload do TXT (Opcional)**
            - Se você deseja realizar o confronto com lançamentos contábeis, faça upload do arquivo TXT/CSV
            - Formato esperado: Coluna 2 = Código LA, Coluna 4 = Valor

            **3. Processamento**
            - Clique em "🚀 Processar" para iniciar
            - O sistema irá extrair eventos e impostos automaticamente

            **4. Resultados**
            - Visualize os dados extraídos em tabelas interativas
            - Baixe o relatório completo em Excel
            - Se TXT fornecido, veja o confronto detalhado com status
            """)

        return

    # Verificar se há dados no session_state (de processamento anterior)
    tem_dados_cache = ('df_eventos' in st.session_state and 
                       'eventos_por_categoria' in st.session_state)

    if processar:
        with st.spinner("Processando arquivos..."):
            # Estruturas de dados
            eventos_por_categoria = defaultdict(list)
            impostos_geral = None

            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Processar cada PDF
            for idx, pdf_file in enumerate(pdf_files):
                tipo = identificar_tipo_resumo(pdf_file.name)
                status_text.text(f"Processando: {pdf_file.name} ({tipo})")

                pdf_bytes = pdf_file.read()

                if tipo == "Geral":
                    impostos_geral = extrair_impostos_resumo_geral(pdf_bytes)
                elif tipo != "Desconhecido":
                    df_eventos = extrair_eventos_resumo_simples(pdf_bytes)
                    if not df_eventos.empty:
                        df_eventos["Categoria"] = tipo
                        df_eventos["Arquivo"] = pdf_file.name
                        eventos_por_categoria[tipo].append(df_eventos)

                progress_bar.progress((idx + 1) / len(pdf_files))

            status_text.empty()
            progress_bar.empty()

            # Consolidar eventos
            todos_eventos = []
            for tipo, dfs in eventos_por_categoria.items():
                todos_eventos.extend(dfs)

            df_eventos_consolidado = pd.concat(todos_eventos, ignore_index=True) if todos_eventos else pd.DataFrame()

            # Armazenar no session_state
            st.session_state['df_eventos'] = df_eventos_consolidado
            st.session_state['impostos_geral'] = impostos_geral
            st.session_state['eventos_por_categoria'] = dict(eventos_por_categoria)
            
            # ========== ABA: VALORES LÍQUIDOS POR CATEGORIA ==========
            # Só mostrar se temos eventos e mapeamento
            if not df_eventos_consolidado.empty:
                # Carregar mapeamento
                mapeamento = load_mapeamento()
                
                if mapeamento:
                    # Mapear eventos
                    df_eventos_mapeados_liquidos = mapear_eventos_para_lancamentos(df_eventos_consolidado, mapeamento)
                    
                    # Armazenar para uso no Excel
                    st.session_state['df_eventos_mapeados_liquidos'] = df_eventos_mapeados_liquidos
                    
                    # Calcular líquidos
                    df_liquidos = calcular_liquidos_por_categoria(df_eventos_mapeados_liquidos)
                    
                    if not df_liquidos.empty:
                        pass # Data stored, no display needed here
            
            # Se não há TXT, marcar como processado agora
            if not txt_file:
                st.session_state['processado'] = True
            
            # ========== CONFRONTO COM TXT ==========
            if txt_file and not df_eventos_consolidado.empty:
                with st.spinner("Processando TXT e realizando confronto..."):
                    # Parsear TXT
                    txt_bytes = txt_file.read()
                    df_lancamentos = parse_txt_lancamentos(txt_bytes)

                    if df_lancamentos.empty:
                        st.warning("⚠️ Nenhum lançamento válido encontrado no arquivo TXT.")
                    else:
                        # Carregar mapeamento
                        mapeamento = load_mapeamento()

                        if not mapeamento:
                            st.error("❌ Arquivo de mapeamento não encontrado. O confronto requer o arquivo `mapeamento_dp.json`.")
                        else:
                            # Calcular confronto do INSS (se há impostos gerais)
                            if impostos_geral and 'INSS_Total_Liquido' in impostos_geral:
                                confronto_inss_result = confrontar_inss(
                                    impostos_geral['INSS_Total_Liquido'],
                                    df_lancamentos,
                                    mapeamento
                                )
                                st.session_state['confronto_inss'] = confronto_inss_result
                            
                            # Calcular confronto do FGTS (se há impostos gerais)
                            if impostos_geral and 'FGTS_Total_Apurado' in impostos_geral:
                                confronto_fgts_result = confrontar_fgts(
                                    impostos_geral['FGTS_Total_Apurado'],
                                    df_lancamentos,
                                    mapeamento
                                )
                                st.session_state['confronto_fgts'] = confronto_fgts_result
                                
                                # Calcular empréstimos FGTS separadamente
                                emprestimos_fgts_result = calcular_emprestimos_fgts(df_lancamentos)
                                st.session_state['emprestimos_fgts'] = emprestimos_fgts_result
                            
                            # Calcular confronto do IRRF (se há impostos gerais)
                            if impostos_geral and 'IRRF_Total' in impostos_geral:
                                confronto_irrf_result = confrontar_irrf(
                                    impostos_geral['IRRF_Total'],
                                    df_lancamentos,
                                    mapeamento
                                )
                                st.session_state['confronto_irrf'] = confronto_irrf_result
                            
                            # Calcular Pró-Labore do TXT
                            prolabore_txt_result = calcular_prolabore_txt(df_lancamentos)
                            st.session_state['prolabore_txt'] = prolabore_txt_result
                            
                            # Mapear eventos
                            df_eventos_mapeados = mapear_eventos_para_lancamentos(df_eventos_consolidado, mapeamento)
                            
                            # Armazenar eventos mapeados no session_state para uso no Excel
                            st.session_state['df_eventos_mapeados'] = df_eventos_mapeados

                            # Realizar confronto
                            df_confronto = realizar_confronto(df_eventos_mapeados, df_lancamentos)

                            # Armazenar confronto no session_state
                            st.session_state['df_confronto'] = df_confronto
                            
                            # Estatísticas
                            total_ok = len(df_confronto[df_confronto['Status'] == '✅ OK'])
                            total_divergencia = len(df_confronto[df_confronto['Status'] == '⚠️ Divergência'])
                            total_apenas_pdf = len(df_confronto[df_confronto['Status'] == '📄 Apenas no PDF'])
                            total_apenas_txt = len(df_confronto[df_confronto['Status'] == '📝 Apenas no TXT'])

            # Marcar como processado para exibir resultados
            st.session_state['processado'] = True

    # ========== EXIBIÇÃO DE RESULTADOS (usa dados do session_state) ==========
    # Este bloco é executado sempre que há dados processados, mesmo quando apenas filtros mudam
    
    if st.session_state.get('processado', False):
        # Recuperar dados do session_state
        df_eventos_consolidado = st.session_state.get('df_eventos', pd.DataFrame())
        eventos_por_categoria = st.session_state.get('eventos_por_categoria', {})
        impostos_geral = st.session_state.get('impostos_geral', None)
        
        if processar:
            st.success("✅ Processamento concluído!")
        
        # Informações de Debug (se disponíveis)
        if 'pdf_debug' in st.session_state or 'txt_debug' in st.session_state:
            with st.expander("🔍 Informações de Debug da Extração"):
                col_debug1, col_debug2 = st.columns(2)
                
                with col_debug1:
                    if 'pdf_debug' in st.session_state:
                        pdf_info = st.session_state['pdf_debug']
                        st.markdown("**📄 Extração de PDF:**")
                        st.write(f"- Linhas processadas: {pdf_info.get('linhas_processadas', 0)}")
                        st.write(f"- Linhas matcheadas: {pdf_info.get('linhas_matcheadas', 0)}")
                        st.write(f"- Eventos extraídos: {pdf_info.get('eventos_extraidos', 0)}")
                        
                        # Mostrar formato detectado
                        formato = pdf_info.get('formato_detectado', 'unknown')
                        if formato == 'with_prefix':
                            st.success("✅ Formato: **COM** prefixo +/- (formato antigo)")
                        elif formato == 'without_prefix':
                            st.info("ℹ️ Formato: **SEM** prefixo +/- (formato novo - usando mapeamento para tipos)")
                        else:
                            st.warning("⚠️ Formato: Desconhecido ou não detectado")
                        
                        if pdf_info.get('linhas_matcheadas', 0) == 0:
                            st.warning("⚠️ Nenhuma linha foi reconhecida como evento no PDF. Verifique o formato do arquivo.")
                
                with col_debug2:
                    if 'txt_debug' in st.session_state:
                        txt_info = st.session_state['txt_debug']
                        st.markdown("**📋 Extração de TXT:**")
                        st.write(f"- Linhas processadas: {txt_info.get('linhas_processadas', 0)}")
                        st.write(f"- Linhas válidas: {txt_info.get('linhas_validas', 0)}")
                        st.write(f"- Lançamentos extraídos: {txt_info.get('lancamentos_extraidos', 0)}")
                        
                        if txt_info.get('lancamentos_extraidos', 0) == 0:
                            st.warning("⚠️ Nenhum lançamento foi extraído do TXT. Verifique o formato do arquivo.")


        # ========== VALORES LÍQUIDOS POR CATEGORIA ==========
        if 'df_eventos_mapeados_liquidos' in st.session_state:
            st.markdown("---")
            st.header("Resumos Líquidos")
            st.info("📌 Valores calculados com base nos **Adicionais (+)** e **Descontos (-)** dos resumos")
            
            try:
                df_liquidos = calcular_liquidos_por_categoria(st.session_state['df_eventos_mapeados_liquidos'])
                
                if not df_liquidos.empty:
                    # Cards estilizados para cada categoria
                    for _, row in df_liquidos.iterrows():
                        categoria = row['Categoria']
                        adicionais = row['Total_Adicionais']
                        descontos = row['Total_Descontos']
                        liquido = row['Liquido']  # Nome correto da coluna
                        
                        # Definir cor do gradiente baseado na categoria
                        cores_gradiente = {
                            '13ª parcela': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            '13º Segunda Parcela': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            'Adiantamento': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            'Folha': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                            'Férias': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                            'Rescisão': 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
                        }
                        
                        gradiente = cores_gradiente.get(categoria, 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
                        
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 3])
                        
                        with col1:
                            st.markdown(f"""
                            <div style="background: #f0f2f6; padding: 15px; border-radius: 8px; text-align: center;
                                        min-height: 85px; display: flex; align-items: center; justify-content: center;">
                                <h4 style="color: #333; margin: 0; font-size: 1em;">{categoria}</h4>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            st.markdown(f"""
                            <div style="background: #d4edda; padding: 15px; border-radius: 8px; text-align: center;
                                        border: 1px solid #c3e6cb; min-height: 85px;">
                                <p style="color: #155724; margin: 0; font-size: 0.85em;">➕ Adicionais</p>
                                <p style="color: #155724; font-size: 1.3em; font-weight: bold; margin: 5px 0;">
                                    {money(adicionais)}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col3:
                            st.markdown(f"""
                            <div style="background: #f8d7da; padding: 15px; border-radius: 8px; text-align: center;
                                        border: 1px solid #f5c6cb; min-height: 85px;">
                                <p style="color: #721c24; margin: 0; font-size: 0.85em;">➖ Descontos</p>
                                <p style="color: #721c24; font-size: 1.3em; font-weight: bold; margin: 5px 0;">
                                    {money(descontos)}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col4:
                            st.markdown(f"""
                            <div style="background: {gradiente};
                                        padding: 15px; border-radius: 8px; text-align: center;
                                        box-shadow: 0 4px 6px rgba(0,0,0,0.15); min-height: 85px;">
                                <p style="color: white; margin: 0; font-size: 0.85em;">💰 LÍQUIDO</p>
                                <p style="color: white; font-size: 1.5em; font-weight: bold; margin: 5px 0;">
                                    {money(liquido)}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("")  # Espaçamento
                        
            except Exception as e:
                st.error(f"Erro ao exibir valores líquidos: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

        # ========== TABELA DE CONFRONTO DETALHADO (PDF x TXT) ==========
        if 'df_confronto' in st.session_state:
            st.markdown("---")
            st.header("📊 Confronto Resumo x Lançamentos Contábeis ")
            # st.info("📌 Comparação detalhada entre eventos dos Resumos e Lançamentos Contábeis")
            
            df_confronto = st.session_state['df_confronto']
            
            # Estatísticas
            total_ok = len(df_confronto[df_confronto['Status'] == '✅ OK'])
            total_divergencia = len(df_confronto[df_confronto['Status'] == '⚠️ Divergência'])
            total_apenas_pdf = len(df_confronto[df_confronto['Status'] == '📄 Apenas no PDF'])
            total_apenas_txt = len(df_confronto[df_confronto['Status'] == '📝 Apenas no TXT'])

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("✅ OK", total_ok)
            col2.metric("⚠️ Divergências", total_divergencia)
            col3.metric("📄 Apenas PDF", total_apenas_pdf)
            col4.metric("📝 Apenas TXT", total_apenas_txt)

            # Informações de Debug do Confronto
            # if 'confronto_debug' in st.session_state:
            #     with st.expander("🔍 Debug: Informações do Confronto"):
            #         debug_info = st.session_state['confronto_debug']
                    
            #         col_d1, col_d2 = st.columns(2)
                    
            #         with col_d1:
            #             st.markdown("**📄 Eventos PDF:**")
            #             st.write(f"- Total eventos: {debug_info.get('eventos_total', 0)}")
            #             st.write(f"- Eventos com LA: {debug_info.get('eventos_com_la', 0)}")
            #             st.write(f"- Códigos LA únicos: {debug_info.get('pdf_las_unicos', 0)}")
                        
            #             if debug_info.get('pdf_las_sample'):
            #                 st.write("- Amostra de LAs:")
            #                 for la in debug_info['pdf_las_sample']:
            #                     st.code(la, language=None)
                        
            #             if debug_info.get('eventos_com_la', 0) == 0:
            #                 st.error("⚠️ PROBLEMA: Nenhum evento tem CodigoLA mapeado!")
            #                 st.info("Verifique se os códigos de eventos do PDF existem no mapeamento_dp.json para a categoria correta.")
                    
            #         with col_d2:
            #             st.markdown("**📝 Lançamentos TXT:**")
            #             st.write(f"- Códigos LA únicos: {debug_info.get('txt_las_unicos', 0)}")
                        
            #             if debug_info.get('txt_las_sample'):
            #                 st.write("- Amostra de LAs:")
            #                 for la in debug_info['txt_las_sample']:
            #                     st.code(la, language=None)

            # st.markdown("")

            # Filtro por status
            status_filtro = st.multiselect(
                "Filtrar por status:",
                ['✅ OK', '⚠️ Divergência', '📄 Apenas no PDF', '📝 Apenas no TXT'],
                default=['⚠️ Divergência', '📄 Apenas no PDF', '📝 Apenas no TXT'],
                key="status_filtro_confronto"
            )

            df_confronto_filtrado = df_confronto[df_confronto['Status'].isin(status_filtro)].copy()

            # Formatar valores
            df_confronto_filtrado['Total_PDF'] = df_confronto_filtrado['Total_PDF'].apply(money)
            df_confronto_filtrado['Total_TXT'] = df_confronto_filtrado['Total_TXT'].apply(money)
            df_confronto_filtrado['Diferenca'] = df_confronto_filtrado['Diferenca'].apply(money)

            st.dataframe(df_confronto_filtrado, use_container_width=True, hide_index=True, height=400)

        # ========== IMPOSTOS CONSOLIDADOS ==========
        if impostos_geral:
            st.markdown("---")
            st.header("📑 Impostos de Folha")
            st.info("📌 Conforme apuração do Resumo Geral")
            
            # Cards principais (INSS, FGTS, IRRF Total)
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">💰 INSS</h4>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(impostos_geral['INSS_Total_Liquido'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">🏦 FGTS</h4>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(impostos_geral['FGTS_Total_Apurado'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">📊 IRRF</h4>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(impostos_geral['IRRF_Total'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("")
            
            # Card de Empréstimos FGTS (se houver dados de TXT)
            if 'emprestimos_fgts' in st.session_state:
                emprestimos = st.session_state['emprestimos_fgts']
                
                # Exibir card de empréstimos
                col_emp = st.columns(1)[0]
                with col_emp:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">💳 Empréstimo Crédito Trabalhador</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Empréstimo consignado repassado através do FGTS</p>
                        <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(emprestimos['Emprestimos_Total'])}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detalhes em expander
#                 with st.expander("🔍 Ver Detalhes dos Empréstimos FGTS"):
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.metric("➕ Adicionais", money(emprestimos['Emprestimos_Adicionais']))
#                         st.caption("Códigos: 30075, 40045, 50035, 70045")
#                     with col2:
#                         st.metric("➖ Descontos", money(emprestimos['Emprestimos_Descontos']))
#                         st.caption("Códigos: 30074, 70044")
                    
#                     st.markdown("---")
#                     st.markdown("### 📐 Fórmula do Cálculo:")
#                     st.code(f"""
#                         Empréstimos Total = Adicionais - Descontos
#                         Empréstimos Total = {money(emprestimos['Emprestimos_Adicionais'])} - {money(emprestimos['Emprestimos_Descontos'])}
#                         Empréstimos Total = {money(emprestimos['Emprestimos_Total'])}

# ℹ️ Estes valores NÃO são incluídos no cálculo do FGTS Total Apurado.
#                     """, language="text")

            st.markdown("")

            



        # ========== CONFRONTO INSS (TXT vs Resumo Geral) ==========
        if 'confronto_inss' in st.session_state and impostos_geral:
            st.markdown("---")
            st.header("📊 Confronto INSS - Resumo Geral x Lançamentos Contábeis")
            
            confronto_inss = st.session_state['confronto_inss']
            
            # Cards principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">💰 INSS Resumo Geral</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Total Líquido</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_inss['INSS_Resumo_Geral'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">📝 INSS - Lanc. Contábeis</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Adicionais - Descontos</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_inss['INSS_TXT_Total'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                diferenca = confronto_inss['INSS_Diferenca']
                # Definir cor baseada na diferença (verde se OK, vermelho se divergente)
                cor_valor = '#28a745' if abs(diferenca) < 0.01 else '#dc3545'
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Geral - TXT</p>
                    <p style="color: {cor_valor}; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(diferenca)}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detalhes em expander
            with st.expander("🔍 Ver Detalhes do Cálculo INSS"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("➕ Adicionais TXT", money(confronto_inss['INSS_TXT_Adicionais']))
                with col2:
                    st.metric("➖ Descontos TXT", money(confronto_inss['INSS_TXT_Descontos']))
                
                st.markdown("---")
                st.markdown("### 📐 Fórmula do Cálculo:")
                st.code(f"""
INSS Total (TXT) = Adicionais - Descontos
INSS Total (TXT) = {money(confronto_inss['INSS_TXT_Adicionais'])} - {money(confronto_inss['INSS_TXT_Descontos'])}
INSS Total (TXT) = {money(confronto_inss['INSS_TXT_Total'])}

Diferença = Resumo Geral - TXT
Diferença = {money(confronto_inss['INSS_Resumo_Geral'])} - {money(confronto_inss['INSS_TXT_Total'])}
Diferença = {money(diferenca)}
                """, language="text")
            
            # Debug log detalhado
            if 'debug_log' in confronto_inss and confronto_inss['debug_log']:
                with st.expander("🐛 Ver Log Detalhado dos Lançamentos TXT (Debug)"):
                    st.markdown("### 📋 Detalhamento Completo dos Lançamentos INSS")
                    st.info("Este log mostra TODOS os lançamentos do TXT que foram somados no cálculo do INSS.")
                    for line in confronto_inss['debug_log']:
                        st.text(line)
            
        # ========== CONFRONTO FGTS (TXT vs Resumo Geral) ==========
        if 'confronto_fgts' in st.session_state and impostos_geral:
            st.markdown("---")
            st.header("📊 Confronto FGTS - Resumo Geral x Lançamentos Contábeis")
            
            confronto_fgts = st.session_state['confronto_fgts']
            
            # Cards principais
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">🏦 FGTS Resumo Geral</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Total Apurado</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_fgts['FGTS_Resumo_Geral'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">📝 FGTS Lanc. Contábeis</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Adicionais - Descontos</p>
                    <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(confronto_fgts['FGTS_TXT_Total'])}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                diferenca_fgts = confronto_fgts['FGTS_Diferenca']
                # Definir cor baseada na diferença (verde se OK, vermelho se divergente)
                cor_valor_fgts = '#28a745' if abs(diferenca_fgts) < 0.01 else '#dc3545'
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                            padding: 20px; border-radius: 10px; text-align: center;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
                    <p style="color: white; font-size: 0.85em; opacity: 0.9;">Geral - TXT</p>
                    <p style="color: {cor_valor_fgts}; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                        {money(diferenca_fgts)}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detalhes em expander
            with st.expander("🔍 Ver Detalhes do Cálculo FGTS"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("➕ Adicionais TXT", money(confronto_fgts['FGTS_TXT_Adicionais']))
                with col2:
                    st.metric("➖ Descontos TXT", money(confronto_fgts['FGTS_TXT_Descontos']))
                
                st.markdown("---")
                st.markdown("### 📐 Fórmula do Cálculo:")
                st.code(f"""
FGTS Total (TXT) = Adicionais - Descontos
FGTS Total (TXT) = {money(confronto_fgts['FGTS_TXT_Adicionais'])} - {money(confronto_fgts['FGTS_TXT_Descontos'])}
FGTS Total (TXT) = {money(confronto_fgts['FGTS_TXT_Total'])}

Diferença = Resumo Geral - TXT
Diferença = {money(confronto_fgts['FGTS_Resumo_Geral'])} - {money(confronto_fgts['FGTS_TXT_Total'])}
Diferença = {money(diferenca_fgts)}
                """, language="text")
            
            # Debug log detalhado
            if 'debug_log' in confronto_fgts and confronto_fgts['debug_log']:
                with st.expander("🐛 Ver Log Detalhado dos Lançamentos TXT (Debug)"):
                    st.markdown("### 📋 Detalhamento Completo dos Lançamentos FGTS")
                    st.info("Este log mostra TODOS os lançamentos do TXT que foram somados no cálculo do FGTS.")
                    for line in confronto_fgts['debug_log']:
                        st.text(line)
            
        # ========== CONFRONTO IRRF (TXT vs Resumo Geral) ==========
#         if 'confronto_irrf' in st.session_state and impostos_geral:
#             st.markdown("---")
#             st.header("📊 Confronto IRRF - Resumo Geral vs TXT")
#             st.info("📌 Comparação entre IRRF Total (Resumo Geral) e valores calculados do TXT baseado em códigos LA específicos")
            
#             confronto_irrf = st.session_state['confronto_irrf']
            
#             # Cards principais
#             col1, col2, col3 = st.columns(3)
            
#             with col1:
#                 st.markdown(f"""
#                 <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#                             padding: 20px; border-radius: 10px; text-align: center;
#                             box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
#                     <h4 style="color: white; margin: 0;">📊 IRRF Resumo Geral</h4>
#                     <p style="color: white; font-size: 0.85em; opacity: 0.9;">Total</p>
#                     <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
#                         {money(confronto_irrf['IRRF_Resumo_Geral'])}
#                     </p>
#                 </div>
#                 """, unsafe_allow_html=True)
            
#             with col2:
#                 st.markdown(f"""
#                 <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
#                             padding: 20px; border-radius: 10px; text-align: center;
#                             box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
#                     <h4 style="color: white; margin: 0;">📝 IRRF TXT</h4>
#                     <p style="color: white; font-size: 0.85em; opacity: 0.9;">Soma Total</p>
#                     <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
#                         {money(confronto_irrf['IRRF_TXT_Total'])}
#                     </p>
#                 </div>
#                 """, unsafe_allow_html=True)
            
#             with col3:
#                 diferenca_irrf = confronto_irrf['IRRF_Diferenca']
#                 # Verificar se está OK (diferença próxima de zero)
#                 status_irrf = '✅ OK' if abs(diferenca_irrf) < 0.01 else '⚠️ Divergência'
#                 cor_status_irrf = '#28a745' if status_irrf == '✅ OK' else '#dc3545'
                
#                 st.markdown(f"""
#                 <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
#                             padding: 20px; border-radius: 10px; text-align: center;
#                             box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
#                     <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
#                     <p style="color: white; font-size: 0.85em; opacity: 0.9;">Geral - TXT</p>
#                     <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
#                         {money(diferenca_irrf)}
#                     </p>
#                     <p style="background: {cor_status_irrf}; color: white; padding: 5px; border-radius: 5px; font-size: 0.9em; margin-top: 10px;">
#                         {status_irrf}
#                     </p>
#                 </div>
#                 """, unsafe_allow_html=True)
            
#             # Detalhes em expander
#             with st.expander("🔍 Ver Detalhes do Cálculo IRRF"):
#                 st.metric("➕ Total TXT", money(confronto_irrf['IRRF_TXT_Adicionais']))
#                 st.info("ℹ️ Todos os códigos LA de IRRF são Adicionais (não há descontos)")
                
#                 st.markdown("---")
#                 st.markdown("### 📐 Fórmula do Cálculo:")
#                 st.code(f"""
# IRRF Total (TXT) = Σ Adicionais
# IRRF Total (TXT) = {money(confronto_irrf['IRRF_TXT_Total'])}

# Diferença = Resumo Geral - TXT
# Diferença = {money(confronto_irrf['IRRF_Resumo_Geral'])} - {money(confronto_irrf['IRRF_TXT_Total'])}
# Diferença = {money(diferenca_irrf)}
#                 """, language="text")
            
#             # Debug log detalhado
#             if 'debug_log' in confronto_irrf and confronto_irrf['debug_log']:
#                 with st.expander("🐛 Ver Log Detalhado dos Lançamentos TXT (Debug)"):
#                     st.markdown("### 📋 Detalhamento Completo dos Lançamentos IRRF")
#                     st.info("Este log mostra TODOS os lançamentos do TXT que foram somados no cálculo do IRRF.")
#                     for line in confronto_irrf['debug_log']:
            

            st.header("📊 Confronto Pró-Labore e Autônomos")
            st.info("📌  Com base no Resumo Geral e nos Lançamentos Contábeis")
            
            # Verificar se temos os dados necessários
            if 'prolabore_txt' in st.session_state and impostos_geral:
                prolabore_txt = st.session_state['prolabore_txt']
                
                # Pró-Labore Sócios - 3 Cards
                st.markdown("### 💼 Pró-Labore Sócios")
                col1, col2, col3 = st.columns(3)
                
                resumo_liquido = impostos_geral['ProLabore_Socios_Liquido']
                txt_liquido = prolabore_txt['ProLabore_TXT_Total']
                diferenca = resumo_liquido - txt_liquido
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">👨‍💼 Resumo Geral</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Líquido</p>
                        <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(resumo_liquido)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">📝 Lanc. Contábeis</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Líquido</p>
                        <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(txt_liquido)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    # Definir cor baseada na diferença (verde se OK, vermelho se divergente)
                    cor_valor = '#28a745' if abs(diferenca) < 0.01 else '#dc3545'
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Resumo - TXT</p>
                        <p style="color: {cor_valor}; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(diferenca)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detalhes em expander
                with st.expander("🔍 Ver Detalhes do Cálculo Pró-Labore (TXT)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("➕ Adicionais TXT", money(prolabore_txt['ProLabore_TXT_Adicionais']))
                        st.caption("Códigos: 30003, 30064")
                    with col2:
                        st.metric("➖ Descontos TXT", money(prolabore_txt['ProLabore_TXT_Descontos']))
                        st.caption("Códigos: 30067, 30066")
                    
                    st.markdown("---")
                    st.markdown("### 📐 Fórmula do Cálculo:")
                    st.code(f"""
Pró-Labore TXT = Adicionais - Descontos
Pró-Labore TXT = {money(prolabore_txt['ProLabore_TXT_Adicionais'])} - {money(prolabore_txt['ProLabore_TXT_Descontos'])}
Pró-Labore TXT = {money(txt_liquido)}

Diferença = Resumo Geral - TXT
Diferença = {money(resumo_liquido)} - {money(txt_liquido)}
Diferença = {money(diferenca)}
                    """, language="text")
                
                st.markdown("")
                
                # Autônomos - 3 Cards
                st.markdown("### 👨‍💼 Autônomos")
                col1, col2, col3 = st.columns(3)
                
                resumo_autonomos = impostos_geral['ProLabore_Autonomos_Liquido']
                txt_autonomos = prolabore_txt['Autonomos_TXT_Total']
                diferenca_autonomos = resumo_autonomos - txt_autonomos
                
                with col1:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">📊 Resumo Geral</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Líquido</p>
                        <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(resumo_autonomos)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">� TXT</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Líquido</p>
                        <p style="color: white; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(txt_autonomos)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    # Definir cor baseada na diferença (verde se OK, vermelho se divergente)
                    cor_valor_aut = '#28a745' if abs(diferenca_autonomos) < 0.01 else '#dc3545'
                    
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                                padding: 20px; border-radius: 10px; text-align: center;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <h4 style="color: white; margin: 0;">⚖️ Diferença</h4>
                        <p style="color: white; font-size: 0.85em; opacity: 0.9;">Resumo - TXT</p>
                        <p style="color: {cor_valor_aut}; font-size: 1.8em; font-weight: bold; margin: 10px 0;">
                            {money(diferenca_autonomos)}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detalhes em expander
                with st.expander("🔍 Ver Detalhes do Cálculo Autônomos (TXT)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("➕ Adicionais TXT", money(prolabore_txt['Autonomos_TXT_Adicionais']))
                        st.caption("Códigos: 30060, 30069")
                    with col2:
                        st.metric("➖ Descontos TXT", money(prolabore_txt['Autonomos_TXT_Descontos']))
                        st.caption("Códigos: 30070, 30071")
                    
                    st.markdown("---")
                    st.markdown("### 📐 Fórmula do Cálculo:")
                    st.code(f"""
Autônomos TXT = Adicionais - Descontos
Autônomos TXT = {money(prolabore_txt['Autonomos_TXT_Adicionais'])} - {money(prolabore_txt['Autonomos_TXT_Descontos'])}
Autônomos TXT = {money(txt_autonomos)}

Diferença = Resumo Geral - TXT
Diferença = {money(resumo_autonomos)} - {money(txt_autonomos)}
Diferença = {money(diferenca_autonomos)}
                    """, language="text")
            
            # Detalhes do IRRF em expander
            # with st.expander("📊 Ver Detalhes do IRRF"):
            #     col1, col2 = st.columns(2)
            #     with col1:
            #         st.metric("IRRF Folha", money(impostos_geral.get("IRRF_Folha", 0)))
            #         st.metric("IRRF Férias", money(impostos_geral.get("IRRF_Ferias", 0)))
            #         st.metric("IRRF Rescisão", money(impostos_geral.get("IRRF_Rescisao", 0)))
            #     with col2:
            #         st.metric("IRRF Sócio", money(impostos_geral.get("IRRF_Socio", 0)))
            #         st.metric("IRRF Autônomo", money(impostos_geral.get("IRRF_Autonomo", 0)))


        # ========== DOWNLOAD EXCEL ==========
        st.markdown("---")
        st.header("💾 Download do Relatório")

        # Gerar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Resumo
            if not df_eventos_consolidado.empty:
                resumo_data = []
                for tipo, dfs in eventos_por_categoria.items():
                    total_eventos = sum([len(df) for df in dfs])
                    total_valor = sum([df['Total'].sum() for df in dfs])
                    resumo_data.append({
                        "Categoria": tipo,
                        "Total_Eventos": total_eventos,
                        "Total_Valor": total_valor
                    })

                df_resumo = pd.DataFrame(resumo_data)
                df_resumo.to_excel(writer, sheet_name="Resumo", index=False)

            # Eventos por categoria
            for tipo, dfs in eventos_por_categoria.items():
                df_cat = pd.concat(dfs, ignore_index=True)
                nome_aba = f"Eventos_{tipo.replace(' ', '_')[:25]}"
                df_cat.to_excel(writer, sheet_name=nome_aba, index=False)

            # Impostos
            if impostos_geral:
                df_imp = pd.DataFrame([impostos_geral]).T
                df_imp.columns = ["Valor"]
                df_imp.index.name = "Imposto"
                df_imp.to_excel(writer, sheet_name="Impostos_Geral")

            # Valores Líquidos por Categoria
            if 'df_eventos_mapeados_liquidos' in st.session_state:
                df_liquidos_excel = calcular_liquidos_por_categoria(st.session_state['df_eventos_mapeados_liquidos'])
                if not df_liquidos_excel.empty:
                    df_liquidos_excel.to_excel(writer, sheet_name="Valores_Liquidos", index=False)

            # Confronto (se existe)
            if 'df_confronto' in st.session_state:
                st.session_state['df_confronto'].to_excel(writer, sheet_name="Confronto_PDF_TXT", index=False)
                st.session_state['df_eventos_mapeados'].to_excel(writer, sheet_name="Eventos_Mapeados", index=False)

                # Eventos não mapeados
                nao_mapeados = st.session_state['df_eventos_mapeados'][
                    st.session_state['df_eventos_mapeados']['CodigoLA'].isna()
                ]
                if not nao_mapeados.empty:
                    nao_mapeados.to_excel(writer, sheet_name="Eventos_Nao_Mapeados", index=False)

            # ========== CONFRONTOS COM TXT ==========
            
            # Confronto INSS
            if 'confronto_inss' in st.session_state:
                confronto_inss = st.session_state['confronto_inss']
                df_confronto_inss = pd.DataFrame([{
                    'INSS Resumo Geral': confronto_inss['INSS_Resumo_Geral'],
                    'INSS TXT (Adicionais)': confronto_inss['INSS_TXT_Adicionais'],
                    'INSS TXT (Descontos)': confronto_inss['INSS_TXT_Descontos'],
                    'INSS TXT Total': confronto_inss['INSS_TXT_Total'],
                    'Diferença (Geral - TXT)': confronto_inss['INSS_Diferenca']
                }])
                df_confronto_inss.to_excel(writer, sheet_name="Confronto_INSS", index=False)
            
            # Confronto FGTS
            if 'confronto_fgts' in st.session_state:
                confronto_fgts = st.session_state['confronto_fgts']
                df_confronto_fgts = pd.DataFrame([{
                    'FGTS Resumo Geral': confronto_fgts['FGTS_Resumo_Geral'],
                    'FGTS TXT (Adicionais)': confronto_fgts['FGTS_TXT_Adicionais'],
                    'FGTS TXT (Descontos)': confronto_fgts['FGTS_TXT_Descontos'],
                    'FGTS TXT Total': confronto_fgts['FGTS_TXT_Total'],
                    'Diferença (Geral - TXT)': confronto_fgts['FGTS_Diferenca']
                }])
                df_confronto_fgts.to_excel(writer, sheet_name="Confronto_FGTS", index=False)
            
            # Empréstimos FGTS
            if 'emprestimos_fgts' in st.session_state:
                emprestimos = st.session_state['emprestimos_fgts']
                df_emprestimos = pd.DataFrame([{
                    'Empréstimos Adicionais': emprestimos['Emprestimos_Adicionais'],
                    'Empréstimos Descontos': emprestimos['Emprestimos_Descontos'],
                    'Empréstimos Total': emprestimos['Emprestimos_Total']
                }])
                df_emprestimos.to_excel(writer, sheet_name="Emprestimos_FGTS", index=False)
            
            # Confronto Pró-Labore e Autônomos
            if 'prolabore_txt' in st.session_state and impostos_geral:
                prolabore_txt = st.session_state['prolabore_txt']
                
                # Pró-Labore Sócios
                df_prolabore = pd.DataFrame([{
                    'Pró-Labore Resumo Geral': impostos_geral.get('ProLabore_Socios_Liquido', 0),
                    'Pró-Labore TXT (Adicionais)': prolabore_txt['ProLabore_TXT_Adicionais'],
                    'Pró-Labore TXT (Descontos)': prolabore_txt['ProLabore_TXT_Descontos'],
                    'Pró-Labore TXT Total': prolabore_txt['ProLabore_TXT_Total'],
                    'Diferença (Geral - TXT)': impostos_geral.get('ProLabore_Socios_Liquido', 0) - prolabore_txt['ProLabore_TXT_Total']
                }])
                df_prolabore.to_excel(writer, sheet_name="Confronto_ProLabore", index=False)
                
                # Autônomos
                df_autonomos = pd.DataFrame([{
                    'Autônomos Resumo Geral': impostos_geral.get('ProLabore_Autonomos_Liquido', 0),
                    'Autônomos TXT (Adicionais)': prolabore_txt['Autonomos_TXT_Adicionais'],
                    'Autônomos TXT (Descontos)': prolabore_txt['Autonomos_TXT_Descontos'],
                    'Autônomos TXT Total': prolabore_txt['Autonomos_TXT_Total'],
                    'Diferença (Geral - TXT)': impostos_geral.get('ProLabore_Autonomos_Liquido', 0) - prolabore_txt['Autonomos_TXT_Total']
                }])
                df_autonomos.to_excel(writer, sheet_name="Confronto_Autonomos", index=False)

        excel_data = output.getvalue()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"confronto_dp_{timestamp}.xlsx"

        st.download_button(
            label="📥 Baixar Relatório Excel",
            data=excel_data,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
