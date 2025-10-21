
# app.py — Confronto Folha x Lote Contábil (PDF x TXT)
# Python 3.12 + Streamlit

import io
import os
import re
import json
import csv
from collections import defaultdict
from typing import List, Tuple

import streamlit as st
import pandas as pd

# -------------- Dependência PDF --------------
try:
    import pdfplumber
except Exception:
    st.error("Falta a dependência 'pdfplumber'. Instale com: pip install pdfplumber")
    raise

# -------------- Utils --------------
def normalize_text(s: str | None) -> str:
    if s is None:
        return ""
    s = str(s)
    subs = {
        "ç": "c", "Ç": "C",
        "á": "a","à":"a","ä":"a","â":"a","ã":"a",
        "Á": "A","À":"A","Ä":"A","Â":"A","Ã":"A",
        "é": "e","ê":"e","É":"E","Ê":"E",
        "í":"i","î":"i","Í":"I","Î":"I",
        "ó":"o","ô":"o","ö":"o","õ":"o","Ó":"O","Ô":"O","Ö":"O","Õ":"O",
        "ú":"u","ü":"u","Ú":"U","Ü":"U",
    }
    for k, v in subs.items():
        s = s.replace(k, v)
    return s.lower().strip()

def canonical_categoria(raw: str) -> str:
    base = normalize_text(raw)
    if base in {"folha", "folha complementar", "folha comp", "folhacomplementar"} or ("folha" in base and "complementar" in base):
        return "Folha"
    if base in {"rescisao", "rescisao comp", "rescisao complementar", "rescisao compl", "rescisao comp."} or ("rescisao" in base and "complementar" in base):
        return "Rescisão"
    aliases = {
        "folha socios": "Folha Sócios",
        "folha autonomos": "Folha Autonomos",
        "13 primeira parcela": "13º Primeira Parcela",
        "13 segunda parcela": "13º Segunda Parcela",
        "13 adiantamento": "13º Adiantamento",
        "ferias": "Férias",
        "adiantamento": "Adiantamento",
        "pro labore": "Pró-Labore",
        "decimo terceiro": "13º",
        "13": "13º",
    }
    if base in aliases:
        return aliases[base]
    if "/" in (raw or ""):
        parts = [p.strip() for p in (raw or "").split("/") if p.strip()]
        if any("folha" in normalize_text(p) for p in parts):
            return "Folha"
        if any("rescisao" in normalize_text(p) for p in parts):
            return "Rescisão"
    return (raw or "").strip().title() or "Sem Categoria"

def parse_brl_decimal(s: str) -> float:
    s = (s or "").strip()
    s = s.replace(".", "").replace(",", ".")
    return float(s)

def money(n: float | int | None) -> str:
    if n is None:
        return "R$ 0,00"
    return f"R$ {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# -------------- Mapeamento --------------
def find_mapping_path() -> str | None:
    here = os.path.dirname(__file__)
    local_path = os.path.join(here, "mapeamento_dp.json")
    if os.path.exists(local_path):
        return local_path
    fallback = "/mnt/data/mapeamento_dp.json"
    if os.path.exists(fallback):
        return fallback
    return None

@st.cache_data(show_spinner=False)
def load_mapping() -> dict:
    path = find_mapping_path()
    if not path:
        st.error("Não encontrei 'mapeamento_dp.json'. Coloque-o na MESMA pasta do app.py (ou em /mnt/data).")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        st.error(f"Erro ao ler mapeamento JSON: {e}")
        return {}

    norm: dict[str, list[dict[str, str]]] = {}
    for cat, items in data.items():
        cat_canon = canonical_categoria(cat)
        norm_items = []
        for it in items or []:
            ev = re.sub(r"[^\d]", "", str(it.get("evento", "")))
            la = str(it.get("codigo_lancamento", "")).strip().replace(".0", "")
            if ev or la:
                norm_items.append({"evento": ev, "codigo_lancamento": la})
        norm[cat_canon] = norm_items
    return norm

def mapping_la_to_categoria(mapping: dict) -> dict:
    la2cat = {}
    for cat, items in (mapping or {}).items():
        for it in items or []:
            la = str(it.get("codigo_lancamento", "")).strip()
            if la:
                la2cat[la] = cat
    return la2cat

def mapping_event_to_la(mapping: dict) -> pd.DataFrame:
    rows: list[tuple[str, str, str]] = []
    for cat, items in (mapping or {}).items():
        for it in items or []:
            ev = re.sub(r"[^\d]", "", str(it.get("evento", "")))
            la = str(it.get("codigo_lancamento", ""))
            if ev and la:
                rows.append((cat, ev, la))
    return pd.DataFrame(rows, columns=["Categoria", "EventoCod", "CodigoLA"]).drop_duplicates()

# -------------- PDF (colunas por coordenadas) --------------
def _group_words_by_line(words, y_tol: float = 3.0):
    lines = []
    current = []
    last_y = None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        y = (w["top"] + w["bottom"]) / 2
        if last_y is None or abs(y - last_y) <= y_tol:
            current.append(w)
        else:
            lines.append(current)
            current = [w]
        last_y = y
    if current:
        lines.append(current)
    return lines

def _find_header_centers(line_words):
    name_map = {
        "codigo": {"codigo", "código"},
        "evento": {"evento"},
        "quantidade": {"quantidade"},
        "valor": {"valor"},
        "funcionarios": {"funcionarios", "funcionários"},
    }
    centers = {}
    for w in line_words:
        txt = normalize_text(w["text"])
        for key, variants in name_map.items():
            if txt in variants:
                centers[key] = (w["x0"] + w["x1"]) / 2.0
    if all(k in centers for k in name_map):
        return centers
    return None

