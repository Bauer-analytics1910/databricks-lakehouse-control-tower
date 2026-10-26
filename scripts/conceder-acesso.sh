#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-DEFAULT}"
APP_NAME="minha-torre"

echo "Obtendo service_principal_client_id do app ${APP_NAME} (profile: ${PROFILE})..."
SP_ID=$(databricks apps get "${APP_NAME}" --profile "${PROFILE}" -o json | python3 -c "import sys, json; print(json.load(sys.stdin)['service_principal_client_id'])")

if [ -z "${SP_ID}" ]; then
  echo "Erro: não foi possível obter service_principal_client_id."
  exit 1
fi

echo "Service Principal ID: ${SP_ID}"
echo "Concedendo permissões em lakehouse_vertice (gold e silver)..."

databricks experimental aitools tools query "GRANT USE CATALOG ON CATALOG lakehouse_vertice TO \`${SP_ID}\`" --profile "${PROFILE}"
databricks experimental aitools tools query "GRANT USE SCHEMA ON SCHEMA lakehouse_vertice.gold TO \`${SP_ID}\`" --profile "${PROFILE}"
databricks experimental aitools tools query "GRANT SELECT ON SCHEMA lakehouse_vertice.gold TO \`${SP_ID}\`" --profile "${PROFILE}"
databricks experimental aitools tools query "GRANT USE SCHEMA ON SCHEMA lakehouse_vertice.silver TO \`${SP_ID}\`" --profile "${PROFILE}"
databricks experimental aitools tools query "GRANT SELECT ON SCHEMA lakehouse_vertice.silver TO \`${SP_ID}\`" --profile "${PROFILE}"

echo "Permissões concedidas com sucesso!"
