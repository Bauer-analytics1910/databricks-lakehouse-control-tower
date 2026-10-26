-- =============================================================================
-- silver.tarefas: AS TRÊS FERRAMENTAS VIRAM UMA.
-- Cada ferramenta ganha uma TEMPORARY VIEW com as MESMAS colunas:
--   projeto_id, ferramenta, id_na_ferramenta, fase, tarefa, responsavel,
--   inicio_baseline, fim_baseline, inicio_real, fim_real, pct_como_veio,
--   horas, status_na_ferramenta
-- e a materialized view final é um UNION ALL das três.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Excel (20 planilhas). Sujeiras #3, #4, #5, #6, #7.
-- -----------------------------------------------------------------------------
CREATE TEMPORARY VIEW tarefas_excel AS
SELECT
  -- de-para pelo nome do arquivo; se não casar (código vazio, ou o arquivo
  -- chegou sem acento), o PRJ-xxx vem do próprio nome do arquivo
  coalesce(p.projeto_id, regexp_extract(e.arquivo, 'PRJ-[0-9]{3}', 0)) AS projeto_id,
  'excel'                                                              AS ferramenta,
  CAST(e.id AS STRING)                                                 AS id_na_ferramenta,
  e.fase,
  e.tarefa,
  e.responsavel,
  -- #4: com '/' é dd/MM/yyyy; senão é o número de série do Excel
  CASE WHEN e.inicio_previsto LIKE '%/%' THEN try_to_date(e.inicio_previsto, 'dd/MM/yyyy')
       WHEN nullif(trim(e.inicio_previsto), '') IS NOT NULL
         THEN date_add(DATE'1899-12-30', CAST(CAST(e.inicio_previsto AS DOUBLE) AS INT)) END AS inicio_baseline,
  CASE WHEN e.termino_previsto LIKE '%/%' THEN try_to_date(e.termino_previsto, 'dd/MM/yyyy')
       WHEN nullif(trim(e.termino_previsto), '') IS NOT NULL
         THEN date_add(DATE'1899-12-30', CAST(CAST(e.termino_previsto AS DOUBLE) AS INT)) END AS fim_baseline,
  CASE WHEN e.inicio_real LIKE '%/%' THEN try_to_date(e.inicio_real, 'dd/MM/yyyy')
       WHEN nullif(trim(e.inicio_real), '') IS NOT NULL
         THEN date_add(DATE'1899-12-30', CAST(CAST(e.inicio_real AS DOUBLE) AS INT)) END AS inicio_real,
  CASE WHEN e.termino_real LIKE '%/%' THEN try_to_date(e.termino_real, 'dd/MM/yyyy')
       WHEN nullif(trim(e.termino_real), '') IS NOT NULL
         THEN date_add(DATE'1899-12-30', CAST(CAST(e.termino_real AS DOUBLE) AS INT)) END AS fim_real,
  -- #5: '45%' / '10,5%' → tira o % e troca a vírgula; 0.45 → fração × 100
  CASE WHEN contains(e.pct_concluido, '%')
         THEN CAST(replace(replace(e.pct_concluido, '%', ''), ',', '.') AS DOUBLE)
       ELSE CAST(replace(e.pct_concluido, ',', '.') AS DOUBLE) * 100 END AS pct_como_veio,
  -- #7: '40h' → 40
  CAST(replace(e.horas_previstas, 'h', '') AS DOUBLE)                  AS horas,
  -- a planilha não tem coluna de status
  CAST(NULL AS STRING)                                                 AS status_na_ferramenta
FROM lakehouse_vertice.bronze.excel_tarefas e
LEFT JOIN projetos p
  ON p.ferramenta = 'excel' AND p.codigo_ferramenta = e.arquivo
-- #6: a linha de TOTAL no fim de cada planilha não é tarefa
WHERE e.tarefa <> 'TOTAL';

