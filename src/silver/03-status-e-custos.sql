-- =============================================================================
-- silver.status_semanal e silver.custos
-- Sujeiras tratadas: #13 vírgula decimal, #14 estorno, #17 farol, #18 status vazio.
-- =============================================================================

CREATE OR REFRESH MATERIALIZED VIEW status_semanal (
  CONSTRAINT farol_valido EXPECT (farol IN ('verde', 'amarelo', 'vermelho')) ON VIOLATION FAIL UPDATE
)
COMMENT 'Status semanal que cada gerente reporta toda sexta: data do status, farol do gerente (verde, amarelo, vermelho), % concluído declarado e o texto livre com os bloqueios. É o histórico do avanço de cada projeto. Status vazios não são descartados: ficam marcados em status_vazio.'
AS
SELECT
  projeto_id,
  to_date(data_status)                                         AS data_status,
  gerente,
  -- #17: 'Verde', 'VERDE', ' verde ' → 'verde'
  lower(trim(farol))                                           AS farol,
  CAST(CAST(replace(pct_concluido, ',', '.') AS DOUBLE) AS INT) AS pct_concluido,
  texto_status,
  -- #18: texto vazio, 'N/A' ou 'ver ata da reunião' — marca, NÃO descarta
  coalesce(trim(texto_status), '') IN ('', 'N/A', 'ver ata da reunião') AS status_vazio
FROM lakehouse_vertice.bronze.status_semanal;


CREATE OR REFRESH MATERIALIZED VIEW custos
COMMENT 'Lançamentos de custo real dos projetos (pessoal, consultoria, cloud, licenças, despesas), com valor em reais já convertido de vírgula decimal. Estornos (valor negativo) ficam, porque o custo é líquido, e são marcados em estorno. semana = a sexta-feira da semana do lançamento, para cruzar com o status semanal.'
AS
SELECT
  lancamento_id,
  projeto_id,
  to_date(data)                                                AS data,
  -- semana termina na sexta: segunda (date_trunc WEEK) + 4 dias
  date_add(CAST(date_trunc('WEEK', to_date(data)) AS DATE), 4) AS semana,
  categoria,
  descricao,
  -- #13: '12345,67' → 12345.67. replace ANTES do CAST; nunca try_cast
  -- (try_cast jogaria R$ 5,4 mi fora em silêncio)
  CAST(replace(valor, ',', '.') AS DECIMAL(18, 2))             AS valor,
  -- #14: estorno é valor negativo: FICA, só sinalizado
  CAST(replace(valor, ',', '.') AS DECIMAL(18, 2)) < 0         AS estorno,
  centro_custo
FROM lakehouse_vertice.bronze.custos;
