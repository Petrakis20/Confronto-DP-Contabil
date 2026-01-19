import pandas as pd
import json

# Read the Excel file
df = pd.read_excel('Pasta1.xlsx')

# Print column names to verify structure
print("Columns:", df.columns.tolist())
print(f"Total rows: {len(df)}")

# Create the new data structure for "13ª parcela"
new_data = []

for _, row in df.iterrows():
    # The Excel columns are: 'Cód. Evento', 'Nome:', 'Tipo Processo', 'Código lançamento', 'Tipo'
    # Get the event code (Cód. Evento - column 0) and format with 3 digits
    evento = str(int(row.iloc[0])).zfill(3) if pd.notna(row.iloc[0]) else ""
    # Get the codigo_lancamento (Código lançamento - column 3)
    codigo_lancamento = str(int(row.iloc[3])) if pd.notna(row.iloc[3]) else ""
    # Get the tipo (Tipo - column 4)
    tipo = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
    
    new_data.append({
        "evento": evento,
        "codigo_lancamento": codigo_lancamento,
        "tipo": tipo
    })

# Load the existing JSON file
with open('../mapeamento_dp.json', 'r', encoding='utf-8') as f:
    mapeamento = json.load(f)

# Remove old "13º Primeira Parcela" if it exists
if "13º Primeira Parcela" in mapeamento:
    del mapeamento["13º Primeira Parcela"]

# Add the new "13ª parcela" entry
mapeamento["13ª parcela"] = new_data

# Save the updated JSON file
with open('../mapeamento_dp.json', 'w', encoding='utf-8') as f:
    json.dump(mapeamento, f, ensure_ascii=False, indent=2)

print(f"\nSuccessfully updated mapeamento_dp.json!")
print(f"Added {len(new_data)} entries to '13ª parcela'")
print(f"Removed old '13º Primeira Parcela' category")
