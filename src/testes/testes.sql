-- =============================================================================
-- src/testes/testes.sql
-- 10 testes de qualidade automatizados sobre as camadas Silver e Gold.
-- Cada teste dispara raise_error() com mensagem detalhada se falhar.
-- Executado como sql_task no SQL Warehouse após a tarefa medalhao.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Os 60 projetos têm cronograma na silver.tarefas
-- -----------------------------------------------------------------------------
SELECT
  CASE
    WHEN count(DISTINCT projeto_id) = 60 THEN 'ok: 60 projetos com cronograma em silver.tarefas'
    ELSE raise_error(concat('Teste 1 falhou: esperado 60 projetos em silver.tarefas, obtido ', count(DISTINCT projeto_id)))
  END AS resultado_teste_01
FROM lakehouse_vertice.silver.tarefas;

-- -----------------------------------------------------------------------------
-- 2. Cada projeto veio de UMA ferramenta, a do cadastro do PMO
-- -----------------------------------------------------------------------------
WITH divergencias AS (
  SELECT
    t.projeto_id,
    p.ferramenta AS ferramenta_esperada,
    collect_set(t.ferramenta) AS ferramentas_obtidas
  FROM lakehouse_vertice.silver.tarefas t
  JOIN lakehouse_vertice.silver.projetos p USING (projeto_id)
  GROUP BY t.projeto_id, p.ferramenta
  HAVING size(ferramentas_obtidas) > 1 OR ferramentas_obtidas[0] <> p.ferramenta
)
SELECT
  CASE
    WHEN count(*) = 0 THEN 'ok: cada projeto veio de uma única ferramenta (a do PMO)'
    ELSE raise_error(concat('Teste 2 falhou: projetos com ferramenta divergente: ', count(*)))
  END AS resultado_teste_02
FROM divergencias;

-- -----------------------------------------------------------------------------
-- 3. As horas do Excel na silver = a soma das linhas de TOTAL das planilhas
-- -----------------------------------------------------------------------------
WITH esperado AS (
  SELECT round(sum(CAST(replace(horas_previstas, 'h', '') AS DOUBLE)), 2) AS horas_total_bronze
  FROM lakehouse_vertice.bronze.excel_tarefas
  WHERE tarefa = 'TOTAL'
),
obtido AS (
  SELECT round(sum(horas), 2) AS horas_total_silver
  FROM lakehouse_vertice.silver.tarefas
  WHERE ferramenta = 'excel'
)
SELECT
  CASE
    WHEN e.horas_total_bronze = o.horas_total_silver THEN 'ok: horas do Excel na silver batem com TOTAL'
    ELSE raise_error(concat('Teste 3 falhou: horas Excel bronze TOTAL (', e.horas_total_bronze, ') <> silver (', o.horas_total_silver, ')'))
  END AS resultado_teste_03
FROM esperado e, obtido o;

-- -----------------------------------------------------------------------------
-- 4. Uma linha por pessoa na silver (520 colaboradores únicos)
-- -----------------------------------------------------------------------------
SELECT
  CASE
    WHEN count(*) = 520 AND count(DISTINCT colaborador_id) = 520 THEN 'ok: exatamente 520 colaboradores únicos na silver'
    ELSE raise_error(concat('Teste 4 falhou: esperado 520 colaboradores únicos, obtido ', count(*), ' total e ', count(DISTINCT colaborador_id), ' distintos'))
  END AS resultado_teste_04
FROM lakehouse_vertice.silver.colaboradores;

-- -----------------------------------------------------------------------------
-- 5. A CodeForge virou um fornecedor só
-- -----------------------------------------------------------------------------
WITH codeforge AS (
  SELECT DISTINCT fornecedor
  FROM lakehouse_vertice.silver.entregas_fornecedor
  WHERE replace(lower(fornecedor), ' ', '') LIKE '%codeforge%'
)
SELECT
  CASE
    WHEN count(*) = 1 AND max(fornecedor) = 'CodeForge Consultoria Ltda' THEN 'ok: CodeForge unificada em uma única grafia'
    ELSE raise_error(concat('Teste 5 falhou: fornecedores CodeForge distintos: ', count(*), ' (', coalesce(max(fornecedor), 'vazio'), ')'))
  END AS resultado_teste_05
FROM codeforge;

