# Minha Torre · Databricks App (Torre de Controle Executiva)

Aplicação web full-stack construída com **React 19**, **TypeScript**, **Tailwind CSS v4** e **Databricks AppKit (`@databricks/appkit` / `@databricks/appkit-ui`)**, projetada para rodar nativamente no **Databricks Apps** como a interface executiva da **Vértice Tecnologia**.

---

## 1. Visão Geral & Funcionalidades

A **Torre de Controle (`minha-torre`)** conecta a diretoria e o PMO diretamente às camadas **Gold**, **Métricas Governadas** e **Machine Learning** do catálogo `lakehouse_vertice` no Unity Catalog, estruturada em três frentes de decisão:

1. **Monitoramento da Carteira & Projetos em Risco**:
   - Cards executivos em tempo real (Projetos em andamento, Projetos em risco/críticos, *Projetos Melancia*, Estouro total previsto em R$ e Valor total da carteira).
   - Tabela interativa de projetos ordenada por criticidade (`crítico` → `atenção` → `ok`), exibindo `SPI`, `CPI`, `EAC`, atraso projetado em dias, comparativo **Farol do Gerente vs. Farol Calculado**, causa de bloqueio mais frequente extraída por IA (`ai_classify`) e dias de impacto acumulados.
2. **Radar Preditivo de Estouro em 30 Dias (MLflow `@prod`)**:
   - Consumo direto da tabela `lakehouse_vertice.gold.score_estouro_30d` via endpoint `/api/score-estouro`, destacando a probabilidade (`prob_estouro_30d`), a faixa de risco (`alto`, `medio`, `baixo`) e os **principais fatores explicativos em português** gerados pelo pipeline de Machine Learning.
3. **Simulador de Realocação de Squad & Agente Analítico Genie**:
   - Identifica colaboradores com **utilização média inferior a 20% nas últimas 12 semanas** (`pessoas_ociosas.sql`) e permite simular o impacto de alocá-los em projetos penalizados por *Falta de SRE* ou *Rotatividade*.
   - Aba **"Perguntar"** com o componente nativo `<GenieChat />`, permitindo conversação em linguagem natural sobre toda a carteira com autenticação **OAuth On-Behalf-Of (OBO)**.

---

## 2. Arquitetura Técnica (React 19 + Node.js / AppKit)

```text
minha-torre/
├── app.yaml                        # Manifesto de execução no Databricks Apps (comando, env vars e escopos OBO)
├── databricks.yml                  # Configuração do Databricks Asset Bundle para deploy da aplicação
├── package.json                    # Scripts de build, tipagem e dependências (@databricks/appkit 0.84.0)
├── config/
│   ├── metric-views/               # Definições e metadados gerados das Metric Views do Unity Catalog
│   └── queries/                    # Queries SQL gerenciadas pelo plugin analytics() do AppKit
│       ├── kpis.sql                # Resumo executivo da carteira (gold.projeto_situacao_atual)
│       ├── projetos_risco.sql      # Ranking de projetos + causas de bloqueio IA (gold.status_estruturado)
│       └── pessoas_ociosas.sql     # Colaboradores com utilização < 20% em 12 semanas
├── server/
│   └── server.ts                   # Servidor Node/Express com plugins analytics(), genie() e rotas customizadas
├── client/
│   ├── src/App.tsx                 # Interface executiva principal, simulador de realocação e aba GenieChat
│   ├── src/ErrorBoundary.tsx       # Tratamento resiliente de erros de renderização
│   └── vite.config.ts              # Configuração de build do frontend (rolldown-vite + Tailwind v4)
└── shared/appkit-types/            # Tipos TypeScript gerados automaticamente a partir das queries SQL
```

### Contratos de Dados do Backend (`server/server.ts`)
Além dos endpoints automáticos providos pelos plugins `analytics()` e `genie()` do `@databricks/appkit`, o servidor expõe duas rotas customizadas:
- **`GET /api/whoami`**: Identifica o usuário autenticado a partir dos cabeçalhos injetados pelo proxy do Databricks Apps (`x-forwarded-email`, `x-forwarded-user`).
- **`GET /api/score-estouro`**: Executa uma consulta assíncrona via `statementExecution.executeStatement` no SQL Warehouse lendo `lakehouse_vertice.gold.score_estouro_30d`, valida o retorno com **Zod** (`scoreRowSchema`) e retorna `{ disponivel: boolean, linhas: ScoreRow[] }` com degradação graciosa caso a tabela de ML ainda não tenha sido populada.

---

## 3. Variáveis de Ambiente e Autenticação OAuth OBO

No ambiente gerenciado do Databricks Apps, as variáveis e escopos são injetados declarativamente através do arquivo [`app.yaml`](app.yaml) e vinculados aos recursos em [`databricks.yml`](databricks.yml):

| Variável / Configuração | Origem (`app.yaml` / `databricks.yml`) | Descrição |
| :--- | :--- | :--- |
| `DATABRICKS_WAREHOUSE_ID` | `valueFrom: sql-warehouse` (`CAN_USE`) | ID do SQL Warehouse Serverless utilizado para executar as queries de `config/queries/` e `/api/score-estouro`. |
| `DATABRICKS_GENIE_SPACE_ID` | `valueFrom: genie-space` (`CAN_RUN`) | ID do espaço Genie **`Farol · Diretoria`** consumido pelo componente `<GenieChat />`. |
| `user_api_scopes` | `genie`, `dashboards.genie` | Escopos de autenticação **OAuth On-Behalf-Of (OBO)** necessários para que o Genie execute consultas em nome do usuário autenticado. |

Para desenvolvimento local, crie um arquivo `.env` na pasta `minha-torre/` (ignorado pelo Git):

```env
DATABRICKS_HOST=https://<seu-workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<seu-pat-ou-oauth-token>
DATABRICKS_WAREHOUSE_ID=<id-do-sql-warehouse>
DATABRICKS_GENIE_SPACE_ID=<id-do-genie-space>
```

---

## 4. Execução Local e Deploy

### Desenvolvimento Local
```bash
cd minha-torre

# 1. Instalar dependências
npm install

# 2. Sincronizar plugins AppKit, gerar tipos das queries SQL e iniciar servidor em modo watch
npm run dev

# 3. Validar tipagem TypeScript (client + server) e gerar build de produção
npm run typecheck
npm run build
```

### Deploy no Databricks Apps via DABs
```bash
cd minha-torre

# 1. Validar e publicar o bundle do aplicativo
databricks bundle validate -t default
databricks bundle deploy -t default

# 2. Na raiz do repositório, conceder acesso ao Service Principal do App no Unity Catalog
cd ..
bash scripts/conceder-acesso.sh DEFAULT
```
