import {
  analytics,
  createApp,
  genie,
  getExecutionContext,
  getWarehouseId,
  server,
} from '@databricks/appkit';
import { z } from 'zod';

const scoreRowSchema = z.object({
  projeto_id: z.string(),
  data_referencia: z.string().nullable().optional(),
  prob_estouro_30d: z.coerce.number(),
  ranking: z.coerce.number(),
  faixa_risco: z.string(),
  principais_fatores: z.string().nullable().optional(),
});

createApp({
  cache: { enabled: false },
  plugins: [analytics(), genie(), server()],
  onPluginsReady(appkit) {
    appkit.server.extend((app) => {
      app.get('/api/whoami', (req, res) => {
        const email =
          (req.headers['x-forwarded-email'] as string) ||
          (req.headers['x-databricks-org-id']
            ? 'usuario@vertice.com'
            : 'dev@vertice.com');
        const user = (req.headers['x-forwarded-user'] as string) || 'dev';
        res.json({ email, user });
      });

      app.get('/api/score-estouro', async (_req, res) => {
        try {
          const { client } = getExecutionContext();
          const warehouseId = await getWarehouseId();
          const response = await client.statementExecution.executeStatement({
            warehouse_id: warehouseId,
            statement:
              'SELECT projeto_id, data_referencia, prob_estouro_30d, ranking, faixa_risco, principais_fatores FROM lakehouse_vertice.gold.score_estouro_30d ORDER BY ranking ASC',
            wait_timeout: '15s',
          });

          if (
            response.status?.state !== 'SUCCEEDED' ||
            !response.result?.data_array
          ) {
            res.json({ disponivel: false, linhas: [] });
            return;
          }

          const columns =
            response.manifest?.schema?.columns?.map((c) => c.name ?? '') ?? [];
          const rawRows = response.result.data_array.map((row) => {
            const obj: Record<string, unknown> = {};
            columns.forEach((col, idx) => {
              if (col) {
                obj[col] = row[idx];
              }
            });
            return obj;
          });

          const linhas = z.array(scoreRowSchema).parse(rawRows);
          res.json({ disponivel: true, linhas });
        } catch {
          res.json({ disponivel: false, linhas: [] });
        }
      });
    });
  },
}).catch(console.error);
