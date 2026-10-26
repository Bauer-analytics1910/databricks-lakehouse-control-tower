-- =============================================================================
-- silver.colaboradores e silver.apontamentos
-- Sujeira tratada: #16 pessoa cadastrada duas vezes.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW colaboradores
COMMENT 'As 520 pessoas da Vértice: papel, senioridade, custo por hora, data de admissão e de desligamento (vazia = ativa). COL0102, COL0257 e COL0433 vinham duplicadas na bronze (uma cópia em CAIXA ALTA); fica o cadastro com papel em minúsculas.'
AS
WITH ordenado AS (
  SELECT
    *,
    -- #16: entre as duplicatas, o cadastro bom é o de papel em minúsculas
    row_number() OVER (
      PARTITION BY colaborador_id
      ORDER BY CASE WHEN papel = lower(papel) THEN 0 ELSE 1 END
    ) AS rn
  FROM lakehouse_vertice.bronze.colaboradores
)
SELECT
  colaborador_id,
  nome,
  papel,
  senioridade,
  CAST(replace(custo_hora, ',', '.') AS DECIMAL(10, 2)) AS custo_hora,
  to_date(nullif(trim(data_admissao), ''))              AS data_admissao,
  to_date(nullif(trim(data_desligamento), ''))          AS data_desligamento
FROM ordenado
WHERE rn = 1;


CREATE OR REFRESH MATERIALIZED VIEW apontamentos
COMMENT 'Timesheet semanal: horas disponíveis e horas apontadas por pessoa e projeto. semana = a sexta-feira da semana (semana_inicio + 4), para cruzar com o status semanal e os custos.'
AS
SELECT
  colaborador_id,
  projeto_id,
  to_date(semana_inicio)                                    AS semana_inicio,
  date_add(to_date(semana_inicio), 4)                       AS semana,
  CAST(replace(horas_disponiveis, ',', '.') AS DOUBLE)      AS horas_disponiveis,
  CAST(replace(horas_apontadas, ',', '.') AS DOUBLE)        AS horas_apontadas
FROM lakehouse_vertice.bronze.apontamentos;
