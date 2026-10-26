-- Métricas governadas do Projeto Farol: a fórmula de cada KPI mora aqui, uma vez só.
-- HOJE do dataset = 2026-10-16. Nunca use current_date().
-- ATENÇÃO: nada de ponto e vírgula dentro do YAML (nem em comentário). Só o último.
CREATE OR REPLACE VIEW lakehouse_vertice.gold.mv_projetos
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
comment: "Métricas governadas da carteira de projetos em andamento (SPI, CPI, EAC, estouro, margem, riscos). Fonte única das fórmulas."
source: lakehouse_vertice.gold.projeto_situacao_atual
filter: status = 'em_andamento'

dimensions:
  - name: projeto_id
    expr: projeto_id
    comment: "Código do projeto, no formato PRJ-000"
    synonyms: ["código do projeto", "id do projeto", "PRJ"]
  - name: projeto
    expr: projeto
    comment: "Código e nome do projeto juntos"
    synonyms: ["obra", "nome do projeto"]
  - name: cliente
    expr: cliente
    synonyms: ["conta", "empresa"]
  - name: segmento
    expr: segmento
    comment: "varejo, financeiro, saude, logistica ou industria"
    synonyms: ["setor", "vertical"]
  - name: ferramenta
    expr: ferramenta
    comment: "Onde o gerente controla o projeto: excel, clickup ou msproject"
    synonyms: ["ferramenta de gestão", "sistema"]
  - name: situacao
    expr: situacao
    comment: "Regra de corte: crítico se SPI ou CPI < 0,8. atenção se < 0,9. senão ok"
    synonyms: ["status do risco", "criticidade"]
  - name: farol_do_gerente
    expr: farol_do_gerente
    comment: "Farol que o gerente publicou no último status (verde, amarelo, vermelho)"
    synonyms: ["farol informado", "farol do gerente de projeto"]
  - name: farol_calculado
    expr: farol_calculado
    comment: "Farol pela regra do manual da Vértice: verde com SPI >= 0,95. amarelo >= 0,90. vermelho abaixo"
    synonyms: ["farol real", "farol da regra"]
  - name: gerente_projeto
    expr: gerente_projeto
    synonyms: ["gerente", "GP"]

measures:
  - name: projetos
    expr: COUNT(1)
    synonyms: ["quantidade de projetos", "número de projetos"]
  - name: carteira
    expr: SUM(valor_contrato)
    comment: "Soma do valor dos contratos em R$"
    synonyms: ["valor da carteira", "valor dos contratos", "receita contratada"]
  - name: spi
    expr: SUM(ev) / SUM(pv)
    comment: "Índice de prazo da carteira = valor agregado (EV) ÷ valor planejado (PV). Abaixo de 1 é atraso"
    synonyms: ["índice de prazo", "schedule performance index"]
  - name: cpi
    expr: SUM(ev) / SUM(ac)
    comment: "Índice de custo da carteira = EV ÷ custo real (AC). Abaixo de 1 é estouro"
    synonyms: ["índice de custo", "cost performance index"]
  - name: eac
    expr: SUM(eac)
    comment: "Estimativa no término = orçamento ÷ CPI de cada projeto, somada"
    synonyms: ["custo estimado no término", "estimativa no término"]
  - name: estouro_previsto
    expr: SUM(estouro_previsto)
    comment: "EAC menos orçamento, só quando positivo, em R$"
    synonyms: ["estouro", "quanto vai estourar", "sobrecusto previsto"]
  - name: margem_projetada
    expr: (SUM(valor_contrato) - SUM(eac)) / SUM(valor_contrato)
    comment: "(valor do contrato - EAC) ÷ valor do contrato"
    synonyms: ["margem", "margem prevista"]
  - name: atraso_projetado_medio_dias
    expr: AVG(atraso_projetado_dias)
    comment: "Média de (duração baseline ÷ SPI - duração baseline) por projeto"
    synonyms: ["atraso médio", "atraso previsto em dias"]
  - name: projetos_em_risco
    expr: COUNT(1) FILTER (WHERE situacao IN ('atenção', 'crítico'))
    comment: "Projetos em atenção ou críticos"
  - name: projetos_criticos
    expr: COUNT(1) FILTER (WHERE situacao = 'crítico')
    synonyms: ["críticos"]
  - name: projetos_melancia
    expr: COUNT(1) FILTER (WHERE melancia)
    comment: "Melancia = farol do gerente verde mas SPI < 0,9. Verde por fora, vermelho por dentro"
    synonyms: ["melancias", "farol verde atrasado"]
$$;
