-- =============================================================================
-- silver.entregas_fornecedor
-- Sujeira tratada: #15 a mesma consultoria com 4 grafias.
-- data_entrega vazia NÃO é sujeira: é entrega em aberto.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW entregas_fornecedor
COMMENT 'Entregas das consultorias contratadas: o que foi pedido, quando foi prometido e quando foi entregue. Traz o prazo prometido e o real em dias, os dias de atraso na entrega, e as flags em_aberto (sem data de entrega) e em_atraso (em aberto com a data prometida antes de 16/10/2026, o hoje do dataset). O nome da CodeForge vem normalizado; a grafia original fica em fornecedor_como_veio.'
AS
WITH tipado AS (
  SELECT
    entrega_id,
    projeto_id,
    -- #15: 'CodeForge Consultoria Ltda', 'Codeforge Consultoria',
    -- 'CODEFORGE CONSULTORIA LTDA', 'Code Forge Consultoria' → um nome só
    CASE WHEN replace(lower(fornecedor), ' ', '') LIKE '%codeforge%'
         THEN 'CodeForge Consultoria Ltda'
         ELSE fornecedor END                                 AS fornecedor,
    fornecedor                                               AS fornecedor_como_veio,
    item,
    CAST(replace(valor, ',', '.') AS DECIMAL(18, 2))         AS valor,
    to_date(nullif(trim(data_pedido), ''))                   AS data_pedido,
    to_date(nullif(trim(data_prometida), ''))                AS data_prometida,
    to_date(nullif(trim(data_entrega), ''))                  AS data_entrega,
    CAST(nullif(trim(prazo_contratado_dias), '') AS INT)     AS prazo_contratado_dias,
    status
  FROM lakehouse_vertice.bronze.entregas_fornecedor
)
SELECT
  *,
  datediff(data_prometida, data_pedido)                      AS prazo_prometido_dias,
  datediff(data_entrega, data_pedido)                        AS prazo_real_dias,
  datediff(data_entrega, data_prometida)                     AS dias_de_atraso_na_entrega,
  data_entrega IS NULL                                       AS em_aberto,
  -- "hoje" do dataset é 16/10/2026: nunca current_date()
  data_entrega IS NULL AND data_prometida < DATE'2026-10-16' AS em_atraso
FROM tipado;
