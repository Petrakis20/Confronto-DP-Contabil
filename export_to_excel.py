import json
import pandas as pd

# Carregar o arquivo JSON
with open('mapeamento_dp.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Criar lista para armazenar os dados
rows = []

# Iterar sobre cada categoria e seus eventos
for categoria, eventos in data.items():
    for evento in eventos:
        rows.append({
            'Categoria': categoria,
            'Evento': evento['evento'],
            'Código de Lançamento': evento['codigo_lancamento'],
            'Tipo': evento['tipo']
        })

# Criar DataFrame
df = pd.DataFrame(rows)

# Exportar para Excel
output_file = 'mapeamento_dp.xlsx'
df.to_excel(output_file, index=False, sheet_name='Mapeamento')

print(f'Arquivo exportado com sucesso: {output_file}')
print(f'Total de linhas: {len(df)}')
