# Sistema Moderno de Processamento de Resumos DP

## Visão Geral

O novo sistema `processar_resumos_modernos.py` é uma solução completa para processar diferentes tipos de resumos de folha de pagamento e confrontá-los com lançamentos contábeis.

## Funcionalidades

### 1. Extração de Eventos por Tipo de Resumo

O sistema identifica automaticamente o tipo de resumo pelo nome do arquivo:

| Padrão no Nome | Categoria Gerada |
|----------------|------------------|
| "13", "decimo" | 13º Primeira Parcela |
| "adiantamento" | Adiantamento |
| "ferias" | Férias |
| "folha" (sem "geral") | Folha |
| "rescisao" | Rescisão |
| "geral" | Geral (processamento especial) |

**Para resumos específicos (13º, Adiantamento, Férias, Folha, Rescisão):**
- Extrai apenas: **Código do Evento** (3 dígitos) e **Total**
- Ignora colunas intermediárias (Ativos, Demitidos, Afastados)
- Agrupa eventos por categoria

### 2. Extração de Impostos Consolidados (Resumo Geral)

**Do Resumo Geral, extrai APENAS:**

#### INSS
- **INSS Total Líquido**: Valor líquido a recolher

#### FGTS
- **FGTS Total Apurado recibos s/CS**: Total calculado sem compensação

#### IRRF
- **IRRF Folha**: Imposto de Renda sobre folha normal
- **IRRF Férias**: Imposto de Renda sobre férias
- **IRRF Rescisão**: Imposto de Renda sobre rescisões
- **IRRF Sócio**: Imposto de Renda sobre pró-labore de sócios
- **IRRF Autônomo**: Imposto de Renda sobre autônomos
- **IRRF Total**: Soma de todos os IRRF acima

#### Pró-Labore
- **ProLabore_Socios_Liquido**: Pró-labore bruto - INSS (líquido)
- **ProLabore_Autonomos_Liquido**: Autônomos bruto - INSS (líquido)

### 3. Confronto com TXT Contábil (Opcional)

Se um arquivo TXT for fornecido como argumento, o sistema:

1. **Carrega o mapeamento** (`mapeamento_dp.json`)
   - Mapeia eventos (código de 3 dígitos) para lançamentos contábeis (LA, 4+ dígitos)
   - Organizado por categoria

2. **Extrai lançamentos do TXT**
   - Formato: Coluna 2 = Código LA, Coluna 4 = Valor
   - Suporta separadores: `;` ou `,`

3. **Realiza o confronto**
   - Agrupa eventos do PDF por LA (usando mapeamento)
   - Agrupa lançamentos do TXT por LA
   - Compara totais: `PDF - TXT`

4. **Classifica resultados**
   - ✅ **OK**: Diferença < R$ 0,01
   - ⚠️ **Divergência**: Valores diferentes entre PDF e TXT
   - 📄 **Apenas no PDF**: LA mapeado mas sem lançamento no TXT
   - 📝 **Apenas no TXT**: LA no TXT sem evento correspondente no PDF

## Como Usar

### Modo Básico (Apenas Extração)
```bash
cd novosArquivos
python3 processar_resumos_modernos.py
```

**Resultado**: Excel com abas:
- `Resumo`: Quantidade de eventos por categoria
- `Eventos_<Categoria>`: Eventos extraídos de cada tipo
- `Impostos_Geral`: Impostos consolidados do Resumo Geral

### Modo Completo (Extração + Confronto)
```bash
cd novosArquivos
python3 processar_resumos_modernos.py /caminho/para/arquivo.txt
```

**Resultado**: Excel com abas adicionais:
- `Confronto_PDF_TXT`: Comparação por LA com status
- `Eventos_Mapeados`: Todos os eventos com seus LAs
- `Eventos_Nao_Mapeados`: Eventos sem mapeamento definido
- `Lancamentos_TXT`: Lançamentos extraídos do TXT

## Estrutura do Mapeamento

O arquivo `mapeamento_dp.json` deve estar no diretório pai:

```json
{
  "Categoria": [
    {
      "evento": "001",
      "codigo_lancamento": "30055",
      "tipo": "Adicional"
    }
  ]
}
```

**Campos**:
- `evento`: Código do evento no PDF (3 dígitos)
- `codigo_lancamento`: Código LA contábil (4+ dígitos)
- `tipo`: Classificação (Adicional, Desconto, etc.)

## Arquivos Gerados

### Nomenclatura
`confronto_dp_YYYYMMDD_HHMMSS.xlsx`

Exemplo: `confronto_dp_20260105_160338.xlsx`

### Abas do Excel

#### Sempre Geradas:
1. **Resumo**: Totalizador de eventos por categoria
2. **Eventos_<Categoria>**: Uma aba para cada tipo encontrado
3. **Impostos_Geral**: Impostos consolidados (se Resumo Geral presente)

#### Geradas com TXT:
4. **Confronto_PDF_TXT**: Comparação detalhada com status
5. **Eventos_Mapeados**: Vinculação evento→LA
6. **Eventos_Nao_Mapeados**: Eventos pendentes de mapeamento
7. **Lancamentos_TXT**: Lançamentos brutos do arquivo contábil

## Vantagens do Novo Sistema

1. **Modular**: Separa extração de confronto
2. **Flexível**: Funciona com ou sem TXT
3. **Automático**: Identifica tipos de resumo por nome de arquivo
4. **Completo**: Extrai tanto eventos quanto impostos consolidados
5. **Rastreável**: Identifica eventos não mapeados
6. **Preciso**: Tolerância de R$ 0,01 para diferenças de arredondamento

## Próximos Passos

Para utilizar o sistema completo:

1. **Preparar PDFs**: Colocar todos os resumos em `novosArquivos/`
2. **Preparar TXT**: Exportar lançamentos contábeis no formato esperado
3. **Verificar Mapeamento**: Conferir se todos os eventos estão em `mapeamento_dp.json`
4. **Executar**: Rodar o script com ou sem TXT
5. **Analisar**: Verificar aba `Confronto_PDF_TXT` para divergências

## Solução de Problemas

### Eventos não extraídos
- Verifique se o PDF tem o formato de tabela esperado
- Códigos devem ter exatamente 3 dígitos
- Valores devem estar no formato brasileiro (1.234,56)

### Eventos não mapeados
- Adicione o mapeamento em `mapeamento_dp.json`
- Verifique a categoria correta
- Consulte a aba `Eventos_Nao_Mapeados`

### Divergências no confronto
- Verifique se o LA está correto no mapeamento
- Confira se o TXT tem o formato esperado (colunas 2 e 4)
- Analise valores na aba `Confronto_PDF_TXT`
