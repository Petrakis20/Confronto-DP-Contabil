# Como Executar a Interface Streamlit

## 🚀 Início Rápido

### 1. Abrir Terminal
Navegue até a pasta do projeto:

```bash
cd /Users/matheuspetrakis/Documents/GitHub/Confronto-DP-Contabil/novosArquivos
```

### 2. Executar a Interface
```bash
streamlit run app_resumos.py
```

### 3. Acessar no Navegador
A interface abrirá automaticamente em:
```
http://localhost:8501
```

Se não abrir automaticamente, copie e cole esse endereço no navegador.

## 📁 Arquivos Necessários

### Obrigatórios
- ✅ `app_resumos.py` - Interface Streamlit (já criado)
- ✅ `mapeamento_dp.json` - Mapeamento de eventos (no diretório pai)

### Para Processar
- 📄 PDFs dos resumos (13º, Adiantamento, Férias, Folha, Rescisão, Geral)
- 📝 TXT/CSV contábil (opcional, para confronto)

## 🎯 Fluxo de Trabalho

```
1. Execute: streamlit run app_resumos.py
2. Interface abre no navegador
3. Faça upload dos PDFs
4. (Opcional) Faça upload do TXT
5. Clique em "Processar"
6. Visualize resultados
7. Baixe relatório Excel
```

## ⚙️ Opções Avançadas

### Executar em Porta Diferente
```bash
streamlit run app_resumos.py --server.port 8502
```

### Desabilitar Auto-Abertura do Navegador
```bash
streamlit run app_resumos.py --server.headless true
```

### Modo de Desenvolvimento (Auto-Reload)
```bash
streamlit run app_resumos.py --server.runOnSave true
```

## 🛑 Parar a Aplicação

No terminal onde o Streamlit está rodando:
- Pressione `Ctrl + C`

## 🔄 Alternativa: Linha de Comando

Se preferir processar sem interface gráfica:

```bash
python3 processar_resumos_modernos.py
```

Com arquivo TXT:
```bash
python3 processar_resumos_modernos.py arquivo.txt
```

## 📊 Comparação

| Método | Interface | Upload | Visualização | Confronto |
|--------|-----------|--------|--------------|-----------|
| **Streamlit** | ✅ Gráfica | ✅ Drag & Drop | ✅ Interativa | ✅ Automático |
| **Linha de Comando** | ❌ Terminal | ❌ Arquivos locais | ❌ Texto | ⚠️ Manual |

## 💡 Recomendação

**Use a Interface Streamlit** (`app_resumos.py`) para:
- ✅ Melhor experiência de usuário
- ✅ Visualização interativa
- ✅ Upload fácil de arquivos
- ✅ Análise visual de resultados

**Use Linha de Comando** (`processar_resumos_modernos.py`) para:
- ⚡ Processamento em lote automatizado
- 🤖 Integração com scripts
- 📦 Processamento em servidor sem interface

## 🆘 Problemas Comuns

### "Command not found: streamlit"
```bash
pip install streamlit
```

### Porta 8501 já em uso
```bash
streamlit run app_resumos.py --server.port 8502
```

### Erro ao carregar mapeamento
Verifique se `mapeamento_dp.json` existe em:
```
/Users/matheuspetrakis/Documents/GitHub/Confronto-DP-Contabil/mapeamento_dp.json
```

### Interface não atualiza
- Recarregue a página do navegador
- Ou pressione `R` na interface
