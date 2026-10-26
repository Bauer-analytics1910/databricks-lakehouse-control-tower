import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
  GenieChat,
  Input,
  Label,
  ResourceStatusIndicator,
  ResourceStatusProvider,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  useAnalyticsQuery,
} from '@databricks/appkit-ui/react';
import {
  AlertTriangle,
  ArrowRightLeft,
  MessageSquare,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';

interface WhoAmIResponse {
  email?: string;
  user?: string;
}

interface ScoreRow {
  projeto_id: string;
  data_referencia?: string | null;
  prob_estouro_30d: number;
  ranking: number;
  faixa_risco: string;
  principais_fatores?: string | null;
}

interface ScoreResponse {
  disponivel: boolean;
  linhas: ScoreRow[];
}

const brlCompact = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
});

function formatBRLMilhoes(valor: number): string {
  const n = Number(valor) || 0;
  if (Math.abs(n) >= 1_000_000) {
    return `R$ ${(n / 1_000_000).toLocaleString('pt-BR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 2,
    })} mi`;
  }
  if (Math.abs(n) >= 1_000) {
    return `R$ ${(n / 1_000).toLocaleString('pt-BR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} mil`;
  }
  return brlCompact.format(n);
}

function formatIndice(valor: unknown): string {
  const n = Number(valor);
  if (Number.isNaN(n)) return '—';
  return n.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

const CAUSA_LABELS: Record<string, string> = {
  falta_sre: 'Falta de SRE',
  rotatividade: 'Rotatividade',
  dependencia_fornecedor: 'Dependência fornecedor',
  change_freeze: 'Change freeze',
  mudanca_escopo: 'Mudança de escopo',
  bug_retrabalho: 'Bug / retrabalho',
  aprovacao_cliente: 'Aprovação do cliente',
  sem_bloqueio: 'Sem bloqueio',
  nao_reportado: 'Não reportado',
};

function formatCausa(causa: string): string {
  return CAUSA_LABELS[causa] ?? causa;
}

function SituacaoBadge({ situacao }: { situacao: string }) {
  const norm = (situacao || '').toLowerCase();
  if (norm === 'crítico' || norm === 'critico') {
    return <Badge variant="destructive">Crítico</Badge>;
  }
  if (norm === 'atenção' || norm === 'atencao') {
    return (
      <Badge
        variant="secondary"
        style={{
          backgroundColor: 'var(--warning)',
          color: 'var(--warning-foreground)',
        }}
      >
        Atenção
      </Badge>
    );
  }
  return <Badge variant="outline">OK</Badge>;
}

function FarolBadge({
  farol,
  melancia = false,
}: {
  farol: string;
  melancia?: boolean;
}) {
  const norm = (farol || '').toLowerCase();
  let style: React.CSSProperties | undefined;
  let variant: 'default' | 'destructive' | 'secondary' | 'outline' = 'outline';

  if (norm === 'vermelho') {
    variant = 'destructive';
  } else if (norm === 'amarelo') {
    variant = 'secondary';
    style = {
      backgroundColor: 'var(--warning)',
      color: 'var(--warning-foreground)',
    };
  } else if (norm === 'verde') {
    variant = 'secondary';
    style = {
      backgroundColor: 'var(--success)',
      color: 'var(--success-foreground)',
    };
  }

  return (
    <Badge variant={variant} style={style}>
      {farol || '—'}
      {melancia ? ' 🍉' : ''}
    </Badge>
  );
}

export default function App() {
  const [abaAtiva, setAbaAtiva] = useState<'risco' | 'simulador' | 'perguntar'>(
    'risco'
  );
  const [usuario, setUsuario] = useState<{
    email?: string;
    user?: string;
  } | null>(null);
  const [scoreState, setScoreState] = useState<{
    carregando: boolean;
    dados: ScoreResponse;
  }>({
    carregando: true,
    dados: { disponivel: false, linhas: [] },
  });

  useEffect(() => {
    let ativo = true;
    fetch('/api/whoami')
      .then((r) => (r.ok ? (r.json() as Promise<WhoAmIResponse>) : null))
      .then((data) => {
        if (ativo && data) setUsuario(data);
      })
      .catch(() => {});
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    let ativo = true;
    fetch('/api/score-estouro')
      .then((r) => r.json())
      .then((json: ScoreResponse) => {
        if (ativo) {
          setScoreState({
            carregando: false,
            dados: {
              disponivel: Boolean(json?.disponivel),
              linhas: Array.isArray(json?.linhas) ? json.linhas : [],
            },
          });
        }
      })
      .catch(() => {
        if (ativo) {
          setScoreState({
            carregando: false,
            dados: { disponivel: false, linhas: [] },
          });
        }
      });
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <ResourceStatusProvider>
      <ResourceStatusIndicator />
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <header className="border-b px-4 md:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-6 w-6 text-primary" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">Projeto Farol</h1>
              <p className="text-xs text-muted-foreground">
                Torre de Controle · Vértice Tecnologia · Ref. 16/10/2026
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Badge variant="outline" className="hidden sm:inline-flex text-xs">
              {usuario?.email ?? 'dev@vertice.com'}
            </Badge>

            <nav
              className="flex items-center gap-2"
              aria-label="Menu principal"
            >
              <Button
                variant={abaAtiva === 'risco' ? 'default' : 'ghost'}
                onClick={() => setAbaAtiva('risco')}
              >
                <AlertTriangle className="h-4 w-4 mr-2" />
                Projetos em risco
              </Button>
              <Button
                variant={abaAtiva === 'simulador' ? 'default' : 'ghost'}
                onClick={() => setAbaAtiva('simulador')}
              >
                <ArrowRightLeft className="h-4 w-4 mr-2" />
                Simulador
              </Button>
              <Button
                variant={abaAtiva === 'perguntar' ? 'default' : 'ghost'}
                onClick={() => setAbaAtiva('perguntar')}
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Perguntar
              </Button>
            </nav>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto space-y-6">
          {abaAtiva === 'risco' && (
            <TelaProjetosRisco scoreState={scoreState} />
          )}
          {abaAtiva === 'simulador' && <TelaSimulador />}
          {abaAtiva === 'perguntar' && <TelaPerguntar usuario={usuario} />}
        </main>
      </div>
    </ResourceStatusProvider>
  );
}

function TelaProjetosRisco({
  scoreState,
}: {
  scoreState: { carregando: boolean; dados: ScoreResponse };
}) {
  const {
    data: kpisData,
    loading: kpisLoading,
    error: kpisError,
  } = useAnalyticsQuery('kpis');

  const {
    data: projetosData,
    loading: projetosLoading,
    error: projetosError,
  } = useAnalyticsQuery('projetos_risco');

  const kpi = kpisData?.[0];

  const scorePorProjeto = useMemo(() => {
    const map = new Map<string, ScoreRow>();
    if (scoreState.dados.disponivel) {
      for (const row of scoreState.dados.linhas) {
        map.set(row.projeto_id, {
          ...row,
          prob_estouro_30d: Number(row.prob_estouro_30d),
          ranking: Number(row.ranking),
        });
      }
    }
    return map;
  }, [scoreState.dados]);

  const altoRisco30d = useMemo(() => {
    if (!scoreState.dados.disponivel) return null;
    return scoreState.dados.linhas.filter(
      (l) => String(l.faixa_risco).toLowerCase() === 'alto',
    ).length;
  }, [scoreState.dados]);

  return (
    <div className="space-y-6">
      {(kpisError || projetosError) && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao consultar o SQL Warehouse</AlertTitle>
          <AlertDescription>{kpisError || projetosError}</AlertDescription>
        </Alert>
      )}

      {/* 4 KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Em risco (atenção + crítico)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {kpisLoading ? (
              <Skeleton className="h-8 w-32" />
            ) : kpi ? (
              <div className="space-y-1">
                <div className="text-2xl font-bold">
                  {Number(kpi.em_risco)} de {Number(kpi.projetos_em_andamento)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {Number(kpi.criticos)} críticos · {Number(kpi.melancias)}{' '}
                  melancias 🍉
                </p>
              </div>
            ) : (
              <div className="text-muted-foreground">—</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Estouro previsto
            </CardTitle>
          </CardHeader>
          <CardContent>
            {kpisLoading ? (
              <Skeleton className="h-8 w-36" />
            ) : kpi ? (
              <div className="space-y-1">
                <div className="text-2xl font-bold text-destructive">
                  {formatBRLMilhoes(Number(kpi.estouro_previsto))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {brlCompact.format(Number(kpi.estouro_previsto))} (EAC −
                  orçamento)
                </p>
              </div>
            ) : (
              <div className="text-muted-foreground">—</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Carteira em andamento
            </CardTitle>
          </CardHeader>
          <CardContent>
            {kpisLoading ? (
              <Skeleton className="h-8 w-36" />
            ) : kpi ? (
              <div className="space-y-1">
                <div className="text-2xl font-bold">
                  {formatBRLMilhoes(Number(kpi.carteira))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {brlCompact.format(Number(kpi.carteira))} em contratos ativos
                </p>
              </div>
            ) : (
              <div className="text-muted-foreground">—</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Alto risco em 30 dias
            </CardTitle>
          </CardHeader>
          <CardContent>
            {scoreState.carregando ? (
              <Skeleton className="h-8 w-24" />
            ) : altoRisco30d !== null ? (
              <div className="space-y-1">
                <div className="text-2xl font-bold">{altoRisco30d}</div>
                <p className="text-xs text-muted-foreground">
                  P(estouro) ≥ 50% no modelo preditivo
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="text-2xl font-bold text-muted-foreground">—</div>
                <p className="text-xs text-muted-foreground">
                  Score preditivo indisponível
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Tabela de projetos */}
      <Card>
        <CardHeader>
          <CardTitle>
            Projetos em andamento · ordenados do pior para o melhor
          </CardTitle>
        </CardHeader>
        <CardContent>
          {projetosLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : !projetosData || projetosData.length === 0 ? (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>Nenhum projeto encontrado</EmptyTitle>
                <EmptyDescription>
                  Não há projetos em andamento na camada gold.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Projeto</TableHead>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Situação</TableHead>
                    <TableHead className="text-right">SPI</TableHead>
                    <TableHead className="text-right">CPI</TableHead>
                    <TableHead className="text-right">Estouro Previsto</TableHead>
                    <TableHead className="text-right">Atraso (dias)</TableHead>
                    <TableHead>Farol (Gerente × Calc.)</TableHead>
                    <TableHead>Causa Frequente (90d)</TableHead>
                    <TableHead className="text-right">P(estouro)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {projetosData.map((p) => {
                    const spi = Number(p.spi);
                    const cpi = Number(p.cpi);
                    const estouro = Number(p.estouro_previsto);
                    const atraso = Number(p.atraso_projetado_dias);
                    const isMelancia =
                      String(p.melancia) === 'true' || p.melancia === true;
                    const diasSre = Number(p.dias_impacto_falta_sre);
                    const diasRot = Number(p.dias_impacto_rotatividade);
                    const score = scorePorProjeto.get(p.projeto_id);

                    return (
                      <TableRow key={p.projeto_id}>
                        <TableCell className="font-medium">
                          <div>{p.projeto}</div>
                          <div className="text-xs text-muted-foreground">
                            {p.gerente_projeto} · {p.segmento}
                          </div>
                        </TableCell>
                        <TableCell>{p.cliente}</TableCell>
                        <TableCell>
                          <SituacaoBadge situacao={p.situacao} />
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatIndice(spi)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatIndice(cpi)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {estouro > 0 ? brlCompact.format(estouro) : 'R$ 0,00'}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {atraso > 0 ? `+${Math.round(atraso)}d` : '0d'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <FarolBadge
                              farol={p.farol_do_gerente}
                              melancia={isMelancia}
                            />
                            <span className="text-xs text-muted-foreground">
                              ×
                            </span>
                            <FarolBadge farol={p.farol_calculado} />
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            {formatCausa(p.causa_mais_frequente)}
                          </div>
                          {(diasSre > 0 || diasRot > 0) && (
                            <div className="text-xs text-muted-foreground">
                              {diasSre > 0 ? `Falta SRE: ${diasSre}d ` : ''}
                              {diasRot > 0 ? `Rotatividade: ${diasRot}d` : ''}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {score ? (
                            <div title={score.principais_fatores ?? undefined}>
                              <span>
                                {(Number(score.prob_estouro_30d) * 100).toFixed(
                                  0,
                                )}
                                %
                              </span>
                              <span className="ml-1 text-xs text-muted-foreground">
                                ({score.faixa_risco})
                              </span>
                            </div>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function TelaSimulador() {
  const {
    data: pessoasData,
    loading: pessoasLoading,
    error: pessoasError,
  } = useAnalyticsQuery('pessoas_ociosas');

  const {
    data: projetosData,
    loading: projetosLoading,
    error: projetosError,
  } = useAnalyticsQuery('projetos_risco');

  const [colaboradorId, setColaboradorId] = useState<string>('COL0017');
  const [projetoDestinoId, setProjetoDestinoId] = useState<string>('PRJ-011');
  const [horasOnboarding, setHorasOnboarding] = useState<number>(40);

  const pessoaSelecionada = useMemo(() => {
    if (!pessoasData || pessoasData.length === 0) return null;
    return (
      pessoasData.find((p) => p.colaborador_id === colaboradorId) ??
      pessoasData[0]
    );
  }, [pessoasData, colaboradorId]);

  const projetosCandidatos = useMemo(() => {
    if (!projetosData) return [];
    const filtrados = projetosData.filter((p) => {
      const sit = (p.situacao || '').toLowerCase();
      return (
        sit === 'crítico' ||
        sit === 'critico' ||
        sit === 'atenção' ||
        sit === 'atencao'
      );
    });

    const isSre =
      (pessoaSelecionada?.papel || '').toLowerCase().trim() === 'sre';

    return [...filtrados].sort((a, b) => {
      if (isSre) {
        const diffSre =
          Number(b.dias_impacto_falta_sre) - Number(a.dias_impacto_falta_sre);
        if (diffSre !== 0) return diffSre;
      } else {
        const diffRot =
          Number(b.dias_impacto_rotatividade) -
          Number(a.dias_impacto_rotatividade);
        if (diffRot !== 0) return diffRot;
      }
      return Number(a.spi) - Number(b.spi);
    });
  }, [projetosData, pessoaSelecionada]);

  const projetoSelecionado = useMemo(() => {
    if (projetosCandidatos.length === 0) return null;
    return (
      projetosCandidatos.find((p) => p.projeto_id === projetoDestinoId) ??
      projetosCandidatos[0]
    );
  }, [projetosCandidatos, projetoDestinoId]);

  const simulacao = useMemo(() => {
    if (!pessoaSelecionada || !projetoSelecionado) return null;

    const mediaHorasSemana = Number(
      pessoaSelecionada.media_horas_ociosas_semana,
    );
    const mediaCustoSemana = Number(
      pessoaSelecionada.media_custo_ocioso_semana,
    );
    const custoHora = Number(pessoaSelecionada.custo_hora);

    const horasNoMes = mediaHorasSemana * 4;
    const ociosidadeEvitada = mediaCustoSemana * 4;

    const isSre =
      (pessoaSelecionada.papel || '').toLowerCase().trim() === 'sre';
    const diasImpacto90d = isSre
      ? Number(projetoSelecionado.dias_impacto_falta_sre)
      : Number(projetoSelecionado.dias_impacto_rotatividade);

    const diasRecuperados = (diasImpacto90d / 90) * 30;
    const mobilizacao = Number(horasOnboarding) * custoHora;
    const saldo = ociosidadeEvitada - mobilizacao;

    return {
      mediaHorasSemana,
      mediaCustoSemana,
      custoHora,
      horasNoMes,
      ociosidadeEvitada,
      diasImpacto90d,
      diasRecuperados,
      mobilizacao,
      saldo,
      causaAlvo: isSre ? 'falta_sre' : 'rotatividade',
    };
  }, [pessoaSelecionada, projetoSelecionado, horasOnboarding]);

  if (pessoasLoading || projetosLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (pessoasError || projetosError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Erro ao carregar dados do simulador</AlertTitle>
        <AlertDescription>{pessoasError || projetosError}</AlertDescription>
      </Alert>
    );
  }

  if (!pessoasData || pessoasData.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Nenhuma pessoa ociosa encontrada</EmptyTitle>
          <EmptyDescription>
            Não há colaboradores com utilização inferior a 20% nas últimas 12
            semanas.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Simulador de Realocação de Pessoas</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <Label htmlFor="select-pessoa">
              Pessoa ociosa (utilização &lt; 20% em 12 semanas)
            </Label>
            <Select
              value={pessoaSelecionada?.colaborador_id ?? ''}
              onValueChange={setColaboradorId}
            >
              <SelectTrigger id="select-pessoa">
                <SelectValue placeholder="Selecione um colaborador" />
              </SelectTrigger>
              <SelectContent>
                {pessoasData.map((p) => (
                  <SelectItem key={p.colaborador_id} value={p.colaborador_id}>
                    {p.colaborador_id} · {p.nome} ({p.papel.toUpperCase()} ·{' '}
                    {p.projeto_atual} ·{' '}
                    {(Number(p.utilizacao_media) * 100).toFixed(1)}% uso)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {pessoaSelecionada && (
              <p className="text-xs text-muted-foreground">
                Média de{' '}
                {Number(pessoaSelecionada.media_horas_ociosas_semana).toFixed(
                  1,
                )}{' '}
                h paradas/sem · Custo/h:{' '}
                {brlCompact.format(Number(pessoaSelecionada.custo_hora))}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="select-projeto">
              Projeto destino (apenas crítico ou atenção)
            </Label>
            <Select
              value={projetoSelecionado?.projeto_id ?? ''}
              onValueChange={setProjetoDestinoId}
            >
              <SelectTrigger id="select-projeto">
                <SelectValue placeholder="Selecione o projeto destino" />
              </SelectTrigger>
              <SelectContent>
                {projetosCandidatos.map((proj) => (
                  <SelectItem key={proj.projeto_id} value={proj.projeto_id}>
                    {proj.projeto} ({proj.situacao} · SPI{' '}
                    {formatIndice(proj.spi)} · Falta SRE:{' '}
                    {Number(proj.dias_impacto_falta_sre)}d)
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {projetoSelecionado && (
              <p className="text-xs text-muted-foreground">
                Cliente: {projetoSelecionado.cliente} · Causa 90d:{' '}
                {formatCausa(projetoSelecionado.causa_mais_frequente)}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="input-onboarding">
              Horas de onboarding (mobilização)
            </Label>
            <Input
              id="input-onboarding"
              type="number"
              min={0}
              max={200}
              value={horasOnboarding}
              onChange={(e) =>
                setHorasOnboarding(Math.max(0, Number(e.target.value) || 0))
              }
            />
            <p className="text-xs text-muted-foreground">
              Padrão de 40 horas multiplicadas pelo custo/hora do profissional.
            </p>
          </div>
        </CardContent>
      </Card>

      {simulacao && pessoaSelecionada && projetoSelecionado && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Horas no mês (× 4 sem.)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {Math.round(simulacao.horasNoMes)} h
                </div>
                <p className="text-xs text-muted-foreground">
                  {simulacao.horasNoMes.toLocaleString('pt-BR', {
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                  })}{' '}
                  h disponíveis no mês
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Ociosidade evitada
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatBRLMilhoes(simulacao.ociosidadeEvitada)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {brlCompact.format(simulacao.ociosidadeEvitada)} que deixam de
                  ser perdidos
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Cronograma recuperado
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {simulacao.diasRecuperados.toLocaleString('pt-BR', {
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                  })}{' '}
                  dias
                </div>
                <p className="text-xs text-muted-foreground">
                  Base: {simulacao.diasImpacto90d}d de impacto em 90 dias
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Custo de mobilização
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatBRLMilhoes(simulacao.mobilizacao)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {horasOnboarding} h ×{' '}
                  {brlCompact.format(simulacao.custoHora)}/h
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Saldo líquido no mês
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatBRLMilhoes(simulacao.saldo)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {brlCompact.format(simulacao.saldo)} (ociosidade − onboarding)
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="pt-6">
              <details className="text-sm space-y-3 cursor-pointer">
                <summary className="font-semibold text-foreground">
                  Como calculamos o impacto desta realocação (memória de
                  cálculo)
                </summary>
                <div className="pt-3 space-y-2 text-muted-foreground cursor-default">
                  <p>
                    <strong>1. Horas no mês:</strong> média de horas ociosas por
                    semana nas últimas 12 semanas (
                    {simulacao.mediaHorasSemana.toLocaleString('pt-BR')} h/sem)
                    × 4 semanas ={' '}
                    <strong>
                      {simulacao.horasNoMes.toLocaleString('pt-BR', {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 1,
                      })}{' '}
                      h
                    </strong>{' '}
                    ({Math.round(simulacao.horasNoMes)} h).
                  </p>
                  <p>
                    <strong>2. Ociosidade que deixa de ser paga:</strong> custo
                    ocioso médio semanal (
                    {brlCompact.format(simulacao.mediaCustoSemana)}/sem) × 4
                    semanas ={' '}
                    <strong>
                      {brlCompact.format(simulacao.ociosidadeEvitada)}
                    </strong>{' '}
                    ({formatBRLMilhoes(simulacao.ociosidadeEvitada)}).
                  </p>
                  <p>
                    <strong>3. Dias de cronograma recuperados:</strong> soma dos
                    dias de impacto declarados no status por{' '}
                    <code>{simulacao.causaAlvo}</code> nos últimos 90 dias no
                    projeto {projetoSelecionado.projeto_id} (
                    {simulacao.diasImpacto90d} dias) ÷ 90 × 30 dias ={' '}
                    <strong>
                      {simulacao.diasRecuperados.toLocaleString('pt-BR', {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 1,
                      })}{' '}
                      dias
                    </strong>
                    .
                  </p>
                  <p>
                    <strong>4. Mobilização (onboarding):</strong> horas de
                    onboarding ({horasOnboarding} h) × custo/hora de{' '}
                    {pessoaSelecionada.nome} (
                    {brlCompact.format(simulacao.custoHora)}/h) ={' '}
                    <strong>{brlCompact.format(simulacao.mobilizacao)}</strong>{' '}
                    ({formatBRLMilhoes(simulacao.mobilizacao)}).
                  </p>
                  <p>
                    <strong>5. Saldo no 1º mês:</strong> ociosidade evitada (
                    {brlCompact.format(simulacao.ociosidadeEvitada)}) −
                    mobilização ({brlCompact.format(simulacao.mobilizacao)}) ={' '}
                    <strong>{brlCompact.format(simulacao.saldo)}</strong> (
                    {formatBRLMilhoes(simulacao.saldo)}).
                  </p>
                </div>
              </details>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function TelaPerguntar({
  usuario,
}: {
  usuario: { email?: string; user?: string } | null;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Perguntar ao Farol</h2>
          <p className="text-sm text-muted-foreground">
            Consulte a carteira de projetos em linguagem natural via agente Genie{' '}
            <strong>Farol · Diretoria</strong>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {usuario?.email ?? 'dev@vertice.com'}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            OBO: genie
          </Badge>
        </div>
      </div>

      <Alert>
        <ShieldCheck className="h-4 w-4" />
        <AlertTitle>Padrão de Governança e Confiança de IA</AlertTitle>
        <AlertDescription className="text-xs space-y-1">
          <p>
            • <strong>Identidade e Governança:</strong> As consultas executam com
            as suas permissões reais de acesso no Unity Catalog (on-behalf-of
            com escopo <code>genie</code>).
          </p>
          <p>
            • <strong>Transparência do SQL:</strong> Cada resposta traz as
            consultas SQL geradas para conferência antes de qualquer decisão.
          </p>
          <p>
            • <strong>Aviso fixo:</strong> Respostas geradas por IA a partir dos
            dados do Farol (fotografia de 16/10/2026).
          </p>
        </AlertDescription>
      </Alert>

      <Card className="border shadow-sm overflow-hidden">
        <CardContent className="p-4">
          <div style={{ height: 600 }} className="w-full flex flex-col">
            <GenieChat
              alias="default"
              placeholder="Ex: Quais projetos estão atrasados? Quanto esse atraso vai me custar?"
              className="h-full w-full"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">
            Exemplos de perguntas para o dono e diretoria
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
            <li>Quais projetos estão atrasados, e de quais clientes?</li>
            <li>Quanto esse atraso vai me custar?</li>
            <li>Tenho gente parada enquanto outro projeto pede gente?</li>
            <li>O que vai dar errado no próximo mês?</li>
            <li>Qual a chance de o PRJ-024 estourar?</li>
            <li>Qual é o SPI e CPI da carteira em andamento?</li>
            <li>Qual fornecedor mais atrasa as entregas?</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
