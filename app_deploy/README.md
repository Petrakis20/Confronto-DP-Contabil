# Sistema de Processamento de Resumos DP - Pacote de Deployment

Este pacote contém todos os arquivos necessários para executar a aplicação de processamento de resumos DP em um novo servidor.

## 📦 Conteúdo do Pacote

- `app_resumos.py` - Aplicação principal Streamlit
- `mapeamento_dp.json` - Arquivo de mapeamento de eventos para lançamentos contábeis
- `requirements.txt` - Dependências Python necessárias
- `README.md` - Este arquivo

## 🚀 Como Executar

### 1. Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### 2. Instalação

```bash
# Instalar as dependências
pip install -r requirements.txt
```

### 3. Executar a Aplicação

```bash
# Rodar o Streamlit
streamlit run app_resumos.py
```

A aplicação será iniciada e estará disponível em: `http://localhost:8501`

## 📋 Como Usar

1. Acesse a aplicação no navegador
2. Faça upload dos arquivos PDF (resumos de folha, férias, etc.)
3. Faça upload do arquivo TXT contábil
4. Clique em "🚀 Processar Arquivos"
5. Visualize os resultados do confronto

## 🔧 Configuração

O arquivo `mapeamento_dp.json` contém as configurações de mapeamento de eventos para códigos de lançamento. Este arquivo já está configurado e não precisa ser modificado, a menos que novos eventos precisem ser adicionados.

## 📝 Estrutura de Arquivos Esperados

### PDFs:
- Resumo Geral
- Resumo Folha
- Resumo Férias
- Resumo 13ª Parcela
- Resumo Adiantamento
- Resumo Rescisão

### TXT:
- Arquivo de lançamentos contábeis (formato CSV/TXT)

## 🐛 Solução de Problemas

### A aplicação não inicia:
```bash
# Verifique se o Streamlit está instalado corretamente
streamlit --version

# Se necessário, reinstale as dependências
pip install --force-reinstall -r requirements.txt
```

### Erro ao processar arquivos:
- Verifique se o arquivo `mapeamento_dp.json` está no mesmo diretório que `app_resumos.py`
- Confirme que os PDFs estão no formato esperado

## 📞 Suporte

Em caso de problemas, verifique:
1. Todos os arquivos estão no mesmo diretório
2. As dependências foram instaladas corretamente
3. A versão do Python é compatível (3.8+)
