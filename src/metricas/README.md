# Camada Semântica & Dicionário de Métricas Governadas (`gold.mv_projetos`)

Este diretório contém a definição da **Metric View `lakehouse_vertice.gold.mv_projetos`** ([`metricas.sql`](metricas.sql)), que estabelece a **fonte única de verdade (Single Source of Truth)** para todos os indicadores de negócio da carteira de projetos da **Vértice Tecnologia** no **Unity Catalog**.

> **Regra de Ouro da Governança**: Nenhuma fórmula de KPI (SPI, CPI, EAC, Estouro Previsto, Margem ou Melancia) deve ser recalculada manualmente em dashboards ou prompts. Tanto o **Dashboard Executivo AI/BI**, quanto o **Agente Analítico Genie** e a **Torre de Controle** consomem as regras consolidadas nesta camada.
> **Data-base oficial do dataset (`HOJE`)**: `2026-10-16`.

---

## 1. Arquitetura da Metric View

A view `lakehouse_vertice.gold.mv_projetos` é declarada com `WITH METRICS LANGUAGE YAML` (especificação `version: 1.1`) sobre a Materialized View [`lakehouse_vertice.gold.projeto_situacao_atual`](../gold/02-situacao-e-pessoas.sql), aplicando o filtro padrão `status = 'em_andamento'` (41 projetos ativos da carteira).

---

## 2. Fórmulas Base (Gerenciamento do Valor Agregado — EVM)

No nível de cada projeto ([`src/gold/02-situacao-e-pessoas.sql`](../gold/02-situacao-e-pessoas.sql) e [`src/gold/01-fato-projeto-semana.sql`](../gold/01-fato-projeto-semana.sql)), os insumos fundamentais são:

| Sigla | Nome de Negócio | Definição e Cálculo na Camada Gold |
| :--- | :--- | :--- |
| **`PV`** | **Valor Planejado** (*Planned Value*) | Parcela do orçamento de custo (`orcamento`) que deveria ter sido executada até `16/10/2026` conforme o cronograma baseline das tarefas:<br/>$$\text{PV} = \text{Orçamento} \times \frac{\sum \text{Horas Baseline Decorridas}}{\sum \text{Horas Totais Previstas}}$$ |
| **`EV`** | **Valor Agregado** (*Earned Value*) | Valor orçado do trabalho efetivamente concluído até `16/10/2026` a partir do avanço físico real das tarefas:<br/>$$\text{EV} = \text{Orçamento} \times \frac{\sum \left(\text{Horas da Tarefa} \times \frac{\%\text{Concluído}}{100}\right)}{\sum \text{Horas Totais Previstas}}$$ |
| **`AC`** | **Custo Real** (*Actual Cost*) | Soma acumulada de todos os lançamentos financeiros em `silver.custos` (folha, consultoria terceirizada, cloud e licenças) realizados até `16/10/2026`:<br/>$$\text{AC} = \sum_{\text{data} \le \text{2026-10-16}} \text{valor}$$ |

---

## 3. Medidas Governadas em `gold.mv_projetos` (`measures`)

