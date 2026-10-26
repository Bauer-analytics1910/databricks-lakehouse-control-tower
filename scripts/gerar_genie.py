#!/usr/bin/env python3
"""Gera o arquivo resources/farol.geniespace.json para o agente Genie Farol · Diretoria.

Uso:
  python scripts/gerar_genie.py [--profile DEFAULT] [--output resources/farol.geniespace.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys


def make_id(prefix: str, key: str) -> str:
    """Gera um ID hexadecimal determinístico de 32 caracteres (sem hífens)."""
    return hashlib.md5(f"{prefix}:{key}".encode("utf-8")).hexdigest()


def verificar_tabela_score(profile: str) -> bool:
    """Verifica se a tabela lakehouse_vertice.gold.score_estouro_30d existe no workspace."""
    cmd = [
        "databricks", "tables", "exists",
        "lakehouse_vertice.gold.score_estouro_30d",
        "--profile", profile,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        dados = json.loads(res.stdout)
        return bool(dados.get("table_exists", False))
    except Exception as e:
        print(f"Aviso ao checar score_estouro_30d ({e}), considerando inexistente.")
        return False


def construir_genie_space(tem_score: bool) -> dict:
    """Monta o payload serialized_space versão 2 conforme especificação."""
    # 1. Config: sample_questions ordenadas por id
    sample_questions_raw = [
        "Quais projetos estão atrasados, e de quais clientes?",
        "Quanto esse atraso vai me custar?",
        "Tenho gente parada enquanto outro projeto pede gente?",
        "O que vai dar errado no próximo mês?",
    ]
    if tem_score:
        sample_questions_raw.append("Qual a chance de o PRJ-024 estourar?")

    sample_questions = sorted(
        [{"id": make_id("sample", q), "question": [q]} for q in sample_questions_raw],
        key=lambda x: x["id"],
    )

    # 2. Data sources: tables e metric_views ordenadas por identifier
    # Colunas com configurações específicas ordenadas por column_name
    cols_projeto_situacao = sorted(
        [
            {"column_name": "cliente", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "farol_calculado", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "farol_do_gerente", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "ferramenta", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "segmento", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "situacao", "enable_entity_matching": True, "enable_format_assistance": True},
        ],
        key=lambda c: c["column_name"],
    )

    cols_status_estruturado = sorted(
        [
            {"column_name": "causa_bloqueio", "enable_entity_matching": True, "enable_format_assistance": True},
        ],
        key=lambda c: c["column_name"],
    )

    cols_entregas_fornecedor = sorted(
        [
            {"column_name": "fornecedor", "enable_entity_matching": True, "enable_format_assistance": True},
            {"column_name": "fornecedor_como_veio", "exclude": True},
        ],
        key=lambda c: c["column_name"],
    )

    tables_list = [
        {"identifier": "lakehouse_vertice.gold.fato_projeto_semana"},
        {
            "identifier": "lakehouse_vertice.gold.projeto_situacao_atual",
            "column_configs": cols_projeto_situacao,
        },
        {
            "identifier": "lakehouse_vertice.gold.status_estruturado",
            "column_configs": cols_status_estruturado,
        },
        {"identifier": "lakehouse_vertice.gold.utilizacao_pessoa_semana"},
        {
            "identifier": "lakehouse_vertice.silver.entregas_fornecedor",
            "column_configs": cols_entregas_fornecedor,
        },
    ]

    if tem_score:
        cols_score = sorted(
            [
                {"column_name": "faixa_risco", "enable_entity_matching": True, "enable_format_assistance": True},
            ],
            key=lambda c: c["column_name"],
        )
        tables_list.append({
            "identifier": "lakehouse_vertice.gold.score_estouro_30d",
            "column_configs": cols_score,
        })

    tables_list = sorted(tables_list, key=lambda t: t["identifier"])

    metric_views_list = sorted(
        [
            {"identifier": "lakehouse_vertice.gold.mv_projetos"},
        ],
        key=lambda m: m["identifier"],
    )

    # 3. SQL Snippets (filters) ordenados por id
    filters_list = sorted(
        [
            {
                "id": make_id("filter", "em_andamento"),
                "display_name": "Projetos em andamento",
                "sql": ["projeto_situacao_atual.status = 'em_andamento'"],
                "synonyms": ["em andamento", "ativo", "em execução"],
            },
            {
                "id": make_id("filter", "melancia"),
                "display_name": "Projetos melancia",
                "sql": ["projeto_situacao_atual.melancia"],
                "synonyms": ["melancia", "verde por fora vermelho por dentro", "farol verde atrasado"],
            },
            {
                "id": make_id("filter", "ecommerce"),
                "display_name": "Projetos de e-commerce",
                "sql": [
                    "(lower(projeto_situacao_atual.tipo_projeto) LIKE '%commerce%' OR "
                    "lower(projeto_situacao_atual.tipo_projeto) LIKE '%checkout%' OR "
                    "lower(projeto_situacao_atual.tipo_projeto) LIKE '%marketplace%')"
                ],
                "synonyms": ["e-commerce", "varejo online", "marketplace", "checkout"],
            },
            {
                "id": make_id("filter", "bloqueio_real"),
                "display_name": "Bloqueios reais",
                "sql": ["status_estruturado.causa_bloqueio NOT IN ('sem_bloqueio', 'nao_reportado')"],
                "synonyms": ["bloqueio", "travado", "impedimento"],
            },
        ],
        key=lambda x: x["id"],
    )

    # 4. Text instructions: exatamente 1 item, estruturado pelos 5 headers canônicos
    trecho_score = (
        "(3) no modelo preditivo de estouro (gold.score_estouro_30d), projetos atualmente com situacao = 'ok' "
        "mas com faixa_risco 'alto' ou 'medio' na data_referencia mais recente, indicando prob_estouro_30d e principais_fatores."
        if tem_score
        else "(3) monitoramento de projetos em atenção com SPI próximo de 0.9."
    )

    instrucoes_linhas = [
        "## PURPOSE",
        "- Responder ao dono e à diretoria da Vértice sobre os 60 projetos (41 em andamento): atrasos, custo, gente parada, fornecedores e riscos do próximo mês.",
        "- Nunca use current_date(). HOJE = 2026-10-16 (sexta-feira).",
        "",
        "## DISAMBIGUATION",
        "- Janelas temporais: 'Últimos 90 dias' = data_status >= DATE'2026-07-18'. 'Últimas 12 semanas' = semana > DATE'2026-07-24'. 'Próximo mês' = de 17/10/2026 a 16/11/2026.",
        "- Critério de atraso e criticidade: Atrasado = SPI < 0.9. Situação crítica = SPI ou CPI < 0.8. Situação de atenção = SPI ou CPI < 0.9. Demais são 'ok' ou 'concluído'.",
        "- Fórmulas EVM: SPI = EV ÷ PV. CPI = EV ÷ AC. EAC = orçamento ÷ CPI. Estouro previsto = EAC - orçamento (apenas quando positivo). Margem projetada = (valor_contrato - EAC) ÷ valor_contrato.",
        "- Farol do gerente x calculado: farol_calculado é verde (SPI >= 0.95), amarelo (SPI >= 0.90) ou vermelho (abaixo). Projeto melancia: farol_do_gerente = 'verde' E SPI < 0.9 (flag melancia = true).",
        "- Totais, médias e KPIs agregados da carteira em andamento: use sempre a metric view lakehouse_vertice.gold.mv_projetos com MEASURE(spi), MEASURE(cpi), MEASURE(estouro_previsto), MEASURE(carteira), MEASURE(projetos_em_risco), MEASURE(projetos_criticos), MEASURE(projetos_melancia), MEASURE(projetos).",
        "- Detalhe, listagens e rankings por projeto: use lakehouse_vertice.gold.projeto_situacao_atual filtrando por status = 'em_andamento'.",
        "- Código e nome do projeto: o identificador exato é projeto_id (formato PRJ-000, ex: PRJ-011). A coluna projeto traz código e nome concatenados (ex: 'PRJ-011 · Checkout...'). Para filtrar por código, use projeto_id = 'PRJ-000' ou projeto LIKE 'PRJ-000%' ou projeto = 'PRJ-000'.",
        "- Fato semanal acumulado: PV, EV e AC em fato_projeto_semana são ACUMULADOS: nunca somar semanas. Para consultar a foto de uma semana específica, filtre semana = DATE'YYYY-MM-DD'.",
        "- Gente parada e ociosidade: utilize gold.utilizacao_pessoa_semana nas últimas 12 semanas (semana > DATE'2026-07-24'). Taxa de utilização = SUM(horas_apontadas) / SUM(horas_disponiveis). Ociosidade/baixa utilização = taxa < 0.2. Para SREs, filtre papel = 'sre'.",
        "- Fornecedores: silver.entregas_fornecedor (fornecedor não tem tabela na camada gold). Fornecedor que mais atrasa entregas = ORDER BY AVG(prazo_real_dias / prazo_prometido_dias) DESC LIMIT 1. Entregas em atraso hoje = WHERE em_atraso.",
        "- 'Por que o projeto X atrasou': consulte gold.status_estruturado nos últimos 90 dias (data_status >= DATE'2026-07-18'), excluindo causas 'sem_bloqueio' e 'nao_reportado', agrupando por causa_bloqueio e ordenando por COUNT(*) DESC, mais o SPI do projeto. Se a causa for falta_sre, relacione com os SREs ociosos.",
        f"- 'O que vai dar errado no próximo mês': junte (1) entregas de fornecedores em atraso em silver.entregas_fornecedor; (2) change freeze de fim de ano no varejo (01/11/2026 a 10/01/2027) afetando projetos de e-commerce, checkout ou marketplace; {trecho_score}",
        "- E-commerce: projetos com LOWER(tipo_projeto) LIKE '%commerce%' OR LOWER(tipo_projeto) LIKE '%checkout%' OR LOWER(tipo_projeto) LIKE '%marketplace%'.",
        "- 'Quais clientes': use sempre DISTINCT cliente para retornar cada cliente uma única vez.",
        "",
        "## DATA QUALITY NOTES",
        "- Valores categóricos estão padronizados em minúsculas e sem acentos: ferramentas ('excel', 'clickup', 'msproject'), situações ('crítico', 'atenção', 'ok', 'concluído'), faixas de risco ('alto', 'medio', 'baixo').",
        "- Estornos financeiros já estão abatidos nos custos reais.",
        "",
        "## CONSTRAINTS",
        "- Use apenas as tabelas e a metric view catalogadas no espaço.",
        "- Responda com base estrita nos dados de 16/10/2026 sem extrapolações não fundamentadas.",
        "",
        "## Instructions you must follow when providing summaries",
        "- Apresente valores monetários em R$ e índices (SPI, CPI) com duas casas decimais.",
        "- Cite sempre a data de referência (16/10/2026) nos resumos executivos.",
        "- Se a resposta exigir dados não existentes nestas tabelas, declare a limitação com clareza em vez de inventar.",
    ]

    text_instructions = [
        {
            "id": make_id("text", "instrucoes_farol"),
            "content": instrucoes_linhas,
        }
    ]

    # 5. Example SQLs ordenados por id
    sql_q1 = (
        "SELECT projeto, cliente, ROUND(spi, 2) AS spi, ROUND(cpi, 2) AS cpi, situacao\n"
        "FROM lakehouse_vertice.gold.projeto_situacao_atual\n"
        "WHERE status = 'em_andamento' AND spi < 0.9\n"
        "ORDER BY spi ASC"
    )

    sql_q2 = (
        "SELECT projeto, cliente, orcamento, ROUND(eac, 2) AS eac, ROUND(estouro_previsto, 2) AS estouro_previsto, ROUND(margem_projetada, 2) AS margem_projetada\n"
        "FROM lakehouse_vertice.gold.projeto_situacao_atual\n"
        "WHERE status = 'em_andamento' AND estouro_previsto > 0\n"
        "ORDER BY estouro_previsto DESC"
    )

    sql_q3 = (
        "WITH ociosos AS (\n"
        "  SELECT colaborador_id, papel, ROUND(SUM(horas_apontadas) / SUM(horas_disponiveis), 2) AS utilizacao\n"
        "  FROM lakehouse_vertice.gold.utilizacao_pessoa_semana\n"
        "  WHERE semana > DATE'2026-07-24'\n"
        "  GROUP BY colaborador_id, papel\n"
        "  HAVING SUM(horas_apontadas) / SUM(horas_disponiveis) < 0.2\n"
        "),\n"
        "bloqueios AS (\n"
        "  SELECT projeto_id, causa_bloqueio, SUM(dias_impacto) AS dias_bloqueio\n"
        "  FROM lakehouse_vertice.gold.status_estruturado\n"
        "  WHERE data_status >= DATE'2026-07-18' AND causa_bloqueio = 'falta_sre'\n"
        "  GROUP BY projeto_id, causa_bloqueio\n"
        ")\n"
        "SELECT o.colaborador_id, o.papel, o.utilizacao, b.projeto_id AS projeto_bloqueado, b.dias_bloqueio\n"
        "FROM ociosos o\n"
        "FULL OUTER JOIN bloqueios b ON o.papel = 'sre'"
    )

    if tem_score:
        sql_q4 = (
            "SELECT 'entregas_fornecedor_atraso' AS tipo_risco,\n"
            "       fornecedor AS entidade,\n"
            "       CONCAT('Entrega atrasada: prazo real ', prazo_real_dias, ' vs prometido ', prazo_prometido_dias) AS detalhe\n"
            "FROM lakehouse_vertice.silver.entregas_fornecedor\n"
            "WHERE em_atraso\n"
            "UNION ALL\n"
            "SELECT 'change_freeze_black_friday' AS tipo_risco,\n"
            "       projeto AS entidade,\n"
            "       'Projeto de e-commerce congelado entre 01/11/2026 e 10/01/2027' AS detalhe\n"
            "FROM lakehouse_vertice.gold.projeto_situacao_atual\n"
            "WHERE status = 'em_andamento' AND (LOWER(tipo_projeto) LIKE '%commerce%' OR LOWER(tipo_projeto) LIKE '%checkout%' OR LOWER(tipo_projeto) LIKE '%marketplace%')\n"
            "UNION ALL\n"
            "SELECT 'risco_estouro_score' AS tipo_risco,\n"
            "       p.projeto AS entidade,\n"
            "       CONCAT('P(estouro)=', ROUND(s.prob_estouro_30d * 100, 0), '%, fatores: ', s.principais_fatores) AS detalhe\n"
            "FROM lakehouse_vertice.gold.score_estouro_30d s\n"
            "JOIN lakehouse_vertice.gold.projeto_situacao_atual p USING (projeto_id)\n"
            "WHERE s.data_referencia = (SELECT MAX(data_referencia) FROM lakehouse_vertice.gold.score_estouro_30d)\n"
            "  AND p.situacao = 'ok' AND s.faixa_risco IN ('alto', 'medio')"
        )
    else:
        sql_q4 = (
            "SELECT 'entregas_fornecedor_atraso' AS tipo_risco,\n"
            "       fornecedor AS entidade,\n"
            "       CONCAT('Entrega atrasada: prazo real ', prazo_real_dias, ' vs prometido ', prazo_prometido_dias) AS detalhe\n"
            "FROM lakehouse_vertice.silver.entregas_fornecedor\n"
            "WHERE em_atraso\n"
            "UNION ALL\n"
            "SELECT 'change_freeze_black_friday' AS tipo_risco,\n"
            "       projeto AS entidade,\n"
            "       'Projeto de e-commerce congelado entre 01/11/2026 e 10/01/2027' AS detalhe\n"
            "FROM lakehouse_vertice.gold.projeto_situacao_atual\n"
            "WHERE status = 'em_andamento' AND (LOWER(tipo_projeto) LIKE '%commerce%' OR LOWER(tipo_projeto) LIKE '%checkout%' OR LOWER(tipo_projeto) LIKE '%marketplace%')"
        )

    examples_raw = [
        ("Quais projetos estão atrasados, e de quais clientes?", sql_q1),
        ("Quanto esse atraso vai me custar?", sql_q2),
        ("Tenho gente parada enquanto outro projeto pede gente?", sql_q3),
        ("O que vai dar errado no próximo mês?", sql_q4),
    ]

    if tem_score:
        sql_q5 = (
            "SELECT s.projeto_id, p.projeto, ROUND(s.prob_estouro_30d * 100, 1) AS prob_estouro_pct, s.faixa_risco, s.principais_fatores\n"
            "FROM lakehouse_vertice.gold.score_estouro_30d s\n"
            "JOIN lakehouse_vertice.gold.projeto_situacao_atual p USING (projeto_id)\n"
            "WHERE s.projeto_id = 'PRJ-024'\n"
            "  AND s.data_referencia = (SELECT MAX(data_referencia) FROM lakehouse_vertice.gold.score_estouro_30d)"
        )
        examples_raw.append(("Qual a chance de o PRJ-024 estourar?", sql_q5))

    example_question_sqls = sorted(
        [
            {
                "id": make_id("example", q),
                "question": [q],
                "sql": [sql],
            }
            for q, sql in examples_raw
        ],
        key=lambda x: x["id"],
    )

    payload = {
        "version": 2,
        "config": {
            "sample_questions": sample_questions,
        },
        "data_sources": {
            "tables": tables_list,
            "metric_views": metric_views_list,
        },
        "instructions": {
            "example_question_sqls": example_question_sqls,
            "sql_snippets": {
                "filters": filters_list,
            },
            "text_instructions": text_instructions,
        },
    }

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera o JSON do serialized_space do Genie.")
    parser.add_argument("--profile", default="DEFAULT", help="Perfil Databricks CLI")
    parser.add_argument("--output", default="resources/farol.geniespace.json", help="Arquivo JSON de saída")
    args = parser.parse_args()

    tem_score = verificar_tabela_score(args.profile)
    print(f"Verificação de score_estouro_30d: {'presente' if tem_score else 'ausente'}")

    payload = construir_genie_space(tem_score)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Arquivo gerado com sucesso: {args.output}")
    print(f"Tabelas incluídas: {len(payload['data_sources']['tables'])}")
    print(f"Metric views incluídas: {len(payload['data_sources']['metric_views'])}")
    print(f"Exemplos de SQL: {len(payload['instructions']['example_question_sqls'])}")
    print(f"Perguntas de amostra: {len(payload['config']['sample_questions'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