-- -----------------------------------------------------------------------------
-- ClickUp (25 listas). Sujeiras #3, #8, #9.
-- -----------------------------------------------------------------------------
CREATE TEMPORARY VIEW tarefas_clickup AS
WITH campos AS (
  SELECT
    c.*,
    -- #8: % e baseline moram dentro de custom_fields (lista de structs)
    filter(c.custom_fields, f -> f.name = 'Progresso (%)')[0].value   AS cf_progresso,
    filter(c.custom_fields, f -> f.name = 'Início baseline')[0].value AS cf_inicio_baseline,
    filter(c.custom_fields, f -> f.name = 'Fim baseline')[0].value    AS cf_fim_baseline,
    filter(c.custom_fields, f -> f.name = 'Fase')[0].value            AS cf_fase,
    lower(trim(c.status.status))                                      AS status_bruto
  FROM lakehouse_vertice.bronze.clickup_tarefas c
)
SELECT
  -- de-para pelo list_id; se o código faltar, pelo nome da lista
  coalesce(p1.projeto_id, p2.projeto_id)                               AS projeto_id,
  'clickup'                                                            AS ferramenta,
  c.id                                                                 AS id_na_ferramenta,
  c.cf_fase                                                            AS fase,
  c.name                                                               AS tarefa,
  c.assignees[0].username                                              AS responsavel,
  -- baseline: milissegundos (como as outras datas) ou data em texto
  CASE WHEN c.cf_inicio_baseline RLIKE '^[0-9]{10,}$'
         THEN to_date(timestamp_millis(CAST(c.cf_inicio_baseline AS BIGINT)))
       ELSE coalesce(try_to_date(c.cf_inicio_baseline, 'yyyy-MM-dd'),
                     try_to_date(c.cf_inicio_baseline, 'dd/MM/yyyy')) END AS inicio_baseline,
  CASE WHEN c.cf_fim_baseline RLIKE '^[0-9]{10,}$'
         THEN to_date(timestamp_millis(CAST(c.cf_fim_baseline AS BIGINT)))
       ELSE coalesce(try_to_date(c.cf_fim_baseline, 'yyyy-MM-dd'),
                     try_to_date(c.cf_fim_baseline, 'dd/MM/yyyy')) END AS fim_baseline,
  -- #8: datas em milissegundos
  to_date(timestamp_millis(CAST(nullif(trim(c.start_date), '') AS BIGINT))) AS inicio_real,
  to_date(timestamp_millis(CAST(nullif(trim(c.date_done), '') AS BIGINT)))  AS fim_real,
  CAST(replace(replace(c.cf_progresso, '%', ''), ',', '.') AS DOUBLE)  AS pct_como_veio,
  c.time_estimate / 3600000.0                                          AS horas,
  -- #9: status escrito de 12 jeitos → 3 estados
  CASE
    WHEN c.status_bruto LIKE '%conclu%' OR c.status_bruto LIKE '%done%'
      OR c.status_bruto LIKE '%complete%' OR c.status_bruto LIKE '%closed%'
      OR c.status_bruto LIKE '%fechad%' OR c.status_bruto LIKE '%finaliz%'
      OR c.status_bruto LIKE '%entregue%' OR c.status_bruto LIKE '%feito%'
      THEN 'concluida'
    WHEN c.status_bruto LIKE '%to do%' OR c.status_bruto LIKE '%todo%'
      OR c.status_bruto LIKE '%to-do%' OR c.status_bruto LIKE '%fazer%'
      OR c.status_bruto LIKE '%backlog%' OR c.status_bruto LIKE '%open%'
      OR c.status_bruto LIKE '%aberto%' OR c.status_bruto LIKE '%pendente%'
      OR c.status_bruto LIKE '%not started%' OR c.status_bruto LIKE '%não inic%'
      OR c.status_bruto LIKE '%nao inic%'
      THEN 'a_fazer'
    ELSE 'em_andamento'
  END                                                                  AS status_na_ferramenta
FROM campos c
LEFT JOIN projetos p1
  ON p1.ferramenta = 'clickup' AND p1.codigo_ferramenta = c.list_id
