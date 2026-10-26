-- Projetos em andamento do pior para o melhor, com métricas, causa frequente e impacto
WITH causas_90d AS (
  SELECT
    projeto_id,
    causa_bloqueio,
    count(*) AS frequencia,
    row_number() OVER (
      PARTITION BY projeto_id
      ORDER BY
        CASE WHEN causa_bloqueio IN ('sem_bloqueio', 'nao_reportado') THEN 1 ELSE 0 END,
        count(*) DESC
    ) AS rn
  FROM lakehouse_vertice.gold.status_estruturado
  WHERE data_status >= date_sub(DATE'2026-10-16', 90)
    AND data_status <= DATE'2026-10-16'
  GROUP BY projeto_id, causa_bloqueio
),
impactos_90d AS (
  SELECT
    projeto_id,
    sum(CASE WHEN causa_bloqueio = 'falta_sre' THEN coalesce(dias_impacto, 0) ELSE 0 END)    AS dias_falta_sre,
    sum(CASE WHEN causa_bloqueio = 'rotatividade' THEN coalesce(dias_impacto, 0) ELSE 0 END) AS dias_rotatividade
  FROM lakehouse_vertice.gold.status_estruturado
  WHERE data_status >= date_sub(DATE'2026-10-16', 90)
    AND data_status <= DATE'2026-10-16'
  GROUP BY projeto_id
)
SELECT
  p.projeto_id,
  p.projeto,
  p.nome_projeto,
  p.cliente,
  p.segmento,
  p.gerente_projeto,
  p.valor_contrato,
  p.orcamento,
  p.spi,
  p.cpi,
  p.eac,
  p.estouro_previsto,
  p.atraso_projetado_dias,
  p.situacao,
  p.farol_do_gerente,
  p.farol_calculado,
  p.melancia,
  coalesce(c.causa_bloqueio, 'sem_bloqueio') AS causa_mais_frequente,
  coalesce(i.dias_falta_sre, 0.0)             AS dias_impacto_falta_sre,
  coalesce(i.dias_rotatividade, 0.0)          AS dias_impacto_rotatividade
FROM lakehouse_vertice.gold.projeto_situacao_atual p
LEFT JOIN causas_90d c
  ON c.projeto_id = p.projeto_id AND c.rn = 1
LEFT JOIN impactos_90d i
  ON i.projeto_id = p.projeto_id
WHERE p.status = 'em_andamento'
ORDER BY
  CASE p.situacao WHEN 'crítico' THEN 1 WHEN 'atenção' THEN 2 ELSE 3 END,
  p.spi ASC,
  p.cpi ASC,
  p.estouro_previsto DESC
