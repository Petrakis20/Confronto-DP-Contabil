# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Confronto DP-Contábil** is a Streamlit-based application that compares payroll data from PDF reports against accounting batch data from TXT/CSV files. The system performs three-level reconciliation:
1. **By Category** (Folha, Rescisão, 13º, Férias, etc.)
2. **By Event** (individual payroll event codes)
3. **By LA** (Lançamento Automático - accounting posting codes)

The core workflow: Upload PDF (payroll summary) + TXT/CSV (accounting batch) → The app extracts events from PDF, maps them to accounting codes via JSON config, and generates discrepancy reports.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Key Architecture

### Main Application (`app.py`)
- **PDF Parsing**: Uses `pdfplumber` with coordinate-based column detection to extract payroll events
  - Detects categories from section headers (e.g., "Folha", "Rescisão")
  - Identifies table headers by matching words like "codigo", "evento", "valor"
  - Groups words by Y-coordinate to form rows, assigns words to columns by X-coordinate
  - Stops parsing when reaching footer rows ("Totais", "Base INSS", etc.)
  - Returns DataFrame: `[Categoria, EventoCod, EventoNome, Valor]`

- **TXT Parsing**: Reads CSV/TXT files with auto-delimiter detection (`;` or `,`)
  - Extracts column 2 (LA code) and column 4 (value)
  - Returns DataFrame: `[CodigoLA, Valor]`

- **Mapping System**: Loads `mapeamento_dp.json` which maps:
  - Category → List of `{evento, codigo_lancamento, tipo}`
  - This enables translation between PDF events and TXT accounting codes

- **Comparison Functions**:
  - `compare_by_categoria()`: Aggregates PDF/TXT by category, calculates differences
  - `compare_by_event()`: Joins PDF events with mapped LAs, identifies unmapped events
  - `compare_by_la()`: Groups both sources by LA code for detailed reconciliation

### Category Canonicalization
`canonical_categoria()` normalizes category names (app.py:41-67):
- Handles variations like "Folha Complementar", "Rescisao Comp" → standardized names
- Critical for accurate grouping across PDF sections and JSON mapping
- Uses `normalize_text()` to remove accents and standardize case

### Utility Scripts
- **`mapping.py`**: Generator script that creates LA→Event mappings from `eventos.txt`
  - Parses event codes (3 digits) and associated LA codes (≥4 digits)
  - Outputs `mapping_eventos.json` in format: `{"LA_code": ["event1", "event2"]}`

- **`duplicatas.py`**: Deduplicates entries in `resultado_eventos_por_categoria.json`
  - Groups by `(evento, codigo_lancamento, tipo)` to remove redundancy

## Critical Files

### `mapeamento_dp.json`
The heart of the reconciliation system. Structure:
```json
{
  "Categoria": [
    {
      "evento": "003",
      "codigo_lancamento": "30055",
      "tipo": "Adicional"
    }
  ]
}
```
- Must be in same directory as `app.py` or at `/mnt/data/mapeamento_dp.json`
- Categories must match canonical form (see `canonical_categoria()`)
- Event codes are 3-digit strings, LA codes are 4+ digit strings

### Input Files
- **PDF**: Payroll summary with events grouped by category
- **TXT/CSV**: Accounting batch export (semi-colon or comma delimited)
  - Expected format: `col0, LA_CODE, col2, VALUE, ...`

## Data Flow

1. User uploads PDF + TXT via Streamlit sidebar
2. `parse_pdf_events()` extracts all events with categories
3. `parse_txt_codes_values()` extracts LA codes and values
4. `load_mapping()` provides event↔LA translation table
5. Three comparison reports generated:
   - **Category Report**: High-level totals per category
   - **Event Report**: Shows which events have discrepancies, flags unmapped events
   - **LA Report**: Most granular view by accounting code
6. Reports stored in `st.session_state` and downloadable as CSV

## Text Normalization

Always use `normalize_text()` for string comparisons:
- Removes accents (á→a, ç→c, etc.)
- Converts to lowercase
- Critical for matching category names, event descriptions across data sources

## Currency Handling

- **Input**: Brazilian format (`1.234,56`)
- **Parsing**: `parse_brl_decimal()` converts to float
- **Output**: `money()` formats back to Brazilian format with `R$` prefix
- All financial comparisons use absolute values from PDF

## Common Maintenance Tasks

### Adding New Category Aliases
Edit `canonical_categoria()` in app.py:47-60 to add new variations.

### Updating Event Mappings
1. Modify `mapeamento_dp.json` directly, OR
2. Edit `eventos.txt` and run `python mapping.py` to regenerate

### Handling Unmapped Events
Check section "4) Comparação PDF x TXT por EVENTO" in UI:
- "Eventos do PDF sem LA mapeado" table shows events needing mapping
- "LAs do TXT mapeados sem evento no PDF" shows unused accounting codes

## Important Notes

- PDF parsing relies on consistent table layouts (headers must contain "codigo", "evento", "valor")
- Category detection requires section headers before each table
- The app uses `@st.cache_data` on `load_mapping()` - clear cache if JSON changes aren't reflected
- Session state holds reports for download buttons to work properly
- All comparisons show `PDF - TXT` differences (positive = PDF higher, negative = TXT higher)
