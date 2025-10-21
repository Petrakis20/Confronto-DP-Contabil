import json

# Caminho do arquivo existente
caminho = "./resultado_eventos_por_categoria.json"

# Ler o JSON existente
with open(caminho, "r", encoding="utf-8") as f:
    dados = json.load(f)

# Nova estrutura sem duplicatas
novo = {}

for categoria, lista in dados.items():
    vistos = set()
    unicos = []
    for item in lista:
        chave = (item["evento"], item["codigo_lancamento"], item["tipo"].lower())
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    novo[categoria] = unicos

# Salvar o JSON limpo
with open("./resultado_eventos_sem_duplicatas.json", "w", encoding="utf-8") as f:
    json.dump(novo, f, ensure_ascii=False, indent=2)

print("Arquivo salvo sem duplicatas!")
