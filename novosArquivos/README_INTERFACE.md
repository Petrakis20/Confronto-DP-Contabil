# Interface Streamlit - Processamento de Resumos DP

## 🚀 Como Usar

### Iniciar a aplicação

```bash
cd novosArquivos
streamlit run app_resumos.py
```

A interface abrirá automaticamente no navegador em `http://localhost:8501`

## 📋 Passo a Passo

### 1️⃣ Upload de PDFs
Na barra lateral esquerda, faça upload de todos os resumos:
- ✅ Resumo de 13º
- ✅ Resumo de Adiantamento
- ✅ Resumo de Férias
- ✅ Resumo de Folha
- ✅ Resumo de Rescisão
- ✅ Resumo Geral

**O sistema identifica automaticamente o tipo de cada resumo pelo nome do arquivo!**

### 2️⃣ Upload do TXT (Opcional)
Se você deseja realizar o confronto com lançamentos contábeis:
- Faça upload do arquivo TXT ou CSV
- Formato esperado: Coluna 2 = Código LA, Coluna 4 = Valor

### 3️⃣ Processar
Clique no botão **"🚀 Processar"** na barra lateral

### 4️⃣ Visualizar Resultados

A interface exibirá:

#### 📊 Métricas Gerais
- Total de PDFs processados
- Categorias encontradas
- Eventos extraídos
- Impostos do Resumo Geral

#### 📋 Eventos por Categoria
- Tabela resumida com totais por categoria
- Detalhes expandíveis para ver eventos individuais
- Filtros por categoria

#### 💰 Impostos Consolidados (Resumo Geral)
Cards visuais com:
- **INSS Total Líquido**
- **FGTS Total Apurado**
- **IRRF Total** (soma de Folha + Férias + Rescisão + Sócio + Autônomo)
- **Pró-Labore Sócios** (líquido)
- **Autônomos** (líquido)

#### 🔄 Confronto PDF x TXT
Se TXT foi fornecido:
- Estatísticas do confronto (OK, Divergências, etc.)
- Tabela interativa com filtros por status
- Comparação detalhada por código LA

### 5️⃣ Download
Clique em **"📥 Baixar Relatório Excel"** para baixar o arquivo completo com todas as abas:
- Resumo
- Eventos por categoria
- Impostos do Resumo Geral
- Confronto PDF x TXT (se TXT fornecido)
- Eventos Mapeados
- Eventos Não Mapeados

## 🎨 Recursos da Interface

### ✨ Interatividade
- Upload de múltiplos arquivos simultaneamente
- Filtros dinâmicos por categoria e status
- Tabelas expansíveis para detalhes
- Progress bar durante processamento

### 🎯 Visualização
- Cards coloridos com gradientes para métricas principais
- Tabelas formatadas com valores em moeda brasileira
- Ícones e emojis para fácil identificação
- Layout responsivo em colunas

### 📊 Análise
- Métricas consolidadas em tempo real
- Comparação visual entre PDF e TXT
- Identificação automática de divergências
- Destaque para eventos não mapeados

## 🔍 Detalhes Técnicos

### Identificação de Resumos
O sistema identifica o tipo de resumo procurando palavras-chave no nome do arquivo:

| Palavra-chave | Tipo Identificado |
|---------------|-------------------|
| "13", "decimo" | 13º Primeira Parcela |
| "adiantamento" | Adiantamento |
| "ferias" | Férias |
| "folha" | Folha |
| "rescisao" | Rescisão |
| "geral" | Geral |

### Extração de Dados

**Resumos Específicos:**
- Extrai apenas: Código (3 dígitos) + Total
- Ignora colunas intermediárias
- Agrupa por categoria

**Resumo Geral:**
- INSS: Busca "Total Líquido"
- FGTS: Busca "Total FGTS apurado recibos s/CS"
- IRRF: Extrai da seção "DARF IR" e soma componentes
- Pró-Labore: Extrai da seção "Valores pagos aos Sócios / Autônomos"

### Confronto
1. Mapeia eventos → LAs usando `mapeamento_dp.json`
2. Agrupa PDF e TXT por código LA
3. Compara totais com tolerância de R$ 0,01
4. Classifica em: OK, Divergência, Apenas PDF, Apenas TXT

## 🛠️ Solução de Problemas

### Nenhum evento extraído
- Verifique se o PDF tem a estrutura de tabela esperada
- Confirme que os códigos têm 3 dígitos
- Veja se os valores estão em formato brasileiro (1.234,56)

### Impostos não encontrados (Resumo Geral)
- Confirme que o arquivo é realmente um Resumo Geral
- Verifique se as seções estão no formato padrão
- Nome do arquivo deve conter "geral"

### Confronto não funciona
- Verifique se o TXT tem o formato correto (colunas 2 e 4)
- Confirme que `mapeamento_dp.json` existe no diretório pai
- Veja a aba "Eventos Não Mapeados" para eventos sem LA

### Erro ao processar
- Verifique o tamanho dos arquivos (PDFs muito grandes podem demorar)
- Confirme que os PDFs não estão corrompidos
- Tente processar um arquivo por vez para identificar o problema

## 💡 Dicas

1. **Nomes de Arquivo**: Use nomes descritivos que contenham palavras-chave (ex: "Resumo_Folha_11_2025.pdf")

2. **Múltiplos Arquivos**: Você pode fazer upload de todos os PDFs de uma vez

3. **Filtros**: Use os filtros de status no confronto para focar em divergências

4. **Download**: Baixe o Excel para análise mais detalhada offline

5. **Reprocessamento**: Basta fazer novo upload e clicar em Processar novamente

## 📝 Exemplo de Uso

```
1. Arraste todos os PDFs para a área de upload (13º, Adiantamento, Férias, Folha, Rescisão, Geral)
2. (Opcional) Arraste o arquivo TXT contábil
3. Clique em "🚀 Processar"
4. Aguarde o processamento (barra de progresso)
5. Navegue pelas seções para visualizar os dados
6. Use filtros para análise específica
7. Baixe o relatório Excel completo
```

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique os logs no terminal onde o Streamlit está rodando
2. Consulte o README_SISTEMA_MODERNO.md para detalhes técnicos
3. Verifique se todos os arquivos necessários estão presentes
