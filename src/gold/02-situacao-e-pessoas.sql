-- =============================================================================
-- gold.projeto_situacao_atual e gold.utilizacao_pessoa_semana
-- Fotografia em 2026-10-16 e análise de alocação de pessoas.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW lakehouse_vertice.gold.projeto_situacao_atual
COMMENT 'Fotografia em 16/10/2026 de cada um dos 60 projetos da Vértice. Consolida o cadastro com os KPIs calculados sobre silver.tarefas (cronograma de hoje): PV, EV, AC, SPI, CPI, EAC, estouro previsto, margem, atraso projetado, farol do gerente, farol calculado e flag melancia.'
AS
WITH tarefas_kpi AS (
  SELECT
    t.projeto_id,
    sum(t.horas)                                                      AS total_horas,
    sum(
      t.horas * (coalesce(t.pct_concluido, 0.0) / 100.0)
    )                                                                 AS total_horas_agregadas,
    sum(
      t.horas * (
        CASE
          WHEN t.fim_baseline IS NULL OR t.inicio_baseline IS NULL THEN 1.0
          WHEN datediff(t.fim_baseline, t.inicio_baseline) <= 0   THEN 1.0
          ELSE greatest(
            0.0,
            least(
              1.0,
              CAST(datediff(DATE'2026-10-16', t.inicio_baseline) AS DOUBLE) /
              nullif(CAST(datediff(t.fim_baseline, t.inicio_baseline) AS DOUBLE), 0)
            )
          )
        END
      )
    )                                                                 AS total_horas_baseline
  FROM tarefas t
  GROUP BY t.projeto_id
),
custos_hoje AS (
  SELECT
    projeto_id,
    sum(valor) AS ac
  FROM custos
  WHERE data <= DATE'2026-10-16'
  GROUP BY projeto_id
),
ult_status AS (
  SELECT
    projeto_id,
    farol AS farol_do_gerente,
    row_number() OVER (PARTITION BY projeto_id ORDER BY data_status DESC) AS rn
  FROM status_semanal
  WHERE data_status <= DATE'2026-10-16'
),
status_atual AS (
  SELECT
    projeto_id,
    farol_do_gerente
  FROM ult_status
  WHERE rn = 1
),
consolidado AS (
  SELECT
    p.projeto_id,
    concat(p.projeto_id, ' · ', p.nome_projeto)                       AS projeto,
    p.nome_projeto,
    p.cliente,
    p.segmento,
    p.tipo_projeto,
    p.ferramenta,
    p.gerente_projeto,
    p.valor_contrato,
    p.orcamento_custo                                                 AS orcamento,
    p.data_inicio,
    p.data_fim_baseline,
    datediff(p.data_fim_baseline, p.data_inicio)                      AS duracao_baseline_dias,
    p.status,
    -- PV: orcamento * fracao horas baseline decorridas
    round(
      p.orcamento_custo * (
        coalesce(tk.total_horas_baseline, 0.0) / nullif(tk.total_horas, 0)
      ),
      2
    )                                                                 AS pv,
    -- EV: orcamento * fracao horas agregadas concluidas
    round(
      p.orcamento_custo * (
        coalesce(tk.total_horas_agregadas, 0.0) / nullif(tk.total_horas, 0)
      ),
      2
    )                                                                 AS ev,
    -- AC: soma dos custos ate 16/10/2026
    round(coalesce(c.ac, 0.0), 2)                                     AS ac,
    s.farol_do_gerente
  FROM projetos p
  LEFT JOIN tarefas_kpi tk
    ON tk.projeto_id = p.projeto_id
  LEFT JOIN custos_hoje c
    ON c.projeto_id = p.projeto_id
  LEFT JOIN status_atual s
    ON s.projeto_id = p.projeto_id
),
com_indices AS (
  SELECT
    *,
    round(try_divide(ev, pv), 4)                    AS spi,
    round(try_divide(ev, ac), 4)                    AS cpi,
    round(try_divide(orcamento, try_divide(ev, ac)), 2) AS eac
  FROM consolidado
)
SELECT
  projeto_id,
  projeto,
  nome_projeto,
  cliente,
  segmento,
  tipo_projeto,
  ferramenta,
  gerente_projeto,
  valor_contrato,
  orcamento,
  data_inicio,
  data_fim_baseline,
  duracao_baseline_dias,
  status,
  pv,
  ev,
  ac,
  spi,
  cpi,
  eac,
  greatest(eac - orcamento, 0.0)                                       AS estouro_previsto,
  round(try_divide(valor_contrato - eac, valor_contrato), 4)           AS margem_projetada,
  round(duracao_baseline_dias / nullif(spi, 0) - duracao_baseline_dias) AS atraso_projetado_dias,
  date_add(data_inicio, CAST(round(duracao_baseline_dias / nullif(spi, 0)) AS INT)) AS termino_projetado,
  CASE
    WHEN status <> 'em_andamento' THEN 'concluído'
    WHEN spi < 0.8 OR cpi < 0.8  THEN 'crítico'
    WHEN spi < 0.9 OR cpi < 0.9  THEN 'atenção'
    ELSE 'ok'
  END                                                                  AS situacao,
  farol_do_gerente,
  CASE
    WHEN spi >= 0.95 THEN 'verde'
    WHEN spi >= 0.90 THEN 'amarelo'
    ELSE 'vermelho'
  END                                                                  AS farol_calculado,
  status = 'em_andamento'
    AND coalesce(farol_do_gerente, '') = 'verde'
    AND spi < 0.9                                                      AS melancia
FROM com_indices;


-- =============================================================================
-- gold.utilizacao_pessoa_semana
-- Pessoa x Projeto x Semana com horas disponiveis, apontadas, ociosas, custo
-- e SPI do projeto na semana correspondente.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW lakehouse_vertice.gold.utilizacao_pessoa_semana
COMMENT 'Utilização semanal por pessoa e projeto: horas disponíveis, apontadas, ociosas, taxa de utilização, custo ocioso e o SPI do projeto naquela semana. Permite identificar colaboradores ociosos enquanto projetos pedem recursos.'
AS
SELECT
  a.colaborador_id,
  c.nome,
  c.papel,
  c.senioridade,
  a.projeto_id,
  a.semana,
  a.horas_disponiveis,
  a.horas_apontadas,
  greatest(0.0, a.horas_disponiveis - a.horas_apontadas)               AS horas_ociosas,
  round(try_divide(a.horas_apontadas, a.horas_disponiveis), 4)        AS utilizacao,
  round(
    greatest(0.0, a.horas_disponiveis - a.horas_apontadas) * c.custo_hora,
    2
  )                                                                    AS custo_ocioso,
  f.spi                                                                AS spi_do_projeto
FROM apontamentos a
JOIN colaboradores c
  ON c.colaborador_id = a.colaborador_id
LEFT JOIN lakehouse_vertice.gold.fato_projeto_semana f
  ON f.projeto_id = a.projeto_id AND f.semana = a.semana;
