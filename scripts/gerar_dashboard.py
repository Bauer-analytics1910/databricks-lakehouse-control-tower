#!/usr/bin/env python3
"""Gera o arquivo resources/dashboard-portfolio.lvdash.json para o Databricks Asset Bundle (DAB).

Dashboard AI/BI executivo do Projeto Farol (Vértice Tecnologia) com 3 páginas:
  1. Portfólio & Risco: KPIs gerais, situação, ranking de ML de estouro em 30d e tabela detalhada.
  2. Pessoas & Alocação: horas ociosas, taxa de utilização e causas de bloqueio estruturadas por IA.
  3. Fornecedores & Entregas: acompanhamento de entregas de consultoria, prazos prometidos vs reais e atrasos.

Uso:
  python scripts/gerar_dashboard.py
"""

import json
from pathlib import Path


def construir_dashboard():
    # Paleta de cores e tema seguindo a regra 60/30/10 do Databricks AI/BI
    ui_settings = {
        "theme": {
            "canvasBackgroundColor": {"light": "#F8F9FA", "dark": "#1A1D20"},
            "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#212529"},
            "fontColor": {"light": "#212529", "dark": "#F8F9FA"},
            "selectionColor": {"light": "#0B5ED7", "dark": "#3D8BFD"},
            "visualizationColors": [
                "#0D6EFD",  # Azul principal
                "#198754",  # Verde (sucesso)
                "#FFC107",  # Amarelo (atenção)
                "#DC3545",  # Vermelho (crítico)
                "#0DCAF0",  # Ciano
                "#6F42C1",  # Roxo
                "#FD7E14",  # Laranja
            ],
            "widgetHeaderAlignment": "LEFT",
        }
    }

    # Datasets (utilizam nomes simples de tabela no schema padrão 'gold' do bundle)
    datasets = [
        {
            "name": "ds_portfolio",
            "displayName": "Situação dos Projetos",
            "queryLines": [
                "SELECT\n",
                "  projeto_id,\n",
                "  projeto,\n",
                "  nome_projeto,\n",
                "  cliente,\n",
                "  segmento,\n",
                "  tipo_projeto,\n",
                "  ferramenta,\n",
                "  gerente_projeto,\n",
                "  valor_contrato,\n",
                "  orcamento,\n",
                "  data_inicio,\n",
                "  data_fim_baseline,\n",
                "  duracao_baseline_dias,\n",
                "  status,\n",
                "  pv,\n",
                "  ev,\n",
                "  ac,\n",
                "  spi,\n",
                "  cpi,\n",
                "  eac,\n",
                "  estouro_previsto,\n",
                "  margem_projetada,\n",
                "  atraso_projetado_dias,\n",
                "  situacao,\n",
                "  farol_do_gerente,\n",
                "  farol_calculado,\n",
                "  melancia,\n",
                "  CASE WHEN melancia THEN 1 ELSE 0 END AS melancia_flag,\n",
                "  CASE WHEN status = 'em_andamento' THEN 1 ELSE 0 END AS em_andamento_flag\n",
                "FROM projeto_situacao_atual\n",
            ],
        },
        {
            "name": "ds_ml_score",
            "displayName": "Risco de Estouro (ML)",
            "queryLines": [
                "SELECT\n",
                "  s.projeto_id,\n",
                "  p.nome_projeto,\n",
                "  p.cliente,\n",
                "  p.segmento,\n",
                "  p.gerente_projeto,\n",
                "  s.data_referencia,\n",
                "  s.prob_estouro_30d,\n",
                "  s.ranking,\n",
                "  s.faixa_risco,\n",
                "  s.principais_fatores,\n",
                "  p.spi,\n",
                "  p.cpi,\n",
                "  p.estouro_previsto\n",
                "FROM score_estouro_30d s\n",
                "JOIN projeto_situacao_atual p USING (projeto_id)\n",
                "ORDER BY s.ranking ASC\n",
            ],
        },
        {
            "name": "ds_pessoas",
            "displayName": "Utilização e Pessoas",
            "queryLines": [
                "SELECT\n",
                "  colaborador_id,\n",
                "  nome,\n",
                "  papel,\n",
                "  senioridade,\n",
                "  projeto_id,\n",
                "  semana,\n",
                "  horas_disponiveis,\n",
                "  horas_apontadas,\n",
                "  horas_ociosas,\n",
                "  utilizacao,\n",
                "  custo_ocioso,\n",
                "  spi_do_projeto\n",
                "FROM utilizacao_pessoa_semana\n",
            ],
        },
        {
            "name": "ds_status_ia",
            "displayName": "Status Estruturado por IA",
            "queryLines": [
                "SELECT\n",
                "  projeto_id,\n",
                "  data_status,\n",
                "  farol,\n",
                "  causa_bloqueio,\n",
                "  bloqueio,\n",
                "  quem_destrava,\n",
                "  dias_impacto,\n",
                "  metodo,\n",
                "  texto_status\n",
                "FROM status_estruturado\n",
            ],
        },
        {
            "name": "ds_fornecedores",
            "displayName": "Entregas de Fornecedores",
            "queryLines": [
                "SELECT\n",
                "  entrega_id,\n",
                "  projeto_id,\n",
                "  fornecedor,\n",
                "  item,\n",
                "  valor,\n",
                "  data_pedido,\n",
                "  data_prometida,\n",
                "  data_entrega,\n",
                "  prazo_contratado_dias,\n",
                "  prazo_prometido_dias,\n",
                "  prazo_real_dias,\n",
                "  dias_de_atraso_na_entrega,\n",
                "  em_aberto,\n",
                "  em_atraso,\n",
                "  CASE WHEN em_atraso THEN 1 ELSE 0 END AS em_atraso_flag,\n",
                "  status\n",
                "FROM lakehouse_vertice.silver.entregas_fornecedor\n",
            ],
        },
    ]

    # Página 1: Portfólio & Risco
    p1_layout = [
        # Cabeçalho
        {
            "widget": {
                "name": "header_portfolio",
                "multilineTextboxSpec": {
                    "lines": [
                        "# Projeto Farol · Portfólio de Projetos\n",
                        "\n",
                        "Visão consolidada dos 60 projetos da Vértice Tecnologia: SPI, CPI, estouro financeiro previsto e predição de risco em 30 dias.",
                    ]
                },
            },
            "position": {"x": 0, "y": 0, "width": 12, "height": 2},
        },
        # 4 KPIs no topo
        {
            "widget": {
                "name": "kpi_estouro_total",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [
                                {
                                    "name": "sum(estouro_previsto)",
                                    "expression": "SUM(`estouro_previsto`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(estouro_previsto)",
                            "displayName": "Estouro Previsto",
                            "format": {
                                "type": "number-currency",
                                "currencyCode": "BRL",
                                "abbreviation": "compact",
                                "decimalPlaces": {"type": "max", "places": 2},
                            },
                        }
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Estouro Previsto (EAC - Orç)",
                    },
                },
            },
            "position": {"x": 0, "y": 2, "width": 3, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_spi_carteira",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [{"name": "avg(spi)", "expression": "AVG(`spi`)"}],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "avg(spi)",
                            "displayName": "SPI Médio",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 2},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "SPI Médio da Carteira"},
                },
            },
            "position": {"x": 3, "y": 2, "width": 3, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_cpi_carteira",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [{"name": "avg(cpi)", "expression": "AVG(`cpi`)"}],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "avg(cpi)",
                            "displayName": "CPI Médio",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 2},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "CPI Médio da Carteira"},
                },
            },
            "position": {"x": 6, "y": 2, "width": 3, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_melancias",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [
                                {
                                    "name": "sum(melancia_flag)",
                                    "expression": "SUM(`melancia_flag`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(melancia_flag)",
                            "displayName": "Projetos Melancia",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 0},
                            },
                        }
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Melancias (Farol Verde & SPI < 0.9)",
                    },
                },
            },
            "position": {"x": 9, "y": 2, "width": 3, "height": 3},
        },
        # Gráficos
        {
            "widget": {
                "name": "chart_projetos_situacao",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [
                                {
                                    "name": "situacao",
                                    "expression": "`situacao`",
                                },
                                {
                                    "name": "count(projeto_id)",
                                    "expression": "COUNT(`projeto_id`)",
                                },
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 3,
                    "widgetType": "bar",
                    "encodings": {
                        "x": {
                            "fieldName": "situacao",
                            "scale": {"type": "categorical"},
                            "displayName": "Situação do Projeto",
                        },
                        "y": {
                            "fieldName": "count(projeto_id)",
                            "scale": {"type": "quantitative"},
                            "displayName": "Total de Projetos",
                        },
                        "color": {
                            "fieldName": "situacao",
                            "scale": {"type": "categorical"},
                        },
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Distribuição dos Projetos por Situação",
                    },
                },
            },
            "position": {"x": 0, "y": 5, "width": 6, "height": 6},
        },
        {
            "widget": {
                "name": "chart_ml_risco_estouro",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_ml_score",
                            "fields": [
                                {
                                    "name": "nome_projeto",
                                    "expression": "`nome_projeto`",
                                },
                                {
                                    "name": "prob_estouro_30d",
                                    "expression": "`prob_estouro_30d`",
                                },
                                {
                                    "name": "faixa_risco",
                                    "expression": "`faixa_risco`",
                                },
                            ],
                            "disaggregated": True,
                        },
                    }
                ],
                "spec": {
                    "version": 3,
                    "widgetType": "bar",
                    "encodings": {
                        "x": {
                            "fieldName": "prob_estouro_30d",
                            "scale": {"type": "quantitative"},
                            "displayName": "Probabilidade de Estouro",
                            "format": {
                                "type": "number-percent",
                                "decimalPlaces": {"type": "max", "places": 1},
                            },
                        },
                        "y": {
                            "fieldName": "nome_projeto",
                            "scale": {"type": "categorical"},
                            "displayName": "Projeto",
                        },
                        "color": {
                            "fieldName": "faixa_risco",
                            "scale": {"type": "categorical"},
                        },
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Top Projetos com Risco de Estouro em 30d (ML @prod)",
                    },
                },
            },
            "position": {"x": 6, "y": 5, "width": 6, "height": 6},
        },
        # Tabela Detalhada
        {
            "widget": {
                "name": "table_portfolio_detalhe",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_portfolio",
                            "fields": [
                                {"name": "projeto", "expression": "`projeto`"},
                                {"name": "cliente", "expression": "`cliente`"},
                                {"name": "segmento", "expression": "`segmento`"},
                                {"name": "ferramenta", "expression": "`ferramenta`"},
                                {
                                    "name": "orcamento",
                                    "expression": "`orcamento`",
                                },
                                {"name": "spi", "expression": "`spi`"},
                                {"name": "cpi", "expression": "`cpi`"},
                                {"name": "eac", "expression": "`eac`"},
                                {
                                    "name": "estouro_previsto",
                                    "expression": "`estouro_previsto`",
                                },
                                {"name": "situacao", "expression": "`situacao`"},
                                {
                                    "name": "farol_do_gerente",
                                    "expression": "`farol_do_gerente`",
                                },
                                {
                                    "name": "farol_calculado",
                                    "expression": "`farol_calculado`",
                                },
                                {"name": "melancia", "expression": "`melancia`"},
                            ],
                            "disaggregated": True,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "table",
                    "encodings": {
                        "columns": [
                            {"fieldName": "projeto", "displayName": "Projeto"},
                            {"fieldName": "cliente", "displayName": "Cliente"},
                            {"fieldName": "segmento", "displayName": "Segmento"},
                            {"fieldName": "ferramenta", "displayName": "Ferramenta"},
                            {
                                "fieldName": "orcamento",
                                "displayName": "Orçamento (R$)",
                                "format": {
                                    "type": "number-currency",
                                    "currencyCode": "BRL",
                                    "abbreviation": "compact",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                            {
                                "fieldName": "spi",
                                "displayName": "SPI",
                                "format": {
                                    "type": "number",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                            {
                                "fieldName": "cpi",
                                "displayName": "CPI",
                                "format": {
                                    "type": "number",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                            {
                                "fieldName": "estouro_previsto",
                                "displayName": "Estouro (R$)",
                                "format": {
                                    "type": "number-currency",
                                    "currencyCode": "BRL",
                                    "abbreviation": "compact",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                            {"fieldName": "situacao", "displayName": "Situação"},
                            {
                                "fieldName": "farol_do_gerente",
                                "displayName": "Farol Gerente",
                            },
                            {
                                "fieldName": "farol_calculado",
                                "displayName": "Farol Calc.",
                            },
                            {"fieldName": "melancia", "displayName": "Melancia"},
                        ]
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Detalhamento Situacional de Todos os Projetos",
                    },
                },
            },
            "position": {"x": 0, "y": 11, "width": 12, "height": 7},
        },
    ]

    # Página 2: Pessoas & Alocação
    p2_layout = [
        {
            "widget": {
                "name": "header_pessoas",
                "multilineTextboxSpec": {
                    "lines": [
                        "# Pessoas, Timesheet & Causas de Bloqueio\n",
                        "\n",
                        "Acompanhamento de alocação de equipes, horas ociosas e análise das causas de bloqueio extraídas pela IA nos relatórios semanais.",
                    ]
                },
            },
            "position": {"x": 0, "y": 0, "width": 12, "height": 2},
        },
        {
            "widget": {
                "name": "kpi_horas_ociosas",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_pessoas",
                            "fields": [
                                {
                                    "name": "sum(horas_ociosas)",
                                    "expression": "SUM(`horas_ociosas`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(horas_ociosas)",
                            "displayName": "Horas Ociosas",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 0},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "Horas Ociosas Totais"},
                },
            },
            "position": {"x": 0, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_custo_ocioso",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_pessoas",
                            "fields": [
                                {
                                    "name": "sum(custo_ocioso)",
                                    "expression": "SUM(`custo_ocioso`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(custo_ocioso)",
                            "displayName": "Custo Ocioso",
                            "format": {
                                "type": "number-currency",
                                "currencyCode": "BRL",
                                "abbreviation": "compact",
                                "decimalPlaces": {"type": "max", "places": 2},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "Custo Ocioso Total"},
                },
            },
            "position": {"x": 4, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_taxa_utilizacao",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_pessoas",
                            "fields": [
                                {
                                    "name": "avg(utilizacao)",
                                    "expression": "AVG(`utilizacao`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "avg(utilizacao)",
                            "displayName": "Taxa de Utilização",
                            "format": {
                                "type": "number-percent",
                                "decimalPlaces": {"type": "max", "places": 1},
                            },
                        }
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Taxa Média de Utilização",
                    },
                },
            },
            "position": {"x": 8, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "chart_bloqueios_ia",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_status_ia",
                            "fields": [
                                {
                                    "name": "causa_bloqueio",
                                    "expression": "`causa_bloqueio`",
                                },
                                {
                                    "name": "count(projeto_id)",
                                    "expression": "COUNT(`projeto_id`)",
                                },
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 3,
                    "widgetType": "bar",
                    "encodings": {
                        "x": {
                            "fieldName": "causa_bloqueio",
                            "scale": {"type": "categorical"},
                            "displayName": "Causa do Bloqueio",
                        },
                        "y": {
                            "fieldName": "count(projeto_id)",
                            "scale": {"type": "quantitative"},
                            "displayName": "Ocorrências",
                        },
                        "color": {
                            "fieldName": "causa_bloqueio",
                            "scale": {"type": "categorical"},
                        },
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Causas de Bloqueio nos Status Semanais (IA + Regras)",
                    },
                },
            },
            "position": {"x": 0, "y": 5, "width": 6, "height": 6},
        },
        {
            "widget": {
                "name": "chart_ociosidade_papel",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_pessoas",
                            "fields": [
                                {"name": "papel", "expression": "`papel`"},
                                {
                                    "name": "sum(horas_ociosas)",
                                    "expression": "SUM(`horas_ociosas`)",
                                },
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 3,
                    "widgetType": "bar",
                    "encodings": {
                        "x": {
                            "fieldName": "sum(horas_ociosas)",
                            "scale": {"type": "quantitative"},
                            "displayName": "Total Horas Ociosas",
                        },
                        "y": {
                            "fieldName": "papel",
                            "scale": {"type": "categorical"},
                            "displayName": "Papel Técnico",
                        },
                        "color": {
                            "fieldName": "papel",
                            "scale": {"type": "categorical"},
                        },
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Horas Ociosas por Papel Técnico",
                    },
                },
            },
            "position": {"x": 6, "y": 5, "width": 6, "height": 6},
        },
        {
            "widget": {
                "name": "table_utilizacao_pessoas",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_pessoas",
                            "fields": [
                                {"name": "nome", "expression": "`nome`"},
                                {"name": "papel", "expression": "`papel`"},
                                {
                                    "name": "senioridade",
                                    "expression": "`senioridade`",
                                },
                                {
                                    "name": "projeto_id",
                                    "expression": "`projeto_id`",
                                },
                                {"name": "semana", "expression": "`semana`"},
                                {
                                    "name": "horas_disponiveis",
                                    "expression": "`horas_disponiveis`",
                                },
                                {
                                    "name": "horas_apontadas",
                                    "expression": "`horas_apontadas`",
                                },
                                {
                                    "name": "horas_ociosas",
                                    "expression": "`horas_ociosas`",
                                },
                                {
                                    "name": "utilizacao",
                                    "expression": "`utilizacao`",
                                },
                                {
                                    "name": "custo_ocioso",
                                    "expression": "`custo_ocioso`",
                                },
                            ],
                            "disaggregated": True,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "table",
                    "encodings": {
                        "columns": [
                            {"fieldName": "nome", "displayName": "Colaborador"},
                            {"fieldName": "papel", "displayName": "Papel"},
                            {
                                "fieldName": "senioridade",
                                "displayName": "Senioridade",
                            },
                            {"fieldName": "projeto_id", "displayName": "Projeto"},
                            {"fieldName": "semana", "displayName": "Semana"},
                            {
                                "fieldName": "horas_disponiveis",
                                "displayName": "Horas Disp.",
                            },
                            {
                                "fieldName": "horas_apontadas",
                                "displayName": "Horas Apont.",
                            },
                            {
                                "fieldName": "horas_ociosas",
                                "displayName": "Horas Ociosas",
                            },
                            {
                                "fieldName": "utilizacao",
                                "displayName": "Utilização",
                                "format": {
                                    "type": "number-percent",
                                    "decimalPlaces": {"type": "max", "places": 1},
                                },
                            },
                            {
                                "fieldName": "custo_ocioso",
                                "displayName": "Custo Ocioso (R$)",
                                "format": {
                                    "type": "number-currency",
                                    "currencyCode": "BRL",
                                    "abbreviation": "compact",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                        ]
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Apontamentos e Utilização Semanal",
                    },
                },
            },
            "position": {"x": 0, "y": 11, "width": 12, "height": 6},
        },
    ]

    # Página 3: Fornecedores & Entregas
    p3_layout = [
        {
            "widget": {
                "name": "header_fornecedores",
                "multilineTextboxSpec": {
                    "lines": [
                        "# Gestão de Fornecedores & Consultorias\n",
                        "\n",
                        "Monitoramento das entregas contratadas com foco no cumprimento de prazos e atrasos de consultorias externas.",
                    ]
                },
            },
            "position": {"x": 0, "y": 0, "width": 12, "height": 2},
        },
        {
            "widget": {
                "name": "kpi_entregas_atraso",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {
                                    "name": "sum(em_atraso_flag)",
                                    "expression": "SUM(`em_atraso_flag`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(em_atraso_flag)",
                            "displayName": "Entregas em Atraso",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 0},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "Entregas em Atraso"},
                },
            },
            "position": {"x": 0, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_total_entregas",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {
                                    "name": "count(entrega_id)",
                                    "expression": "COUNT(`entrega_id`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "count(entrega_id)",
                            "displayName": "Total Entregas",
                            "format": {
                                "type": "number",
                                "decimalPlaces": {"type": "max", "places": 0},
                            },
                        }
                    },
                    "frame": {"showTitle": True, "title": "Total de Entregas"},
                },
            },
            "position": {"x": 4, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "kpi_valor_fornecedores",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {
                                    "name": "sum(valor)",
                                    "expression": "SUM(`valor`)",
                                }
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "counter",
                    "encodings": {
                        "value": {
                            "fieldName": "sum(valor)",
                            "displayName": "Valor Total Contratado",
                            "format": {
                                "type": "number-currency",
                                "currencyCode": "BRL",
                                "abbreviation": "compact",
                                "decimalPlaces": {"type": "max", "places": 2},
                            },
                        }
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Valor Total Contratado (R$)",
                    },
                },
            },
            "position": {"x": 8, "y": 2, "width": 4, "height": 3},
        },
        {
            "widget": {
                "name": "chart_atrasos_itens",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {"name": "item", "expression": "`item`"},
                                {
                                    "name": "dias_de_atraso_na_entrega",
                                    "expression": "`dias_de_atraso_na_entrega`",
                                },
                            ],
                            "disaggregated": True,
                        },
                    }
                ],
                "spec": {
                    "version": 3,
                    "widgetType": "bar",
                    "encodings": {
                        "x": {
                            "fieldName": "dias_de_atraso_na_entrega",
                            "scale": {"type": "quantitative"},
                            "displayName": "Dias de Desvio na Entrega",
                        },
                        "y": {
                            "fieldName": "item",
                            "scale": {"type": "categorical"},
                            "displayName": "Item Contratado",
                        },
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Dias de Desvio na Entrega (Real vs Prometido)",
                    },
                },
            },
            "position": {"x": 0, "y": 5, "width": 6, "height": 6},
        },
        {
            "widget": {
                "name": "table_resumo_fornecedores",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {
                                    "name": "fornecedor",
                                    "expression": "`fornecedor`",
                                },
                                {
                                    "name": "count(entrega_id)",
                                    "expression": "COUNT(`entrega_id`)",
                                },
                                {
                                    "name": "sum(em_atraso_flag)",
                                    "expression": "SUM(`em_atraso_flag`)",
                                },
                                {
                                    "name": "avg(dias_de_atraso_na_entrega)",
                                    "expression": "AVG(`dias_de_atraso_na_entrega`)",
                                },
                            ],
                            "disaggregated": False,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "table",
                    "encodings": {
                        "columns": [
                            {"fieldName": "fornecedor", "displayName": "Fornecedor"},
                            {
                                "fieldName": "count(entrega_id)",
                                "displayName": "Total Entregas",
                            },
                            {
                                "fieldName": "sum(em_atraso_flag)",
                                "displayName": "Entregas em Atraso",
                            },
                            {
                                "fieldName": "avg(dias_de_atraso_na_entrega)",
                                "displayName": "Atraso Médio (Dias)",
                                "format": {
                                    "type": "number",
                                    "decimalPlaces": {"type": "max", "places": 1},
                                },
                            },
                        ]
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Desempenho por Fornecedor",
                    },
                },
            },
            "position": {"x": 6, "y": 5, "width": 6, "height": 6},
        },
        {
            "widget": {
                "name": "table_detalhe_entregas",
                "queries": [
                    {
                        "name": "main_query",
                        "query": {
                            "datasetName": "ds_fornecedores",
                            "fields": [
                                {
                                    "name": "entrega_id",
                                    "expression": "`entrega_id`",
                                },
                                {
                                    "name": "projeto_id",
                                    "expression": "`projeto_id`",
                                },
                                {
                                    "name": "fornecedor",
                                    "expression": "`fornecedor`",
                                },
                                {"name": "item", "expression": "`item`"},
                                {"name": "valor", "expression": "`valor`"},
                                {
                                    "name": "data_pedido",
                                    "expression": "`data_pedido`",
                                },
                                {
                                    "name": "data_prometida",
                                    "expression": "`data_prometida`",
                                },
                                {
                                    "name": "data_entrega",
                                    "expression": "`data_entrega`",
                                },
                                {
                                    "name": "dias_de_atraso_na_entrega",
                                    "expression": "`dias_de_atraso_na_entrega`",
                                },
                                {"name": "status", "expression": "`status`"},
                            ],
                            "disaggregated": True,
                        },
                    }
                ],
                "spec": {
                    "version": 2,
                    "widgetType": "table",
                    "encodings": {
                        "columns": [
                            {"fieldName": "entrega_id", "displayName": "ID"},
                            {"fieldName": "projeto_id", "displayName": "Projeto"},
                            {"fieldName": "fornecedor", "displayName": "Fornecedor"},
                            {"fieldName": "item", "displayName": "Item"},
                            {
                                "fieldName": "valor",
                                "displayName": "Valor (R$)",
                                "format": {
                                    "type": "number-currency",
                                    "currencyCode": "BRL",
                                    "abbreviation": "compact",
                                    "decimalPlaces": {"type": "max", "places": 2},
                                },
                            },
                            {
                                "fieldName": "data_pedido",
                                "displayName": "Data Pedido",
                            },
                            {
                                "fieldName": "data_prometida",
                                "displayName": "Data Prometida",
                            },
                            {
                                "fieldName": "data_entrega",
                                "displayName": "Data Entrega",
                            },
                            {
                                "fieldName": "dias_de_atraso_na_entrega",
                                "displayName": "Dias Atraso",
                            },
                            {"fieldName": "status", "displayName": "Status"},
                        ]
                    },
                    "frame": {
                        "showTitle": True,
                        "title": "Relação Completa de Entregas de Consultorias",
                    },
                },
            },
            "position": {"x": 0, "y": 11, "width": 12, "height": 6},
        },
    ]

    dashboard = {
        "datasets": datasets,
        "pages": [
            {
                "name": "portfolio",
                "displayName": "Portfólio & Risco",
                "pageType": "PAGE_TYPE_CANVAS",
                "layoutVersion": "GRID_V1",
                "layout": p1_layout,
            },
            {
                "name": "pessoas",
                "displayName": "Pessoas & Alocação",
                "pageType": "PAGE_TYPE_CANVAS",
                "layoutVersion": "GRID_V1",
                "layout": p2_layout,
            },
            {
                "name": "fornecedores",
                "displayName": "Fornecedores & Entregas",
                "pageType": "PAGE_TYPE_CANVAS",
                "layoutVersion": "GRID_V1",
                "layout": p3_layout,
            },
        ],
        "uiSettings": ui_settings,
    }

    return dashboard


def main():
    dashboard = construir_dashboard()
    destino = Path(__file__).resolve().parent.parent / "resources" / "dashboard-portfolio.lvdash.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)
    print(f"Dashboard gerado com sucesso em: {destino}")


if __name__ == "__main__":
    main()