-- -----------------------------------------------------------------------------
-- 6. A limpeza não mudou o custo total (bronze com replace = silver)
-- -----------------------------------------------------------------------------
WITH bronze_custo AS (
  SELECT round(sum(CAST(replace(valor, ',', '.') AS DECIMAL(18, 2))), 2) AS total_bronze
  FROM lakehouse_vertice.bronze.custos
),
silver_custo AS (
  SELECT round(sum(valor), 2) AS total_silver
  FROM lakehouse_vertice.silver.custos
)
SELECT
  CASE
    WHEN b.total_bronze = s.total_silver THEN 'ok: custo total preservado (R$ 193,35 mi)'
    ELSE raise_error(concat('Teste 6 falhou: custo total bronze (', b.total_bronze, ') <> silver (', s.total_silver, ')'))
  END AS resultado_teste_06
FROM bronze_custo b, silver_custo s;

-- -----------------------------------------------------------------------------
-- 7. Os 60 projetos têm fotografia de hoje
-- -----------------------------------------------------------------------------
SELECT
  CASE
    WHEN count(*) = 60 AND count(DISTINCT projeto_id) = 60 THEN 'ok: 60 projetos com fotografia atual em gold.projeto_situacao_atual'
    ELSE raise_error(concat('Teste 7 falhou: esperado 60 projetos na fotografia atual, obtido ', count(*)))
  END AS resultado_teste_07
FROM lakehouse_vertice.gold.projeto_situacao_atual;

-- -----------------------------------------------------------------------------
-- 8. Todo projeto em andamento tem SPI e CPI
-- -----------------------------------------------------------------------------
WITH em_andamento AS (
  SELECT
    count(*) AS total_andamento,
    count(spi) AS total_spi,
    count(cpi) AS total_cpi
  FROM lakehouse_vertice.gold.projeto_situacao_atual
  WHERE status = 'em_andamento'
)
SELECT
  CASE
    WHEN total_andamento = 41 AND total_spi = 41 AND total_cpi = 41
    THEN 'ok: todos os 41 projetos em andamento têm SPI e CPI não nulos'
    ELSE raise_error(concat('Teste 8 falhou: em andamento (', total_andamento, '), com SPI (', total_spi, '), com CPI (', total_cpi, ')'))
  END AS resultado_teste_08
FROM em_andamento;

-- -----------------------------------------------------------------------------
-- 9. O EV de hoje do status semanal bate com o das ferramentas (diferença < 1%)
-- -----------------------------------------------------------------------------
WITH ev_comparacao AS (
  SELECT
    sum(s.ev) AS ev_ferramentas,
    sum(f.ev) AS ev_status
  FROM lakehouse_vertice.gold.projeto_situacao_atual s
  JOIN lakehouse_vertice.gold.fato_projeto_semana f
    ON f.projeto_id = s.projeto_id AND f.semana = DATE'2026-10-16'
)
SELECT
  CASE
    WHEN abs(ev_ferramentas - ev_status) / nullif(ev_status, 0) < 0.01
    THEN 'ok: EV das ferramentas bate com EV do status semanal (< 1% de diferença)'
    ELSE raise_error(concat('Teste 9 falhou: EV ferramentas (', ev_ferramentas, ') difere do EV status (', ev_status, ') em mais de 1%'))
  END AS resultado_teste_09
FROM ev_comparacao;

-- -----------------------------------------------------------------------------
-- 10. AC de hoje no fato = soma dos lançamentos até hoje
-- -----------------------------------------------------------------------------
WITH ac_fato AS (
  SELECT round(sum(ac), 2) AS ac_fato_hoje
  FROM lakehouse_vertice.gold.fato_projeto_semana
  WHERE semana = DATE'2026-10-16'
),
ac_custos AS (
  SELECT round(sum(valor), 2) AS ac_custos_hoje
  FROM lakehouse_vertice.silver.custos
  WHERE data <= DATE'2026-10-16'
)
SELECT
  CASE
    WHEN f.ac_fato_hoje = c.ac_custos_hoje
    THEN 'ok: AC de hoje no fato bate exatamente com a soma dos custos até hoje'
    ELSE raise_error(concat('Teste 10 falhou: AC fato hoje (', f.ac_fato_hoje, ') <> custos hoje (', c.ac_custos_hoje, ')'))
  END AS resultado_teste_10
FROM ac_fato f, ac_custos c;
