-- Colaboradores com utilização média < 20% nas últimas 12 semanas
SELECT
  u.colaborador_id,
  u.nome,
  u.papel,
  u.senioridade,
  u.projeto_id                                       AS projeto_atual,
  round(avg(u.utilizacao), 4)                        AS utilizacao_media,
  round(avg(u.horas_ociosas), 2)                     AS media_horas_ociosas_semana,
  round(avg(u.custo_ocioso), 2)                      AS media_custo_ocioso_semana,
  c.custo_hora
FROM lakehouse_vertice.gold.utilizacao_pessoa_semana u
JOIN lakehouse_vertice.silver.colaboradores c
  ON c.colaborador_id = u.colaborador_id
WHERE u.semana > date_sub(DATE'2026-10-16', 84)
  AND u.semana <= DATE'2026-10-16'
GROUP BY
  u.colaborador_id,
  u.nome,
  u.papel,
  u.senioridade,
  u.projeto_id,
  c.custo_hora
HAVING avg(u.utilizacao) < 0.20
ORDER BY utilizacao_media ASC
