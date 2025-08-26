#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
app.py (corrigido sem regex)

Conciliação de eventos entre PDF e TXT via mapping_eventos.json:
Cada código LA (TXT) corresponde a um ou mais códigos de evento (PDF).

Somente os eventos presentes no PDF são considerados.

Exibe relatório com colunas:
- Evento
- Resumo da Folha
- Lote Contábil
- Conta Devedora
- Conta Credora
- Diferença

Além disso, mostra extração detalhada de cada fonte (PDF e TXT).

Os valores numéricos no relatório final são formatados usando ponto "." como separador de milhar e vírgula "," como decimal.

Python 3.12 + Streamlit interface.
"""
from pathlib import Path
import io
import re
import json
import csv

import streamlit as st
import pdfplumber
import pandas as pd

#------------------------------------------------------------------------------
# Utilitários
#------------------------------------------------------------------------------

def parse_brazilian_number(s: str) -> float | None:
    """
    Converte formatos brasileiros para float:
    - Troca ':' por '.' (alguns PDFs vêm com esse caractere)
    - Remove pontos de milhar e troca vírgula por ponto decimal
    Retorna None se falhar.
    """
    if not isinstance(s, str):
        return None
    s = s.replace(':', '.')
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

#------------------------------------------------------------------------------
# Extração de dados
#------------------------------------------------------------------------------

@st.cache_data
def extract_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    # Ex.: "+ 101 ... 1.234,56  12"  -> captura codigo=101, valor=1.234,56
    regex = re.compile(r'^[\+\-]?\s*(\d{3})\s+.*?\s+([\d\.,:]+)\s+\d+$')
    records: list[dict] = []
    with io.BytesIO(pdf_bytes) as buff, pdfplumber.open(buff) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or '').split('\n'):
                m = regex.match(line)
                if m:
                    valor = parse_brazilian_number(m.group(2))
                    if valor is not None:
                        records.append({'codigo': m.group(1), 'valor_pdf': valor})
    return pd.DataFrame(records)

@st.cache_data
def extract_from_txt(txt_bytes: bytes) -> pd.DataFrame:
    """Lê o TXT como CSV delimitado por vírgula respeitando aspas.
    Captura:
      - coluna 2  -> LA
      - coluna 4  -> valor_txt
      - coluna 5  -> conta_devedora
      - coluna 6  -> conta_credora
    """
    text = txt_bytes.decode('utf-8', errors='ignore')
    reader = csv.reader(io.StringIO(text), delimiter=',', quotechar='"')
    records: list[dict] = []
    for row in reader:
        # Garantir pelo menos 6 colunas
        if len(row) < 6:
            continue
        la = (row[1] or '').strip()
        valor_raw = (row[3] or '').strip()
        conta_dev = (row[4] or '').strip()
        conta_cre = (row[5] or '').strip()
        valor = parse_brazilian_number(valor_raw)
        if valor is None:
            continue
        records.append({
            'la': la,
            'valor_txt': valor,
            'conta_devedora': conta_dev,
            'conta_credora': conta_cre,
        })
    return pd.DataFrame(records)

@st.cache_data
def load_mapping_dict() -> dict[str, list[str]]:
    path = Path(__file__).parent / 'mapping_eventos.json'
    if not path.exists():
        st.error(f'Map file not found: {path}')
        return {}
    return json.loads(path.read_text(encoding='utf-8'))

#------------------------------------------------------------------------------
# App Streamlit
#------------------------------------------------------------------------------

def main():
    st.set_page_config(page_title='Conciliação e Mapeamento', layout='wide')
    st.title('🔗 Conciliação PDF vs TXT com Mapping e Formatação')

    # uploads
    pdf_file = st.file_uploader('📄 Envie o PDF Resumo Folha', type='pdf')
    txt_file = st.file_uploader('📑 Envie o TXT Lote Contábil', type='txt')

    if not pdf_file or not txt_file:
        st.info('Envie ambos PDF e TXT para iniciar a conciliação')
        return

    pdf_bytes = pdf_file.read()
    txt_bytes = txt_file.read()

    try:
        df_pdf = extract_from_pdf(pdf_bytes)
        df_txt = extract_from_txt(txt_bytes)
    except Exception as e:
        st.error(f'Erro na extração: {e}')
        return

    # Exibe extração individual
    st.header('📄 Extração de dados do PDF')
    st.dataframe(df_pdf, hide_index=True)
    st.header('📑 Extração de dados do TXT')
    st.dataframe(df_txt, hide_index=True)

    # Agrega resumo da folha por evento
    df_pdf_sum = (
        df_pdf.groupby('codigo', as_index=False)['valor_pdf']
              .sum()
              .rename(columns={'valor_pdf': 'Resumo da Folha'})
    )

    # Carrega e filtra mapping: mantém apenas eventos que existem no PDF
    mapping = load_mapping_dict()
    pdf_codes = set(df_pdf_sum['codigo'])
    rows: list[dict] = []
    for la, eventos in mapping.items():
        for evento in eventos:
            if evento in pdf_codes:
                rows.append({'codigo': evento, 'la': la})
    df_map = pd.DataFrame(rows)

    # Relaciona TXT ↔ eventos PDF (apenas pelo mapping)
    df_txt_mapped = df_map.merge(df_txt, on='la', how='inner')

    # Lote Contábil = soma estrita da COLUNA 4 (valor_txt) por 'codigo' mapeado
    df_txt_sum = (
        df_txt_mapped.groupby('codigo', as_index=False)
                     .agg(
                         **{
                             'Lote Contábil': ('valor_txt', 'sum'),
                             'Conta Devedora': ('conta_devedora', lambda x: ', '.join(sorted(set(map(str, x))))),
                             'Conta Credora': ('conta_credora', lambda x: ', '.join(sorted(set(map(str, x)))))
                         }
                     )
    )

    # Merge final e diferença (usa APENAS o valor_txt consolidado)
    df_final = (
        pd.merge(df_pdf_sum, df_txt_sum, on='codigo', how='left')
          .fillna({'Lote Contábil': 0, 'Conta Devedora': '', 'Conta Credora': ''})
          .rename(columns={'codigo': 'Evento'})
    )

    df_final['Diferença'] = df_final['Resumo da Folha'] - df_final['Lote Contábil']

    # Ordena por divergência absoluta desc para facilitar auditoria
    df_final = df_final.sort_values(by=df_final['Diferença'].abs().name, ascending=False)

    # Formatação de números: milhar '.' e decimal ','
    report = df_final[['Evento', 'Resumo da Folha', 'Lote Contábil', 'Conta Devedora', 'Conta Credora', 'Diferença']]
    styled = report.style.format(precision=2, thousands='.', decimal=',')

    # Exibe relatório consolidado
    st.header('📋 Relatório de Conciliação')
    st.dataframe(styled, hide_index=True, use_container_width=True)

if __name__ == '__main__':
    main()
