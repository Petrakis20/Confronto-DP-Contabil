import json
import pprint

# Load the JSON file
with open('../mapeamento_dp.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Total categories in file:', len(data))
print('"13ª parcela" exists:', '13ª parcela' in data)
print('"13º Primeira Parcela" exists:', '13º Primeira Parcela' in data)

if '13ª parcela' in data:
    print('\nTotal entries in "13ª parcela":', len(data['13ª parcela']))
    print('\nFirst 3 entries:')
    pprint.pprint(data['13ª parcela'][:3])
    print('\nLast 3 entries:')
    pprint.pprint(data['13ª parcela'][-3:])
