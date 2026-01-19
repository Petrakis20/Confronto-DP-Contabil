# Solução de Problemas - Arquivo TXT

## ❌ Erro: "Nenhum lançamento válido encontrado no arquivo TXT"

Este erro ocorre quando o sistema não consegue extrair lançamentos do arquivo TXT. Veja as possíveis causas e soluções:

### 🔍 Diagnóstico Rápido

Execute o script de teste:

```bash
cd novosArquivos
python3 testar_txt.py seu_arquivo.txt
```

Este script irá mostrar:
- Primeiras 10 linhas do arquivo
- Separador detectado
- Número de colunas
- Se o código LA e valor estão nas colunas corretas
- Quantas linhas válidas foram encontradas

### ✅ Formato Esperado

O arquivo TXT deve ter **pelo menos 4 colunas** separadas por:
- `;` (ponto e vírgula) **[RECOMENDADO]**
- `,` (vírgula)
- `TAB` (tabulação)

**Estrutura:**
```
coluna0;CODIGO_LA;coluna2;VALOR;...outras colunas...
```

**Exemplo válido:**
```
000001;30055;Descrição;1234,56;outras_colunas
000002;30056;Descrição;2345,67;outras_colunas
000003;50001;Descrição;3456,78;outras_colunas
```

### 📋 Requisitos das Colunas

#### Coluna 2 (índice 1): Código LA
- ✅ Deve ser **numérico**
- ✅ Mínimo **4 dígitos**
- ❌ Não pode conter letras ou caracteres especiais
- ✅ Exemplos válidos: `30055`, `50001`, `70123`
- ❌ Exemplos inválidos: `305`, `ABC`, `30-55`

#### Coluna 4 (índice 3): Valor
- ✅ Formato brasileiro: `1.234,56`
- ✅ Formato decimal: `1234.56`
- ✅ Pode ser positivo ou negativo
- ✅ Valores zero são ignorados (não incluídos no confronto)

### 🔧 Problemas Comuns

#### 1. Separador Errado
**Problema:** Arquivo usa separador diferente do esperado

**Solução:**
- Abra o arquivo no Excel ou editor de texto
- Verifique qual caractere separa as colunas
- Salve com separador `;` (ponto e vírgula)

#### 2. Código LA na Coluna Errada
**Problema:** Código LA não está na coluna 2 (índice 1)

**Verificação:**
```
Coluna 0 | Coluna 1 | Coluna 2 | Coluna 3 | ...
    ↓         ↓           ↓          ↓
  (0)    [CÓDIGO LA]    (2)      [VALOR]
```

**Solução:**
- Reorganize as colunas do arquivo
- O código LA **DEVE** estar na segunda coluna (índice 1)
- O valor **DEVE** estar na quarta coluna (índice 3)

#### 3. Código LA com Menos de 4 Dígitos
**Problema:** Códigos como `305`, `12`, `1`

**Solução:**
- Adicione zeros à esquerda: `305` → `0305`
- Ou verifique se o código está correto no sistema contábil

#### 4. Valores com Formato Inválido
**Problema:** Valores como `R$ 1.234,56`, `1,234.56` (formato americano), `abc`

**Solução:**
- Remover símbolos de moeda (`R$`, `$`)
- Usar formato brasileiro: `1.234,56`
- Ou formato decimal: `1234.56`

#### 5. Arquivo com Cabeçalho
**Problema:** Primeira linha contém nomes de colunas

**Solução:**
- O sistema automaticamente ignora linhas que não atendem aos critérios
- Se o cabeçalho tiver código LA válido, remova a linha manualmente

#### 6. Codificação do Arquivo
**Problema:** Caracteres especiais aparecem incorretamente

**Solução:**
- Salve o arquivo com codificação UTF-8
- Ou tente Latin-1 (ISO-8859-1)
- O sistema tenta várias codificações automaticamente

### 🧪 Teste Manual

Para testar se o arquivo está correto, abra no editor de texto e verifique:

1. **Separador visível?**
   ```
   123;30055;Desc;1234,56  ← Separador: ;
   ```

2. **Segunda coluna tem 4+ dígitos numéricos?**
   ```
   123;30055;Desc;1234,56
        ↑
       OK (5 dígitos)
   ```

3. **Quarta coluna tem valor numérico?**
   ```
   123;30055;Desc;1234,56
                    ↑
                   OK
   ```

### 📊 Exemplo de Arquivo Correto

```txt
001;30055;SALARIO BASE;197791,51;outros_dados
002;30056;PERICULOSIDADE;1311,23;outros_dados
003;40001;ADIANTAMENTO;40626,89;outros_dados
004;50001;INSS FOLHA;23268,43;outros_dados
005;50002;IRRF FOLHA;22595,60;outros_dados
```

### 🆘 Se Nada Funcionar

1. **Use o script de teste:**
   ```bash
   python3 testar_txt.py seu_arquivo.txt
   ```

2. **Compartilhe as primeiras 3-5 linhas do arquivo** (sem dados sensíveis) para diagnóstico

3. **Verifique na interface Streamlit:**
   - Clique em "Ver Primeiras Linhas do Arquivo" no expander
   - Analise a estrutura mostrada
   - Compare com os exemplos acima

4. **Alternativa: Use o processamento via linha de comando**
   ```bash
   python3 processar_resumos_modernos.py seu_arquivo.txt
   ```
   Pode fornecer mensagens de erro mais detalhadas

### ✅ Checklist Final

Antes de fazer upload, confirme:

- [ ] Arquivo tem separador claro (`;`, `,` ou TAB)
- [ ] Coluna 2 (índice 1) contém códigos numéricos de 4+ dígitos
- [ ] Coluna 4 (índice 3) contém valores numéricos
- [ ] Arquivo tem pelo menos 4 colunas
- [ ] Não há linhas completamente vazias (ou são poucas)
- [ ] Codificação é UTF-8 ou Latin-1

Se tudo estiver OK e ainda não funcionar, o problema pode ser específico do formato do seu sistema contábil. Neste caso, será necessário adaptar o código para o formato específico.
