-- =============================================================================
-- gold.fato_projeto_semana
-- Evolução semanal (toda sexta-feira) dos 60 projetos da Vértice.
-- Cobre da semana de início de cada projeto até 2026-10-16.
-- Colunas de Valor Agregado: PV, EV, AC, SPI, CPI, EAC, farol e timesheet.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW lakehouse_vertice.gold.fato_projeto_semana (
  CONSTRAINT pv_positivo EXPECT (pv >= 0) ON VIOLATION FAIL UPDATE,
  CONSTRAINT ev_valido   EXPECT (ev <= orcamento) ON VIOLATION FAIL UPDATE
)
COMMENT 'Evolução semanal dos 60 projetos (toda sexta-feira): Planned Value (PV), Earned Value (EV), Actual Cost (AC), SPI, CPI, EAC, farol do gerente e horas de timesheet. Histórico completo da data de início até 16/10/2026.'
AS
WITH grid_semanas AS (
  SELECT
    p.projeto_id,
    p.orcamento_custo AS orcamento,
    p.data_inicio,
    p.data_fim_baseline,
    explode(
      sequence(
        date_add(CAST(date_trunc('WEEK', p.data_inicio) AS DATE), 4),
        DATE'2026-10-16',
        INTERVAL 1 WEEK
      )
    ) AS semana
  FROM projetos p
),
custos_semana AS (
  SELECT
    projeto_id,
    semana,
    sum(valor) AS custo_semana
  FROM custos
  GROUP BY projeto_id, semana
),
apontamentos_semana AS (
  SELECT
    projeto_id,
    semana,
    sum(horas_disponiveis) AS horas_disponiveis,
    sum(horas_apontadas)   AS horas_apontadas
  FROM apontamentos
  GROUP BY projeto_id, semana
),
status_semana AS (
  SELECT
    projeto_id,
    data_status AS semana,
    pct_concluido,
    farol
  FROM status_semanal
),
metricas_base AS (
  SELECT
    g.projeto_id,
    g.semana,
    g.orcamento,
    g.data_inicio,
    g.data_fim_baseline,
    -- Fração do baseline decorrida até a semana
    greatest(
      0.0,
      least(
        1.0,
        CAST(datediff(g.semana, g.data_inicio) AS DOUBLE) /
        nullif(CAST(datediff(g.data_fim_baseline, g.data_inicio) AS DOUBLE), 0)
      )
    ) AS fracao_baseline,
    -- Último % concluído publicado até a semana (projeto concluído não publica mais)
    last_value(s.pct_concluido, true) OVER (
      PARTITION BY g.projeto_id
      ORDER BY g.semana
    ) AS pct_concluido_efetivo,
    -- Último farol publicado até a semana
    last_value(s.farol, true) OVER (
      PARTITION BY g.projeto_id
      ORDER BY g.semana
    ) AS farol_do_gerente,
    -- Custo real acumulado da semana (AC)
    sum(coalesce(c.custo_semana, 0.0)) OVER (
      PARTITION BY g.projeto_id
      ORDER BY g.semana
    ) AS ac_acumulado,
    -- Horas do timesheet
    coalesce(a.horas_disponiveis, 0.0) AS horas_disponiveis,
    coalesce(a.horas_apontadas, 0.0)   AS horas_apontadas
  FROM grid_semanas g
  LEFT JOIN custos_semana c
    ON c.projeto_id = g.projeto_id AND c.semana = g.semana
  LEFT JOIN apontamentos_semana a
    ON a.projeto_id = g.projeto_id AND a.semana = g.semana
  LEFT JOIN status_semana s
    ON s.projeto_id = g.projeto_id AND s.semana = g.semana
),
calculado AS (
  SELECT
    projeto_id,
    semana,
    orcamento,
    -- PV: orçamento * fração do baseline
    round(orcamento * fracao_baseline, 2) AS pv,
    -- EV: orçamento * % concluído declarado / 100
    round(orcamento * (coalesce(pct_concluido_efetivo, 0) / 100.0), 2) AS ev,
    -- AC: custo real acumulado
    round(ac_acumulado, 2) AS ac,
    farol_do_gerente,
    horas_disponiveis,
    horas_apontadas,
    greatest(0.0, horas_disponiveis - horas_apontadas) AS horas_ociosas
  FROM metricas_base
)
SELECT
  projeto_id,
  semana,
  orcamento,
  pv,
  ev,
  ac,
  round(try_divide(ev, pv), 4)                    AS spi,
  round(try_divide(ev, ac), 4)                    AS cpi,
  round(try_divide(orcamento, try_divide(ev, ac)), 2) AS eac,
  farol_do_gerente,
  horas_disponiveis,
  horas_apontadas,
  horas_ociosas
FROM calculado;
