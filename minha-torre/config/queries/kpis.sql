-- KPIs da carteira e projetos em risco (sem dependência do score ML)
SELECT
  count_if(status = 'em_andamento')                                                      AS projetos_em_andamento,
  count_if(status = 'em_andamento' AND situacao IN ('crítico', 'atenção'))               AS em_risco,
  count_if(status = 'em_andamento' AND situacao = 'crítico')                             AS criticos,
  count_if(status = 'em_andamento' AND melancia = true)                                  AS melancias,
  round(coalesce(sum(CASE WHEN status = 'em_andamento' THEN estouro_previsto ELSE 0 END), 0.0), 2) AS estouro_previsto,
  round(coalesce(sum(CASE WHEN status = 'em_andamento' THEN valor_contrato ELSE 0 END), 0.0), 2)   AS carteira
FROM lakehouse_vertice.gold.projeto_situacao_atual
