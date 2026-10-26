-- =============================================================================
-- silver.projetos: o cadastro do PMO, limpo e tipado.
-- É o DE-PARA da integração: ferramenta + codigo_ferramenta dizem em qual
-- planilha / lista do ClickUp / arquivo do MS Project mora cada projeto.
-- Sujeiras tratadas (CLAUDE.md, seção 3): #1 data em dois formatos,
-- #2 ferramenta escrita de 8 jeitos, #3 código da ferramenta vazio.
-- =============================================================================
CREATE OR REFRESH MATERIALIZED VIEW projetos (
  CONSTRAINT data_inicio_valida EXPECT (data_inicio IS NOT NULL) ON VIOLATION FAIL UPDATE,
  CONSTRAINT ferramenta_valida  EXPECT (ferramenta IN ('excel', 'clickup', 'msproject')) ON VIOLATION FAIL UPDATE
)
COMMENT 'Cadastro dos 60 projetos da Vértice (PMO): cliente, segmento, contrato, orçamento, datas, gerente e a ferramenta onde o projeto é controlado (excel, clickup ou msproject) com o código na ferramenta. É o de-para que integra as três ferramentas em silver.tarefas.'
AS
SELECT
  projeto_id,
  nome_projeto,
  cliente,
  segmento,
  tipo_projeto,
  -- #2: a ferramenta veio escrita de 8 jeitos; normalizamos por LIKE
  CASE
    WHEN lower(ferramenta) LIKE '%click%'   THEN 'clickup'
    WHEN lower(ferramenta) LIKE '%project%'
      OR lower(ferramenta) LIKE '%msp%'     THEN 'msproject'
    WHEN lower(ferramenta) LIKE '%excel%'
      OR lower(ferramenta) LIKE '%planilha%'
      OR lower(ferramenta) LIKE '%xls%'     THEN 'excel'
  END                                                          AS ferramenta,
  ferramenta                                                   AS ferramenta_como_veio,
  -- #3: código vazio vira NULL (a tarefa casa pelo nome do arquivo / da lista)
  nullif(trim(codigo_ferramenta), '')                          AS codigo_ferramenta,
  CAST(replace(valor_contrato, ',', '.') AS DECIMAL(18, 2))    AS valor_contrato,
  CAST(replace(orcamento_custo, ',', '.') AS DECIMAL(18, 2))   AS orcamento_custo,
  -- #1: data em yyyy-MM-dd ou dd/MM/yyyy
  coalesce(try_to_date(data_inicio, 'yyyy-MM-dd'),
           try_to_date(data_inicio, 'dd/MM/yyyy'))             AS data_inicio,
  coalesce(try_to_date(data_fim_baseline, 'yyyy-MM-dd'),
           try_to_date(data_fim_baseline, 'dd/MM/yyyy'))       AS data_fim_baseline,
  lower(trim(status))                                          AS status,
  gerente_projeto
FROM lakehouse_vertice.bronze.projetos;
