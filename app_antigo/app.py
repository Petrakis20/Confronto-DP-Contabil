#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
app.py (todos os eventos do PDF na comparação por LA+Evento)

• Compara por PAR (LA, Evento) para evitar somatórios indevidos.
• Lista TODOS os eventos que estão no PDF — mesmo que sem movimento no TXT (Lote=0) ou com diferença.
• Checkbox opcional para mostrar apenas as linhas que batem.

Colunas:
- LA
- Evento
- Resumo da Folha (total por Evento no PDF — repetido nos LAs mapeados para o evento)
- Lote Contábil (somado do TXT apenas daquele LA)
- Conta Devedora
- Conta Credora
- Diferença = Resumo da Folha − Lote Contábil
"""
from pathlib import Path
import io
import re
import json
import csv

import streamlit as st
import pdfplumber
import pandas as pd

# ----------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------
def parse_brazilian_number(s: str) -> float | None:
    if not isinstance(s, str):
        return None
    s = s.replace(":", ".")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

# ----------------------------------------------------------------------
# Extração
# ----------------------------------------------------------------------
@st.cache_data
def extract_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    # Ex.: "+ 101 ... 1.234,56  12"  -> Evento=101, valor=1.234,56
    regex = re.compile(r'^[\+\-]?\s*(\d{3})\s+.*?\s+([\d\.,:]+)\s+\d+$')
    records: list[dict] = []
    with io.BytesIO(pdf_bytes) as buff, pdfplumber.open(buff) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").split("\n"):
                m = regex.match(line)
                if m:
                    valor = parse_brazilian_number(m.group(2))
                    if valor is not None:
                        records.append({"Evento": m.group(1), "valor_pdf": valor})
    return pd.DataFrame(records)

@st.cache_data
def extract_from_txt(txt_bytes: bytes) -> pd.DataFrame:
    """
    Lê TXT como CSV (vírgula, aspas):
      - col 2 -> la
      - col 4 -> valor_txt
      - col 5 -> conta_devedora
      - col 6 -> conta_credora
    """
    text = txt_bytes.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text), delimiter=",", quotechar='"')
    recs: list[dict] = []
    for row in reader:
        if len(row) < 6:
            continue
        la = (row[1] or "").strip()
        valor_raw = (row[3] or "").strip()
        conta_dev = (row[4] or "").strip()
        conta_cre = (row[5] or "").strip()
        valor = parse_brazilian_number(valor_raw)
        if valor is None:
            continue
        recs.append(
            {
                "la": la,
                "valor_txt": valor,
                "conta_devedora": conta_dev,
                "conta_credora": conta_cre,
            }
        )
    return pd.DataFrame(recs)

@st.cache_data
def load_mapping_dict() -> dict[str, list[str]]:
    path = Path(__file__).parent / "mapping_eventos.json"
    if not path.exists():
        st.error(f"Map file not found: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Conciliação e Mapeamento (LA+Evento)", layout="wide")
    st.title("🔗 Conciliação PDF vs TXT por LA + Evento")

    pdf_file = st.file_uploader("📄 Envie o PDF Resumo Folha", type="pdf")
    txt_file = st.file_uploader("📑 Envie o TXT Lote Contábil", type="txt")

    # Preferências
    st.sidebar.header("Exibição")
    show_only_matches = st.sidebar.checkbox(
        "Mostrar apenas linhas que batem (≈ 2 casas decimais)", value=False
    )
    tol = 0.01

    if not pdf_file or not txt_file:
        st.info("Envie ambos PDF e TXT para iniciar a conciliação")
        return

    pdf_bytes = pdf_file.read()
    txt_bytes = txt_file.read()

    try:
        df_pdf = extract_from_pdf(pdf_bytes)
        df_txt = extract_from_txt(txt_bytes)
    except Exception as e:
        st.error(f"Erro na extração: {e}")
        return

    st.header("📄 Extração do PDF (por Evento)")
    st.dataframe(df_pdf, hide_index=True, use_container_width=True)
    st.header("📑 Extração do TXT (por LA)")
    st.dataframe(df_txt, hide_index=True, use_container_width=True)

    # PDF consolidado por Evento
    df_pdf_sum = (
        df_pdf.groupby("Evento", as_index=False)["valor_pdf"]
        .sum()
        .rename(columns={"valor_pdf": "Resumo da Folha"})
    )

    # Mapeamento: gera todos os pares (la, Evento) que existem no PDF
    mapping = load_mapping_dict()
    eventos_pdf = set(df_pdf_sum["Evento"])
    rows: list[dict] = []
    for la, eventos in mapping.items():
        for ev in eventos:
            if ev in eventos_pdf:
                rows.append({"la": la, "Evento": ev})
    df_map = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["la", "Evento"])

    # Relaciona mapping com TXT por 'la' — LEFT para manter pares sem movimento
    df_txt_mapped = df_map.merge(df_txt, on="la", how="left")

    # Agrega por (la, Evento); onde não houver movimento, o 'valor_txt' fica NaN e a soma vira 0
    if not df_txt_mapped.empty:
        df_txt_sum = (
            df_txt_mapped.groupby(["la", "Evento"], as_index=False).agg(
                **{
                    "Lote Contábil": ("valor_txt", "sum"),
                    "Conta Devedora": (
                        "conta_devedora",
                        lambda x: ", ".join(
                            sorted(set(map(str, [v for v in x if pd.notna(v)])))
                        ),
                    ),
                    "Conta Credora": (
                        "conta_credora",
                        lambda x: ", ".join(
                            sorted(set(map(str, [v for v in x if pd.notna(v)])))
                        ),
                    ),
                }
            )
        )
    else:
        df_txt_sum = pd.DataFrame(
            columns=["la", "Evento", "Lote Contábil", "Conta Devedora", "Conta Credora"]
        )

    # Merge final: TODOS os eventos do PDF (via df_map) + valores do TXT (se houver)
    df_final = (
        df_map.merge(df_pdf_sum, on="Evento", how="left")
        .merge(df_txt_sum, on=["la", "Evento"], how="left")
        .fillna({"Lote Contábil": 0, "Conta Devedora": "", "Conta Credora": ""})
    )

    # Diferença e filtro opcional
    df_final["Diferença"] = df_final["Resumo da Folha"] - df_final["Lote Contábil"]
    if show_only_matches:
        df_final = df_final[df_final["Diferença"].abs() <= tol]

    # Ordena e exibe
    df_final = df_final.sort_values(by=["Evento", "la"])
    report = df_final[
        [
            "la",
            "Evento",
            "Resumo da Folha",
            "Lote Contábil",
            "Conta Devedora",
            "Conta Credora",
            "Diferença",
        ]
    ]
    styled = report.style.format(precision=2, thousands=".", decimal=",")
    st.header("📋 Relatório de Conciliação (LA + Evento)")
    st.dataframe(styled, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