def _assign_to_nearest_column(words, centers):
    if not centers:
        return {}
    col_texts = defaultdict(list)
    for w in words:
        cx = (w["x0"] + w["x1"]) / 2.0
        nearest = min(centers.items(), key=lambda kv: abs(cx - kv[1]))[0]
        col_texts[nearest].append(w)
    out = {}
    for col, ws in col_texts.items():
        ws_sorted = sorted(ws, key=lambda w: w["x0"])
        out[col] = " ".join([t["text"] for t in ws_sorted]).strip()
    return out

def parse_pdf_events(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Lê o PDF por colunas:
     - detecta CATEGORIA (título acima da tabela),
     - detecta SINAL (+/-) antes do código do evento,
     - aplica o sinal ao valor (+ = positivo, - = negativo),
     - encerra bloco ao chegar em Totais/Bases/Líquidos ou quando Código não tem dígitos.
    """
    rows: List[Tuple[str, str, str, str, float]] = []
    current_cat = "Sem Categoria"
    pending_cat = None
    centers = None
    in_block = False

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=True, keep_blank_chars=False)
            for line in _group_words_by_line(words):
                line_text = " ".join([w["text"] for w in sorted(line, key=lambda w: w["x0"])]).strip()
                norm_line = normalize_text(line_text)

                # Categoria
                if norm_line and len(norm_line) <= 80 and not any(ch.isdigit() for ch in norm_line.replace("/", "")):
                    if ("/" in line_text) or any(tok in norm_line for tok in [
                        "folha", "rescisao", "férias", "ferias", "adiantamento", "pro labore", "pró-labore", "decimo", "décimo"
                    ]):
                        pending_cat = canonical_categoria(line_text)
                        centers = None
                        in_block = False
                        continue

                # Cabeçalho
                found = _find_header_centers(line)
                if found:
                    centers = found
                    if pending_cat:
                        current_cat = pending_cat
                        pending_cat = None
                    in_block = True
                    continue

                if not (centers and in_block):
                    continue

                # Rodapés encerram bloco
                if any(k in norm_line for k in ["totais", "base inss", "base irrf", "base fgts", "líquidos", "liquidos"]):
                    centers = None
                    in_block = False
                    continue

                # Linha de dados (evento)
                cols = _assign_to_nearest_column(line, centers)
                codigo_col = (cols.get("codigo") or "").strip()
                evento_col = (cols.get("evento") or "").strip()
                valor_txt  = (cols.get("valor")  or "").strip()

                if not valor_txt:
                    continue

                # Detectar sinal (+/-) antes do código
                sinal = "+"
                codigo_col_clean = codigo_col
                if codigo_col.startswith("+") or codigo_col.startswith("-"):
                    sinal = codigo_col[0]
                    codigo_col_clean = codigo_col[1:].strip()

                # Extrair apenas os dígitos do código
                codigo_digits = re.sub(r"[^\d]", "", codigo_col_clean)
                if not codigo_digits:
                    centers = None
                    in_block = False
                    continue

                # Valor: último token com vírgula decimal
                candidates = [t for t in valor_txt.replace(".", "").split() if "," in t]
                valor_token = candidates[-1] if candidates else valor_txt
                try:
                    valor_num = parse_brl_decimal(valor_token)
                except Exception:
                    continue

                # Aplicar sinal ao valor
                if sinal == "-":
                    valor_num = -abs(valor_num)
                else:
                    valor_num = abs(valor_num)

                evento_clean = evento_col
                m2 = re.match(r"^[\+\-\s]*\d{1,6}\s+(.*)$", evento_clean)
                if m2:
                    evento_clean = m2.group(1).strip()

                rows.append((current_cat, codigo_digits, evento_clean, sinal, valor_num))

    df = pd.DataFrame(rows, columns=["Categoria", "EventoCod", "EventoNome", "Sinal", "Valor"])
    return df

def sum_pdf_by_categoria(df_pdf: pd.DataFrame) -> pd.DataFrame:
    """
    Soma valores do PDF por categoria.
    Os valores já vêm com sinais aplicados (+/-).
    """
    if df_pdf.empty:
        return pd.DataFrame(columns=["Categoria", "Adicionais", "Descontos", "Liquido"])

    df_pdf = df_pdf.copy()
    df_pdf["Categoria"] = df_pdf["Categoria"].apply(canonical_categoria)

    # Separar adicionais (+) e descontos (-)
    adicionais = df_pdf[df_pdf["Valor"] > 0].groupby("Categoria", as_index=False)["Valor"].sum().rename(columns={"Valor": "Adicionais"})
    descontos = df_pdf[df_pdf["Valor"] < 0].groupby("Categoria", as_index=False)["Valor"].sum().rename(columns={"Valor": "Descontos"})

    # Merge e calcular líquido
    result = adicionais.merge(descontos, on="Categoria", how="outer").fillna(0.0)
    result["Liquido"] = result["Adicionais"] + result["Descontos"]  # Descontos já são negativos

    return result

# -------------- TXT --------------
def detect_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","

def parse_txt_codes_values(txt_bytes: bytes) -> pd.DataFrame:
    """
    Lê o TXT/CSV e extrai:
     - Coluna 2: Código de lançamento (LA)
     - Coluna 4: Valor
     - Coluna 8: Descrição do evento/lançamento
    """
    text = txt_bytes.decode("utf-8", errors="ignore")
    first_line = text.splitlines()[0] if text.splitlines() else ","
    delim = detect_delimiter(first_line)
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = []
    for row in reader:
        if not row:
            continue
        # Coluna 2: Código LA (índice 1)
        cod = row[1].strip() if len(row) > 1 else ""
        # Coluna 4: Valor (índice 3)
        val = row[3].strip() if len(row) > 3 else ""
        # Coluna 8: Descrição (índice 7)
        desc = row[7].strip() if len(row) > 7 else ""

        cod = cod.replace(".0", "")
        val_clean = val.replace('"', "").replace(" ", "")
        try:
            valor = parse_brl_decimal(val_clean)
        except Exception:
            try:
                valor = float(val_clean.replace(",", ""))
            except Exception:
                continue
        rows.append((cod or None, abs(valor), desc))
    df = pd.DataFrame(rows, columns=["CodigoLA", "Valor", "Descricao"])
    return df

def classify_txt_by_description(descricao: str) -> str:
    """
    Classifica o código LA por categoria baseado na descrição (coluna 8 do TXT).
    Regras:
     - "inss", "fgts" ou "irrf" → Impostos
     - "folha de pagamento" ou "folha" → Folha
     - "férias" → Férias
     - "rescisao de contrato" → Rescisão
     - "adiantamento" → Adiantamento
    """
    desc_norm = normalize_text(descricao)

    # EXCEÇÃO: INSS, FGTS, IRRF sempre classificados como Impostos
    if any(palavra in desc_norm for palavra in ["fgts"]):
        return "Impostos"

    # Demais classificações
    if "rescisao de contrato" in desc_norm or "rescisao contrato" or "rescisao" in desc_norm:
        return "Rescisão"
    elif "ferias" in desc_norm:
        return "Férias"
    elif "adiantamento" in desc_norm:
        return "Adiantamento"
    elif "folha de pagamento" in desc_norm or "folha pagamento" in desc_norm:
        return "Folha"
    elif "folha" in desc_norm:
        return "Folha"
    else:
        return "Sem Mapeamento"

def sum_txt_by_categoria(df_txt: pd.DataFrame, mapping: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Soma valores do TXT por categoria.
    - Classifica por descrição (coluna 8)
    - Aplica sinais baseado no mapeamento (Adicional = +, Desconto = -)
    - Retorna DataFrame com Adicionais, Descontos e Líquido
    """
    if df_txt.empty:
        return pd.DataFrame(columns=["Categoria", "Adicionais", "Descontos", "Liquido"]), pd.DataFrame(columns=["CodigoLA", "Valor", "Descricao"])

    df_txt = df_txt.copy()

    # Classificar por descrição (coluna 8)
    df_txt["Categoria"] = df_txt["Descricao"].apply(classify_txt_by_description)

    # Criar dicionário de código LA → tipo (Adicional/Desconto) do mapeamento
    la_tipo = {}
    for cat, items in (mapping or {}).items():
        for it in items or []:
            la = str(it.get("codigo_lancamento", "")).strip()
            tipo = str(it.get("tipo", "")).strip()
            if la:
                la_tipo[la] = tipo

    # Aplicar sinais aos valores baseado no tipo
    def apply_sign(row):
        cod = str(row["CodigoLA"]).strip()
        valor = abs(row["Valor"])
        tipo = la_tipo.get(cod, "Adicional")  # Default: Adicional

        if normalize_text(tipo) in ["desconto", "descontos"]:
            return -valor
        else:
            return valor

    df_txt["ValorComSinal"] = df_txt.apply(apply_sign, axis=1)

    # Separar não mapeados
    not_mapped = df_txt[df_txt["Categoria"] == "Sem Mapeamento"][["CodigoLA", "Valor", "Descricao"]]

    # Filtrar apenas categorias mapeadas
    df_mapped = df_txt[df_txt["Categoria"] != "Sem Mapeamento"].copy()
    df_mapped["Categoria"] = df_mapped["Categoria"].apply(canonical_categoria)

    # Separar adicionais (+) e descontos (-)
    adicionais = df_mapped[df_mapped["ValorComSinal"] > 0].groupby("Categoria", as_index=False)["ValorComSinal"].sum().rename(columns={"ValorComSinal": "Adicionais"})
    descontos = df_mapped[df_mapped["ValorComSinal"] < 0].groupby("Categoria", as_index=False)["ValorComSinal"].sum().rename(columns={"ValorComSinal": "Descontos"})

    # Merge e calcular líquido
    result = adicionais.merge(descontos, on="Categoria", how="outer").fillna(0.0)
    result["Liquido"] = result["Adicionais"] + result["Descontos"]  # Descontos já são negativos

    return result, not_mapped

def sum_txt_by_event(df_txt: pd.DataFrame, ev_map: pd.DataFrame, la2cat: dict) -> pd.DataFrame:
    if df_txt.empty or ev_map.empty:
        return pd.DataFrame(columns=["Categoria", "EventoCod", "CodigoLA", "ValorTXT"])
    txt_la = df_txt.groupby("CodigoLA", as_index=False)["Valor"].sum().rename(columns={"Valor": "ValorTXT"})
    txt_la["Categoria"] = txt_la["CodigoLA"].map(lambda x: la2cat.get(str(x).strip(), "Sem Mapeamento"))
    ev_map = ev_map.copy()
    ev_map["EventoCod"] = ev_map["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)
    ev_map["CodigoLA"] = ev_map["CodigoLA"].astype(str).str.strip()
    txt_la["CodigoLA"] = txt_la["CodigoLA"].astype(str).str.strip()
    txt_la["Categoria"] = txt_la["Categoria"].apply(canonical_categoria)
    merged = ev_map.merge(txt_la, on=["CodigoLA", "Categoria"], how="left")
    merged = merged[["Categoria", "EventoCod", "CodigoLA", "ValorTXT"]]
    merged["ValorTXT"] = merged["ValorTXT"].fillna(0.0)
    return merged

# -------------- Comparações --------------
def compare_by_categoria(pdf_sum: pd.DataFrame, txt_sum: pd.DataFrame) -> pd.DataFrame:
    """
    Compara PDF x TXT por categoria.
    Versão simplificada: mostra apenas os Líquidos e se estão batendo.
    """
    # Merge dos dois DataFrames
    result = pdf_sum.merge(
        txt_sum,
        on="Categoria",
        how="outer",
        suffixes=("_PDF", "_TXT")
    ).fillna(0.0)

    # Selecionar apenas as colunas de Líquido
    result = pd.DataFrame({
        "Categoria": result["Categoria"],
        "Líquido PDF": result.get("Liquido_PDF", 0.0),
        "Líquido TXT": result.get("Liquido_TXT", 0.0),
    })

    # Calcular diferença
    result["Diferença"] = result["Líquido PDF"] - result["Líquido TXT"]

    # Adicionar indicador visual se está batendo
    result["Status"] = result["Diferença"].apply(
        lambda x: "✅ OK" if abs(x) < 0.01 else "⚠️ DIVERGENTE"
    )

    # Reordenar colunas
    result = result[["Categoria", "Líquido PDF", "Líquido TXT", "Diferença", "Status"]]

    return result.sort_values("Categoria").reset_index(drop=True)

def compare_by_event(df_pdf_events: pd.DataFrame, df_txt: pd.DataFrame, mapping: dict):
    if df_pdf_events.empty:
        return (
            pd.DataFrame(columns=["Categoria", "EventoCod", "EventoNome", "CodigoLA", "ValorPDF", "ValorTXT", "Diferença (PDF - TXT)"]),
            pd.DataFrame(columns=["Categoria", "EventoCod", "EventoNome"]),
            pd.DataFrame(columns=["Categoria", "CodigoLA", "ValorTXT"]),
        )

    names = (
        df_pdf_events.groupby(["Categoria", "EventoCod"])["EventoNome"]
        .agg(lambda s: next((x for x in s if x), ""))
        .reset_index()
    )
    pdf_ev = (
        df_pdf_events.groupby(["Categoria", "EventoCod"], as_index=False)["Valor"]
        .sum()
        .rename(columns={"Valor": "ValorPDF"})
    )
    pdf_ev = pdf_ev.merge(names, on=["Categoria", "EventoCod"], how="left")

    ev2la = mapping_event_to_la(mapping)
    pdf_m = pdf_ev.merge(ev2la, on=["Categoria", "EventoCod"], how="left")

    la2cat = mapping_la_to_categoria(mapping)
    txt_by_ev = sum_txt_by_event(df_txt, ev2la, la2cat)

    report = pdf_m.merge(txt_by_ev, on=["Categoria", "EventoCod", "CodigoLA"], how="left")
    report["ValorTXT"] = report["ValorTXT"].fillna(0.0)
    report["Diferença (PDF - TXT)"] = report["ValorPDF"] - report["ValorTXT"]
    report = report[
        ["Categoria", "EventoCod", "EventoNome", "CodigoLA", "ValorPDF", "ValorTXT", "Diferença (PDF - TXT)"]
    ].sort_values(["Categoria", "EventoCod"]).reset_index(drop=True)

    sem_map = report[report["CodigoLA"].isna()][["Categoria", "EventoCod", "EventoNome"]].drop_duplicates()

    txt_la = df_txt.groupby("CodigoLA", as_index=False)["Valor"].sum().rename(columns={"Valor": "ValorTXT"})
    txt_la["Categoria"] = txt_la["CodigoLA"].map(lambda x: la2cat.get(str(x).strip(), "Sem Mapeamento"))
    txt_la = txt_la[txt_la["Categoria"] != "Sem Mapeamento"]
    used_las = set(report["CodigoLA"].dropna().astype(str))
    extra_las = txt_la[~txt_la["CodigoLA"].astype(str).isin(used_las)]
    extra_las["Categoria"] = extra_las["Categoria"].apply(canonical_categoria)
    las_sem_evento_pdf = extra_las[["Categoria", "CodigoLA", "ValorTXT"]].sort_values(["Categoria", "CodigoLA"]).reset_index(drop=True)

    return report, sem_map, las_sem_evento_pdf

def compare_by_la(df_pdf_events: pd.DataFrame, df_txt: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    ev2la = mapping_event_to_la(mapping)
    la2cat = mapping_la_to_categoria(mapping)

    # PDF por LA
    if df_pdf_events.empty or ev2la.empty:
        pdf_la = pd.DataFrame(columns=["Categoria", "CodigoLA", "ValorPDF_LA"])
    else:
        pdf_m = df_pdf_events.copy()
        pdf_m["EventoCod"] = pdf_m["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)
        ev2la2 = ev2la.copy()
        ev2la2["EventoCod"] = ev2la2["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)
        joined = pdf_m.merge(ev2la2, on=["Categoria", "EventoCod"], how="left")
        joined = joined.dropna(subset=["CodigoLA"])
        if joined.empty:
            pdf_la = pd.DataFrame(columns=["Categoria", "CodigoLA", "ValorPDF_LA"])
        else:
            pdf_la = joined.groupby(["Categoria", "CodigoLA"], as_index=False)["Valor"].sum().rename(columns={"Valor": "ValorPDF_LA"})

    # TXT por LA
    if df_txt.empty:
        txt_la = pd.DataFrame(columns=["Categoria", "CodigoLA", "ValorTXT_LA"])
    else:
        txt_la = df_txt.groupby("CodigoLA", as_index=False)["Valor"].sum().rename(columns={"Valor": "ValorTXT_LA"})
        txt_la["Categoria"] = txt_la["CodigoLA"].map(lambda x: la2cat.get(str(x).strip(), "Sem Mapeamento"))

    # Canonicaliza cat
    if not pdf_la.empty:
        pdf_la["Categoria"] = pdf_la["Categoria"].apply(canonical_categoria)
    if not txt_la.empty:
        txt_la["Categoria"] = txt_la["Categoria"].apply(canonical_categoria)

    report_la = pd.merge(pdf_la, txt_la, on=["Categoria", "CodigoLA"], how="outer")
    report_la["ValorPDF_LA"] = report_la["ValorPDF_LA"].fillna(0.0)
    report_la["ValorTXT_LA"] = report_la["ValorTXT_LA"].fillna(0.0)
    report_la["Diferença (PDF - TXT)"] = report_la["ValorPDF_LA"] - report_la["ValorTXT_LA"]
    try:
        report_la["_la_num"] = report_la["CodigoLA"].astype(float)
    except Exception:
        report_la["_la_num"] = None
    report_la = report_la.sort_values(["Categoria", "_la_num", "CodigoLA"]).drop(columns=["_la_num"]).reset_index(drop=True)
    return report_la

def extract_taxes_report(df_pdf_events: pd.DataFrame, df_txt: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Extrai e classifica códigos LA específicos de impostos (INSS, IRRF e FGTS).

    Códigos INSS: 897, 30039, 30055, 30056, 30057, 30072, 30073, 40023, 60001, 70019, 80030
    Códigos IRRF: 30058, 40024, 40025, 50003, 60002, 80031
    Códigos FGTS: 30051, 30059, 50026, 70015

    Retorna DataFrame com: Tipo Imposto, Código LA, Eventos, Descrição, Valor PDF, Valor TXT, Diferença
    """
    # Definir códigos de impostos
    INSS_CODES = ["897", "30039", "30055", "30056", "30057", "30072", "30073", "40023", "60001", "70019", "80030"]
    IRRF_CODES = ["30058", "40024", "40025", "50003", "60002", "80031"]
    FGTS_CODES = ["30051", "30059", "50026", "70015"]
    TAX_CODES = INSS_CODES + IRRF_CODES + FGTS_CODES

    ev2la = mapping_event_to_la(mapping)

    if df_pdf_events.empty or ev2la.empty:
        return pd.DataFrame(columns=[
            "Tipo Imposto",
            "Código de Lançamento",
            "Eventos",
            "Descrição (TXT)",
            "Valor PDF",
            "Valor TXT",
            "Diferença"
        ])

    # Preparar PDF
    pdf_m = df_pdf_events.copy()
    pdf_m["EventoCod"] = pdf_m["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)

    ev2la_clean = ev2la.copy()
    ev2la_clean["EventoCod"] = ev2la_clean["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)

    # Join PDF events com mapeamento LA
    joined = pdf_m.merge(ev2la_clean, on=["Categoria", "EventoCod"], how="left")
    joined = joined.dropna(subset=["CodigoLA"])

    # Filtrar apenas códigos de impostos
    joined = joined[joined["CodigoLA"].isin(TAX_CODES)]

    if joined.empty:
        # Tentar pegar do TXT mesmo sem PDF
        if df_txt.empty:
            return pd.DataFrame(columns=[
                "Tipo Imposto",
                "Código de Lançamento",
                "Eventos",
                "Descrição (TXT)",
                "Valor PDF",
                "Valor TXT",
                "Diferença"
            ])

        txt_taxes = df_txt[df_txt["CodigoLA"].isin(TAX_CODES)].copy()
        if txt_taxes.empty:
            return pd.DataFrame(columns=[
                "Tipo Imposto",
                "Código de Lançamento",
                "Eventos",
                "Descrição (TXT)",
                "Valor PDF",
                "Valor TXT",
                "Diferença"
            ])

        txt_grouped = txt_taxes.groupby("CodigoLA").agg({
            "Descricao": "first",
            "Valor": "sum"
        }).reset_index()
        txt_grouped.columns = ["CodigoLA", "Descricao", "ValorTXT"]

        result = txt_grouped.copy()
        result["Eventos"] = ""
        result["ValorPDF"] = 0.0

    else:
        # Agrupar por LA: listar eventos e somar valores PDF
        pdf_grouped = joined.groupby("CodigoLA").agg({
            "EventoCod": lambda x: ", ".join(sorted(set(x.astype(str)))),
            "Valor": "sum"
        }).reset_index()
        pdf_grouped.columns = ["CodigoLA", "Eventos", "ValorPDF"]

        # Preparar TXT
        if df_txt.empty:
            txt_grouped = pd.DataFrame(columns=["CodigoLA", "Descricao", "ValorTXT"])
        else:
            txt_taxes = df_txt[df_txt["CodigoLA"].isin(TAX_CODES)].copy()
            if txt_taxes.empty:
                txt_grouped = pd.DataFrame(columns=["CodigoLA", "Descricao", "ValorTXT"])
            else:
                txt_grouped = txt_taxes.groupby("CodigoLA").agg({
                    "Descricao": "first",
                    "Valor": "sum"
                }).reset_index()
                txt_grouped.columns = ["CodigoLA", "Descricao", "ValorTXT"]

        # Merge PDF + TXT
        result = pdf_grouped.merge(txt_grouped, on="CodigoLA", how="outer")
        result["Eventos"] = result["Eventos"].fillna("")
        result["Descricao"] = result["Descricao"].fillna("Sem descrição")
        result["ValorPDF"] = result["ValorPDF"].fillna(0.0)
        result["ValorTXT"] = result["ValorTXT"].fillna(0.0)

    # Aplicar absoluto
    result["ValorPDF"] = result["ValorPDF"].abs()
    result["ValorTXT"] = result["ValorTXT"].abs()
    result["Diferenca"] = result["ValorPDF"] - result["ValorTXT"]

    # Classificar tipo de imposto
    def classify_tax(cod):
        if cod in INSS_CODES:
            return "INSS"
        elif cod in IRRF_CODES:
            return "IRRF"
        elif cod in FGTS_CODES:
            return "FGTS"
        return "Outros"

    result["TipoImposto"] = result["CodigoLA"].apply(classify_tax)

    # Renomear colunas
    result = result.rename(columns={
        "TipoImposto": "Tipo Imposto",
        "CodigoLA": "Código de Lançamento",
        "Descricao": "Descrição (TXT)",
        "ValorPDF": "Valor PDF",
        "ValorTXT": "Valor TXT",
        "Diferenca": "Diferença"
    })

    # Ordenar por tipo e código
    result = result.sort_values(["Tipo Imposto", "Código de Lançamento"])

    result = result[[
        "Tipo Imposto",
        "Código de Lançamento",
        "Eventos",
        "Descrição (TXT)",
        "Valor PDF",
        "Valor TXT",
        "Diferença"
    ]].reset_index(drop=True)

    return result

def composition_report_by_la(df_pdf_events: pd.DataFrame, df_txt: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Gera relatório de composição por Código de Lançamento (LA).
    EXCLUI apenas códigos específicos de FGTS (30051, 30059, 50026, 70015) e INSS (30072, 30073).
    Mantém todos os outros códigos, incluindo IRRF e demais códigos de INSS.

    Formato:
    - Código de Lançamento
    - Eventos (lista de eventos que compõem o LA presentes na folha)
    - Descrição do código (TXT)
    - Valor PDF
    - Valor TXT
    - Diferença
    """
    # Códigos a serem EXCLUÍDOS da tabela de composição
    EXCLUDED_CODES = ["30051", "30059", "50026", "70015", "30072", "30073"]

    ev2la = mapping_event_to_la(mapping)

    if df_pdf_events.empty or ev2la.empty:
        return pd.DataFrame(columns=[
            "Código de Lançamento",
            "Eventos",
            "Descrição (TXT)",
            "Valor PDF",
            "Valor TXT",
            "Diferença"
        ])

    # Preparar PDF: juntar eventos com seus LAs
    pdf_m = df_pdf_events.copy()
    pdf_m["EventoCod"] = pdf_m["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)

    ev2la_clean = ev2la.copy()
    ev2la_clean["EventoCod"] = ev2la_clean["EventoCod"].astype(str).str.replace(r"[^\d]", "", regex=True)

    # Join PDF events com mapeamento LA
    joined = pdf_m.merge(ev2la_clean, on=["Categoria", "EventoCod"], how="left")
    joined = joined.dropna(subset=["CodigoLA"])

    if joined.empty:
        return pd.DataFrame(columns=[
            "Código de Lançamento",
            "Eventos",
            "Descrição (TXT)",
            "Valor PDF",
            "Valor TXT",
            "Diferença"
        ])

    # Agrupar por LA: listar eventos e somar valores PDF
    pdf_grouped = joined.groupby("CodigoLA").agg({
        "EventoCod": lambda x: ", ".join(sorted(set(x.astype(str)))),
        "Valor": "sum"
    }).reset_index()
    pdf_grouped.columns = ["CodigoLA", "Eventos", "ValorPDF"]

    # Preparar TXT: agrupar por LA e pegar descrição
    if df_txt.empty:
        txt_grouped = pd.DataFrame(columns=["CodigoLA", "Descricao", "ValorTXT"])
    else:
        txt_grouped = df_txt.groupby("CodigoLA").agg({
            "Descricao": "first",  # Pegar primeira descrição do grupo
            "Valor": "sum"
        }).reset_index()
        txt_grouped.columns = ["CodigoLA", "Descricao", "ValorTXT"]

    # Merge PDF + TXT
    result = pdf_grouped.merge(txt_grouped, on="CodigoLA", how="outer")
    result["Eventos"] = result["Eventos"].fillna("")
    result["Descricao"] = result["Descricao"].fillna("Sem descrição")
    result["ValorPDF"] = result["ValorPDF"].fillna(0.0)
    result["ValorTXT"] = result["ValorTXT"].fillna(0.0)

    # EXCLUIR apenas os códigos específicos de FGTS e INSS
    result = result[~result["CodigoLA"].isin(EXCLUDED_CODES)]

    # Aplicar absoluto antes de calcular diferença
    result["ValorPDF"] = result["ValorPDF"].abs()
    result["ValorTXT"] = result["ValorTXT"].abs()
    result["Diferenca"] = result["ValorPDF"] - result["ValorTXT"]

    # Renomear colunas para formato final
    result = result.rename(columns={
        "CodigoLA": "Código de Lançamento",
        "Descricao": "Descrição (TXT)",
        "ValorPDF": "Valor PDF",
        "ValorTXT": "Valor TXT",
        "Diferenca": "Diferença"
    })

    # Ordenar por código LA
    try:
        result["_la_num"] = result["Código de Lançamento"].astype(float)
        result = result.sort_values("_la_num").drop(columns=["_la_num"])
    except Exception:
        result = result.sort_values("Código de Lançamento")

    result = result[[
        "Código de Lançamento",
        "Eventos",
        "Descrição (TXT)",
        "Valor PDF",
        "Valor TXT",
        "Diferença"
    ]].reset_index(drop=True)

    return result

# -------------- UI --------------
st.set_page_config(page_title="Confronto Folha x Lote Contábil", layout="wide", page_icon="📊")

# Session state
if "report_cat_df" not in st.session_state:
    st.session_state.report_cat_df = None
if "report_composition_df" not in st.session_state:
    st.session_state.report_composition_df = None
if "report_taxes_df" not in st.session_state:
    st.session_state.report_taxes_df = None

# Título principal
st.title("📊 Confronto Folha x Lote Contábil")
st.markdown("---")

# Carrega mapeamento
mapping = load_mapping()
if not mapping:
    st.stop()

# Área de upload na página principal
st.header("📁 Arquivos de Entrada")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**PDF da Folha de Pagamento**")
    pdf_file = st.file_uploader("Selecione o arquivo PDF", type=["pdf"], accept_multiple_files=False, label_visibility="collapsed")

with col2:
    st.markdown("**TXT/CSV do Lote Contábil**")
    txt_file = st.file_uploader("Selecione o arquivo TXT/CSV", type=["txt", "csv"], accept_multiple_files=False, label_visibility="collapsed")

# Botão para usar exemplos
use_examples = st.button("🔍 Usar arquivos de exemplo", help="Carrega arquivos de exemplo do sistema (se disponíveis)")

st.markdown("---")
# Entrada de arquivos
pdf_bytes = pdf_file.getvalue() if pdf_file is not None else None
txt_bytes = txt_file.getvalue() if txt_file is not None else None

if use_examples:
    try:
        with open("/mnt/data/Resumo Folha.pdf", "rb") as f:
            pdf_bytes = f.read()
        with open("/mnt/data/Lote Contábil.txt", "rb") as f:
            txt_bytes = f.read()
        st.success("Arquivos de exemplo carregados!")
    except Exception as e:
        st.error(f"Não encontrei os arquivos de exemplo: {e}")

if pdf_bytes and txt_bytes:
    # Processar arquivos
    df_pdf_events = parse_pdf_events(pdf_bytes)
    df_txt = parse_txt_codes_values(txt_bytes)

    if df_pdf_events.empty:
        st.error("❌ Não foi possível extrair eventos do PDF. Verifique o layout do arquivo.")
        st.stop()

    if df_txt.empty:
        st.error("❌ Não foi possível extrair dados do TXT. Verifique o formato do arquivo.")
        st.stop()

    # Calcular agregações
    pdf_sum = sum_pdf_by_categoria(df_pdf_events)
    txt_sum, not_mapped = sum_txt_by_categoria(df_txt, mapping)

    # ========== EXPANDER 1: Leitura do PDF ==========
    with st.expander("📄 Detalhes da Leitura do PDF", expanded=False):
        st.markdown("#### Eventos Extraídos do PDF")
        st.caption("Primeiros 100 registros com sinais aplicados (+/-)")

        df_display = df_pdf_events.head(100).copy()
        df_display["Valor_fmt"] = df_display["Valor"].apply(money)
        st.dataframe(
            df_display[["Categoria", "EventoCod", "EventoNome", "Sinal", "Valor_fmt"]],
            use_container_width=True,
            height=300
        )

    # ========== EXPANDER 2: Leitura do TXT ==========
    with st.expander("📋 Detalhes da Leitura do TXT/CSV", expanded=False):
        st.markdown("#### Códigos de Lançamento Extraídos")
        st.caption("Primeiros 100 registros (Coluna 2=LA, Coluna 4=Valor, Coluna 8=Descrição)")

        df_txt_display = df_txt.head(100).copy()
        df_txt_display["Valor_fmt"] = df_txt_display["Valor"].apply(money)
        st.dataframe(
            df_txt_display[["CodigoLA", "Valor_fmt", "Descricao"]],
            use_container_width=True,
            height=300
        )

        if not not_mapped.empty:
            st.warning(f"⚠️ **{len(not_mapped)} códigos sem classificação automática**")
            st.caption("Estes códigos não puderam ser classificados pela descrição:")
            not_mapped_display = not_mapped.copy()
            not_mapped_display["Valor_fmt"] = not_mapped_display["Valor"].apply(money)
            st.dataframe(not_mapped_display, use_container_width=True, height=200)

    # ========== RESUMO POR CATEGORIA DO PDF ==========
    st.markdown("---")
    st.header("📊 Resumo por Categoria (PDF)")
    st.caption("Valores extraídos e consolidados do PDF da folha de pagamento")

    pdf_sum_display = pdf_sum.copy()
    pdf_sum_display["Adicionais"] = pdf_sum_display["Adicionais"].apply(money)
    pdf_sum_display["Descontos"] = pdf_sum_display["Descontos"].apply(money)
    pdf_sum_display["Líquido"] = pdf_sum_display["Liquido"].apply(money)
    st.dataframe(
        pdf_sum_display[["Categoria", "Adicionais", "Descontos", "Líquido"]],
        use_container_width=True,
        height=300
    )

    # Manter report_cat no session_state para compatibilidade com downloads (se necessário no futuro)
    if not pdf_sum.empty or not txt_sum.empty:
        report_cat = compare_by_categoria(pdf_sum, txt_sum)
        st.session_state.report_cat_df = report_cat

    # ========== RELATÓRIO 4: Composição por LA ==========
    st.markdown("---")
    st.header("🔍 Composição por Código de Lançamento (LA)")
    st.caption("Detalhamento de quais eventos compõem cada código LA presente na folha")

    report_composition = composition_report_by_la(df_pdf_events, df_txt, mapping)
    st.session_state.report_composition_df = report_composition

    if not report_composition.empty:
        # Formatar valores monetários
        report_comp_display = report_composition.copy()
        report_comp_display["Valor PDF"] = report_comp_display["Valor PDF"].apply(money)
        report_comp_display["Valor TXT"] = report_comp_display["Valor TXT"].apply(money)
        report_comp_display["Diferença"] = report_comp_display["Diferença"].apply(money)

        # Adicionar status visual
        report_comp_display["Status"] = report_composition["Diferença"].apply(
            lambda x: "✅ OK" if abs(x) < 0.01 else "⚠️ DIVERGENTE"
        )

        st.dataframe(
            report_comp_display[[
                "Código de Lançamento",
                "Eventos",
                "Descrição (TXT)",
                "Valor PDF",
                "Valor TXT",
                "Diferença",
                "Status"
            ]],
            use_container_width=True,
            height=400
        )

        # Resumo com métricas
        total_las = len(report_composition)
        total_divergencias_la = (report_composition["Diferença"].abs() > 0.01).sum()
        total_ok_la = total_las - total_divergencias_la

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de LAs", total_las)
        with col2:
            st.metric("Batendo", total_ok_la)
        with col3:
            st.metric("Divergentes", total_divergencias_la)

        st.download_button(
            label="📥 Baixar Relatório de Composição CSV",
            data=report_composition.to_csv(index=False).encode("utf-8"),
            file_name="relatorio_composicao_por_la.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("ℹ️ Nenhum dado disponível para o relatório de composição.")

    # ========== RELATÓRIO 5: Impostos ==========
    st.markdown("---")
    st.header("💰 Relatório de Impostos (INSS, IRRF e FGTS)")
    st.caption("Detalhamento de códigos LA específicos de impostos classificados por tipo")

    report_taxes = extract_taxes_report(df_pdf_events, df_txt, mapping)
    st.session_state.report_taxes_df = report_taxes

    if not report_taxes.empty:
        # Formatar valores monetários
        report_taxes_display = report_taxes.copy()
        report_taxes_display["Valor PDF"] = report_taxes_display["Valor PDF"].apply(money)
        report_taxes_display["Valor TXT"] = report_taxes_display["Valor TXT"].apply(money)
        report_taxes_display["Diferença"] = report_taxes_display["Diferença"].apply(money)

        # Adicionar status visual
        report_taxes_display["Status"] = report_taxes["Diferença"].apply(
            lambda x: "✅ OK" if abs(x) < 0.01 else "⚠️ DIVERGENTE"
        )

        st.dataframe(
            report_taxes_display[[
                "Tipo Imposto",
                "Código de Lançamento",
                "Eventos",
                "Descrição (TXT)",
                "Valor PDF",
                "Valor TXT",
                "Diferença",
                "Status"
            ]],
            use_container_width=True,
            height=400
        )

        # Resumo por tipo de imposto com métricas
        inss_total = report_taxes[report_taxes["Tipo Imposto"] == "INSS"]["Diferença"].abs().sum()
        irrf_total = report_taxes[report_taxes["Tipo Imposto"] == "IRRF"]["Diferença"].abs().sum()
        fgts_total = report_taxes[report_taxes["Tipo Imposto"] == "FGTS"]["Diferença"].abs().sum()

        st.markdown("#### Divergências por Tipo de Imposto")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("INSS", money(inss_total), delta="OK" if inss_total < 0.01 else None)
        with col2:
            st.metric("IRRF", money(irrf_total), delta="OK" if irrf_total < 0.01 else None)
        with col3:
            st.metric("FGTS", money(fgts_total), delta="OK" if fgts_total < 0.01 else None)

        st.download_button(
            label="📥 Baixar Relatório de Impostos CSV",
            data=report_taxes.to_csv(index=False).encode("utf-8"),
            file_name="relatorio_impostos.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("ℹ️ Nenhum código de imposto encontrado nos dados processados.")

    # ========== EXPANDER: Mapeamento JSON ==========
    with st.expander("⚙️ Ver Mapeamento JSON Carregado", expanded=False):
        st.caption("Estrutura de mapeamento: Categoria → [evento, código_lançamento, tipo]")
        st.json(mapping)

else:
    # Mensagem quando não há arquivos
    st.info("👆 **Envie os arquivos PDF e TXT/CSV acima para iniciar a análise**")
    st.markdown("""
    ### Como usar:
    1. Faça upload do **PDF da Folha de Pagamento**
    2. Faça upload do **TXT/CSV do Lote Contábil**
    3. A análise será gerada automaticamente

    Ou clique em **"Usar arquivos de exemplo"** se disponível no sistema.
    """)