LEFT JOIN projetos p2
  ON p2.ferramenta = 'clickup' AND p2.codigo_ferramenta IS NULL
 AND lower(trim(p2.nome_projeto)) = lower(trim(c.list_name));

-- -----------------------------------------------------------------------------
-- MS Project (15 XML). Sujeiras #10, #11, #12.
-- -----------------------------------------------------------------------------
CREATE TEMPORARY VIEW tarefas_msproject AS
WITH com_fase AS (
  -- #11: a fase é a última tarefa-resumo de nível 1 antes da tarefa.
  -- A janela roda ANTES de tirar as tarefas-resumo (senão a fase some).
  SELECT
    m.*,
    last_value(CASE WHEN m.OutlineLevel = 1 THEN m.Name END, true)
      OVER (PARTITION BY m.arquivo ORDER BY m.UID)                     AS fase
  FROM lakehouse_vertice.bronze.msproject_tarefas m
)
SELECT
  p.projeto_id,
  'msproject'                                                          AS ferramenta,
  CAST(t.UID AS STRING)                                                AS id_na_ferramenta,
  t.fase,
  t.Name                                                               AS tarefa,
  CAST(NULL AS STRING)                                                 AS responsavel,
  to_date(t.Baseline.Start)                                            AS inicio_baseline,
  to_date(t.Baseline.Finish)                                           AS fim_baseline,
  to_date(t.ActualStart)                                               AS inicio_real,
  to_date(t.ActualFinish)                                              AS fim_real,
  CAST(t.PercentComplete AS DOUBLE)                                    AS pct_como_veio,
  -- #12: 'PT40H0M0S' → 40
  CAST(nullif(regexp_extract(t.Work, 'PT([0-9]+)H', 1), '') AS DOUBLE) AS horas,
  -- o XML não traz status
  CAST(NULL AS STRING)                                                 AS status_na_ferramenta
FROM com_fase t
LEFT JOIN projetos p
  ON p.ferramenta = 'msproject' AND p.codigo_ferramenta = t.arquivo
-- #10: as tarefas-resumo somam as horas de baixo; ficam só as tarefas de verdade
WHERE t.Summary = 0;

-- -----------------------------------------------------------------------------
-- A integração: um modelo só de tarefa para as três ferramentas.
-- -----------------------------------------------------------------------------
CREATE OR REFRESH MATERIALIZED VIEW tarefas (
  CONSTRAINT achou_o_projeto   EXPECT (projeto_id IS NOT NULL)            ON VIOLATION FAIL UPDATE,
  CONSTRAINT pct_entre_0_e_100 EXPECT (pct_concluido BETWEEN 0 AND 100)   ON VIOLATION FAIL UPDATE,
  CONSTRAINT horas_positivas   EXPECT (horas > 0)                         ON VIOLATION FAIL UPDATE
)
COMMENT 'Todas as tarefas dos 60 projetos num modelo só: as planilhas Excel, as listas do ClickUp e os arquivos do MS Project integrados pelo de-para de silver.projetos. Uma linha por tarefa (tarefa_id = projeto-ferramenta-id), com fase, responsável, datas de baseline e reais, % concluído (limitado a 100, com a flag pct_veio_acima_de_100), horas previstas e o status na ferramenta (só o ClickUp tem). Tarefas-resumo e linhas de TOTAL ficam de fora.'
AS
WITH tudo AS (
  SELECT * FROM tarefas_excel
  UNION ALL
  SELECT * FROM tarefas_clickup
  UNION ALL
  SELECT * FROM tarefas_msproject
)
SELECT
  concat_ws('-', projeto_id, ferramenta, id_na_ferramenta) AS tarefa_id,
  projeto_id,
  ferramenta,
  id_na_ferramenta,
  fase,
  tarefa,
  responsavel,
  inicio_baseline,
  fim_baseline,
  inicio_real,
  fim_real,
  pct_como_veio,
  least(pct_como_veio, 100)                                AS pct_concluido,
  pct_como_veio > 100                                      AS pct_veio_acima_de_100,
  horas,
  status_na_ferramenta
FROM tudo;