| Medida (`name`) | Expressão Governada (`expr`) | Definição de Negócio e Interpretação Executiva | Sinônimos Configurados (NL2SQL / Genie) |
| :--- | :--- | :--- | :--- |
| **`projetos`** | `COUNT(1)` | Quantidade total de projetos em andamento no recorte analisado. | *quantidade de projetos*, *número de projetos* |
| **`carteira`** | `SUM(valor_contrato)` | Soma do valor contratado pelo cliente (receita bruta contratada em R$). | *valor da carteira*, *valor dos contratos*, *receita contratada* |
| **`spi`** | `SUM(ev) / SUM(pv)` | **Índice de Performance de Prazo** (*Schedule Performance Index*). Mede a velocidade de entrega da carteira: valores **`< 1,00`** indicam atraso em relação ao baseline; **`>= 1,00`** indicam cronograma em dia ou adiantado. | *índice de prazo*, *schedule performance index* |
| **`cpi`** | `SUM(ev) / SUM(ac)` | **Índice de Performance de Custo** (*Cost Performance Index*). Mede a eficiência financeira: quanto de valor agregado foi entregue para cada R$ 1,00 gasto. Valores **`< 1,00`** indicam estouro de custo. | *índice de custo*, *cost performance index* |
| **`eac`** | `SUM(eac)` | **Estimativa no Término** (*Estimate at Completion*). Projeção do custo final de cada projeto mantendo o `CPI` atual ($\text{EAC}_i = \text{Orçamento}_i / \text{CPI}_i$), somada para a carteira. | *custo estimado no término*, *estimativa no término* |
| **`estouro_previsto`** | `SUM(estouro_previsto)` | Sobrecusto total projetado em R$, considerando apenas projetos onde o custo estimado no término supera o orçamento ($\max(\text{EAC}_i - \text{Orçamento}_i, 0)$). | *estouro*, *quanto vai estourar*, *sobrecusto previsto* |
| **`margem_projetada`** | `(SUM(valor_contrato) - SUM(eac)) / SUM(valor_contrato)` | Margem bruta percentual esperada ao final dos contratos após descontar a estimativa de custo no término (`EAC`). | *margem*, *margem prevista* |
| **`atraso_projetado_medio_dias`** | `AVG(atraso_projetado_dias)` | Média de dias de atraso projetado no término, calculada por projeto como $\text{Duração Baseline} / \text{SPI} - \text{Duração Baseline}$. | *atraso médio*, *atraso previsto em dias* |
| **`projetos_em_risco`** | `COUNT(1) FILTER (WHERE situacao IN ('atenção', 'crítico'))` | Total de projetos ativos que operam abaixo da faixa saudável (`SPI < 0,90` ou `CPI < 0,90`). | — |
| **`projetos_criticos`** | `COUNT(1) FILTER (WHERE situacao = 'crítico')` | Total de projetos ativos em estado severo (`SPI < 0,80` ou `CPI < 0,80`). | *críticos* |
| **`projetos_melancia`** | `COUNT(1) FILTER (WHERE melancia)` | **Projetos Melancia** (*"verdes por fora, vermelhos por dentro"*): projetos em andamento cujo gerente reportou `farol_do_gerente = 'verde'` no último status semanal, mas cujo cronograma real apresenta **`SPI < 0,90`**. | *melancias*, *farol verde atrasado* |

---

## 4. Dimensões e Regras de Classificação (`dimensions`)

| Dimensão | Regra / Domínio de Valores | Uso Analítico |
| :--- | :--- | :--- |
| **`projeto_id` / `projeto`** | `PRJ-001` a `PRJ-060` (`PRJ-000 · Nome`) | Identificador canônico e rótulo executivo do projeto. |
| **`cliente` / `segmento`** | `varejo`, `financeiro`, `saude`, `logistica`, `industria` | Análise de rentabilidade e risco por conta ou vertical de negócios. |
| **`ferramenta`** | `excel`, `clickup`, `msproject` | Sistema de origem onde o cronograma é mantido pelo gerente. |
| **`gerente_projeto`** | Nome do Gerente de Projeto (GP) | Responsável direto pela entrega e pelo reporte semanal de status. |
| **`situacao`** | - **`crítico`**: `SPI < 0,80` ou `CPI < 0,80`<br/>- **`atenção`**: `0,80 <= min(SPI, CPI) < 0,90`<br/>- **`ok`**: `SPI >= 0,90` e `CPI >= 0,90` | Regra oficial de corte da Torre de Controle para priorização executiva. |
| **`farol_do_gerente`** | `verde`, `amarelo`, `vermelho` | Percepção subjetiva declarada pelo gerente no último boletim semanal. |
| **`farol_calculado`** | - **`verde`**: `SPI >= 0,95`<br/>- **`amarelo`**: `0,90 <= SPI < 0,95`<br/>- **`vermelho`**: `SPI < 0,90` | Farol objetivo calculado automaticamente pelas diretrizes do PMO da Vértice. |
