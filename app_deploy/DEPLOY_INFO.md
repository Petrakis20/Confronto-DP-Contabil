# 📦 Pacote de Deploy - Sistema de Processamento de Resumos DP

## ✅ Arquivos Incluídos

Este pacote contém **TODOS** os arquivos necessários para executar a aplicação em um novo servidor.

### 1. **app_resumos.py** (103 KB)
   - Aplicação principal Streamlit
   - Interface web completa
   - Todas as funções de processamento integradas
   - Não depende de nenhum outro arquivo Python customizado

### 2. **mapeamento_dp.json** (159 KB)
   - Arquivo de configuração essencial
   - Mapeia eventos de folha para códigos contábeis
   - Contém mapeamentos para:
     - Folha
     - Férias
     - 13ª Parcela
     - Adiantamento
     - Rescisão
     - INSS
     - FGTS
     - IRRF
     - Pró-Labore

### 3. **requirements.txt**
   - Lista de dependências Python:
     - streamlit (framework web)
     - pandas (manipulação de dados)
     - pdfplumber (extração de PDF)
   
### 4. **README.md**
   - Documentação completa
   - Instruções de instalação
   - Guia de uso
   - Solução de problemas

### 5. **iniciar.sh** (Linux/Mac)
   - Script de inicialização para sistemas Unix
   - Verifica dependências automaticamente
   - Instala pacotes se necessário
   - Inicia a aplicação

### 6. **iniciar.bat** (Windows)
   - Script de inicialização para Windows
   - Mesma funcionalidade do .sh
   - Compatível com Windows Server

---

## 🚀 Como Usar

### Opção 1: Inicialização Rápida (Recomendado)

**Linux/Mac:**
```bash
./iniciar.sh
```

**Windows:**
```cmd
iniciar.bat
```

### Opção 2: Manual

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar aplicação
streamlit run app_resumos.py
```

---

## 📊 Dependências Externas

A aplicação usa apenas bibliotecas Python padrão e de terceiros bem estabelecidas:

- **Python 3.8+** (obrigatório)
- **streamlit** - Framework web
- **pandas** - Análise de dados
- **pdfplumber** - Extração de texto de PDFs

**Bibliotecas nativas do Python (já incluídas):**
- re (regex)
- json
- io
- pathlib
- datetime
- collections
- csv

---

## 📁 Estrutura Esperada no Servidor

```
app_deploy/
├── app_resumos.py          ← Aplicação principal
├── mapeamento_dp.json      ← Configuração de mapeamento
├── requirements.txt        ← Dependências
├── README.md               ← Documentação
├── iniciar.sh              ← Scripts de inicialização
└── iniciar.bat             ←
```

**IMPORTANTE:** O arquivo `mapeamento_dp.json` DEVE estar:
- No mesmo diretório que `app_resumos.py`, OU
- No diretório pai de `app_resumos.py`

O código busca automaticamente em ambos os locais.

---

## 🔒 Requisitos do Sistema

### Mínimos:
- **SO:** Linux, macOS, ou Windows Server
- **Python:** 3.8 ou superior
- **RAM:** 512 MB
- **Disco:** 500 MB de espaço livre

### Recomendados:
- **RAM:** 2 GB ou mais
- **CPU:** 2 cores ou mais
- **Disco:** 2 GB de espaço livre

---

## ✅ Checklist de Deploy

- [ ] Copiar todos os arquivos para o servidor
- [ ] Verificar versão do Python (`python3 --version`)
- [ ] Executar script de inicialização ou instalar dependências
- [ ] Acessar http://localhost:8501
- [ ] Testar upload de um arquivo PDF e TXT
- [ ] Verificar se o processamento funciona corretamente

---

## 🎯 Próximos Passos

Depois de copiar esta pasta para o novo servidor:

1. **Abra um terminal** no diretório `app_deploy`
2. **Execute o script de inicialização:**
   - Linux/Mac: `./iniciar.sh`
   - Windows: `iniciar.bat`
3. **Acesse** http://localhost:8501 no navegador
4. **Teste** com seus arquivos PDF e TXT

---

## 📞 Observações

- ✅ **Nenhum arquivo foi excluído** do projeto original
- ✅ Todos os arquivos foram **copiados** (não movidos)
- ✅ A pasta original `novosArquivos` permanece intacta
- ✅ Este é um pacote **completo e independente**

---

**Pacote criado em:** 19 de Janeiro de 2026
**Versão:** 1.0
