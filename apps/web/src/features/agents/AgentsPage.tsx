import './i18n';
import { useMemo, useState } from 'react';
import {
  CircleAlert,
  CircleCheck,
  ExternalLink,
  LoaderCircle,
  MapPin,
  Play,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { Button, LinkButton } from '@/components/ui/Button';
import { formatArea, intlLocale } from '@/lib/format';
import {
  useAgentCatalog,
  useAgentRun,
  useAgentRuns,
  useAskAgents,
  useRunAgents,
} from '@/services/agentsApi';
import { usePlots } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import { AskBox } from './components/AskBox';
import { Badge } from './components/Badge';
import { ErrorNotice } from './components/ErrorNotice';
import { Explainer } from './components/Explainer';
import { GuardrailsStrip } from './components/GuardrailsStrip';
import { MessageBubble } from './components/MessageBubble';
import { PlanPicker } from './components/PlanPicker';
import { ReasonerBadge } from './components/ReasonerBadge';
import { SummaryPanel } from './components/SummaryPanel';
import { TeamPipeline } from './components/TeamPipeline';
import { TranscriptSkeleton } from './components/TranscriptSkeleton';
import {
  AGENTS_DOCS_URL,
  filterMessagesByAgent,
  findSummaryMessage,
  formatDuration,
  formatRunDate,
  groupMessagesByStep,
  pipelineRows,
  planAgentIds,
  resolvePlanId,
  resolvePlotId,
} from './logic/agentsLogic';
import { sortRunsNewestFirst } from './logic/normalizeRun';
import { useAgentNames } from './useAgentNames';

interface LastAsk {
  runId: string;
  question: string;
}

export default function AgentsPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const language = useUiStore((s) => s.language);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const storedPlotId = useUiStore((s) => s.selectedPlotId);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);

  // ── Which plot ────────────────────────────────────────────────────────────
  const plotsQuery = usePlots();
  const plots = useMemo(() => plotsQuery.data?.items ?? [], [plotsQuery.data]);
  const plotId = resolvePlotId(
    params.get('plot'),
    storedPlotId,
    plots.map((p) => p.plot_id),
  );
  const plot = plots.find((p) => p.plot_id === plotId) ?? null;
  const locale = intlLocale(language, plot?.country);

  // ── Which plan ────────────────────────────────────────────────────────────
  const catalogQuery = useAgentCatalog();
  const catalog = catalogQuery.data ?? null;
  const [wantedPlan, setWantedPlan] = useState<string | null>(null);
  const planId = resolvePlanId(catalog?.plans, wantedPlan);
  const selectedPlan = catalog?.plans.find((p) => p.id === planId) ?? null;

  // ── Which run is on screen ────────────────────────────────────────────────
  const runsQuery = useAgentRuns(plotId);
  const runList = useMemo(() => sortRunsNewestFirst(runsQuery.data ?? []), [runsQuery.data]);
  const [chosenRunId, setChosenRunId] = useState<string | null>(null);
  const activeRunId = chosenRunId ?? runList[0]?.run_id ?? null;
  const runQuery = useAgentRun(activeRunId);
  const loadedRun = runQuery.data ?? null;
  const run = loadedRun && (!loadedRun.plot_id || loadedRun.plot_id === plotId) ? loadedRun : null;
  const [lastAsk, setLastAsk] = useState<LastAsk | null>(null);
  const [agentFilter, setAgentFilter] = useState<string | null>(null);

  // ── Actions ───────────────────────────────────────────────────────────────
  const runMutation = useRunAgents();
  const askMutation = useAskAgents();
  const pending = runMutation.isPending || askMutation.isPending;
  const actionError = runMutation.error ?? askMutation.error;

  const showRun = (runId: string, ask: LastAsk | null) => {
    setChosenRunId(runId);
    setAgentFilter(null);
    setLastAsk(ask);
  };
  const startRun = () => {
    if (!plotId || pending) return;
    askMutation.reset();
    runMutation.mutate(
      { plotId, body: { plan: planId, question: null, locale: language } },
      { onSuccess: (result) => showRun(result.run_id, null) },
    );
  };
  const ask = (question: string) => {
    if (!plotId || pending) return;
    runMutation.reset();
    askMutation.mutate(
      { question, plot_id: plotId, locale: language },
      { onSuccess: (result) => showRun(result.run_id, { runId: result.run_id, question }) },
    );
  };
  const choosePlot = (id: string) => {
    setSelectedPlotId(id);
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.set('plot', id);
        return next;
      },
      { replace: true },
    );
    setChosenRunId(null);
    setAgentFilter(null);
    setLastAsk(null);
    runMutation.reset();
    askMutation.reset();
  };
  const chooseEarlierRun = (runId: string) => {
    runMutation.reset();
    askMutation.reset();
    showRun(runId, null);
  };

  // ── What the Team column shows ────────────────────────────────────────────
  const names = useAgentNames(catalog?.agents, run?.messages);
  // While a run is requested the team of the chosen plan is shown, waiting to start.
  const shownPlan = !pending && run?.plan.steps.length ? run.plan : selectedPlan;
  const teamSteps = shownPlan?.steps ?? [];
  const rows = pipelineRows({ planSteps: teamSteps, run: pending ? null : run, pending });
  const filter = agentFilter && rows.some((r) => r.agent === agentFilter) ? agentFilter : null;
  const teamPlanTitle = shownPlan
    ? t(`agentsPage.plans.${shownPlan.id}.title`, { defaultValue: shownPlan.title })
    : '';

  // ── Early states ──────────────────────────────────────────────────────────
  const noPlots = plotsQuery.isSuccess && plots.length === 0;
  const header = (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex max-w-[780px] flex-col gap-1.5">
        <nav
          aria-label={t('agentsPage.breadcrumbLabel')}
          className="flex items-center gap-2 text-[13px] text-muted"
        >
          <Link to="/app" className="text-ink-2 no-underline hover:text-forest">
            {t('agentsPage.breadcrumbWorkspace')}
          </Link>
          <span aria-hidden="true">›</span>
          <span className="font-semibold text-ink">{t('agentsPage.title')}</span>
        </nav>
        <h1 className="m-0 text-[28px] tracking-tight">{t('agentsPage.title')}</h1>
        <p className="m-0 text-sm text-ink-2">{t('agentsPage.subtitle')}</p>
      </div>
      <LinkButton to={AGENTS_DOCS_URL} external variant="secondary" size="sm">
        {t('agentsPage.learnLink')}
        <ExternalLink size={14} aria-hidden="true" />
        <span className="sr-only">({t('agentsPage.opensNewTab')})</span>
      </LinkButton>
    </header>
  );

  if (noPlots) {
    return (
      <div className="mx-auto flex max-w-[1440px] flex-col gap-5 p-4 md:p-5">
        {header}
        <div className="card flex flex-col items-start gap-3 p-6">
          <span className="grid h-11 w-11 place-items-center rounded-full bg-mint text-forest-deep">
            <MapPin size={22} aria-hidden="true" />
          </span>
          <h2 className="m-0 text-[18px]">{t('agentsPage.emptyTitle')}</h2>
          <p className="m-0 max-w-[560px] text-sm leading-relaxed text-ink-2">
            {t('agentsPage.emptyBody')}
          </p>
          <LinkButton to="/app">{t('agentsPage.emptyAction')}</LinkButton>
        </div>
        <Explainer />
      </div>
    );
  }

  // ── Conversation ──────────────────────────────────────────────────────────
  const llmOn = run ? run.reasoner.mode === 'llm' : Boolean(catalog?.framework.llm_enabled);
  const provider = run?.reasoner.provider ?? null;
  const summaryMessage = run ? findSummaryMessage(run.messages) : null;
  const visibleMessages = run ? filterMessagesByAgent(run.messages, filter) : [];
  const summaryShown =
    !!run &&
    (summaryMessage
      ? visibleMessages.some((m) => m.id === summaryMessage.id)
      : !!run.summary && (filter === null || filter === 'coordinator'));
  const showStandaloneSummary = !!run && !summaryMessage && summaryShown;
  const groups = groupMessagesByStep(visibleMessages);
  const failedSteps = run?.steps.filter((s) => s.status === 'failed') ?? [];
  // Position of each bubble in the transcript; only used to stagger the entrance animation.
  const positionById = new Map(visibleMessages.map((m, position) => [m.id, position]));

  const statusBadge = run ? (
    run.status === 'failed' ? (
      <Badge tone="rose">
        <CircleAlert size={12} aria-hidden="true" />
        {t('agentsPage.runStatus.failed')}
      </Badge>
    ) : run.status === 'completed-with-warnings' ? (
      <Badge tone="amber">
        <TriangleAlert size={12} aria-hidden="true" />
        {t('agentsPage.runStatus.completed-with-warnings')}
      </Badge>
    ) : run.status === 'running' ? (
      <Badge tone="blue">
        <LoaderCircle size={12} aria-hidden="true" className="animate-spin" />
        {t('agentsPage.runStatus.running')}
      </Badge>
    ) : (
      <Badge tone="mint">
        <CircleCheck size={12} aria-hidden="true" />
        {t('agentsPage.runStatus.completed')}
      </Badge>
    )
  ) : null;

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 p-4 md:p-5">
      {header}

      {/* Plot · plan · run */}
      <section
        aria-label={t('agentsPage.setupLabel')}
        className="card flex flex-col gap-4 p-4 md:p-5"
      >
        <div className="flex flex-wrap items-end gap-3 md:gap-4">
          <label className="flex min-w-[240px] flex-1 flex-col gap-1.5 text-[12px] font-medium text-ink-2 md:max-w-[440px]">
            {t('agentsPage.plot')}
            <select
              className="field-input h-11 text-[14px] font-semibold"
              value={plotId ?? ''}
              disabled={plots.length === 0 || pending}
              onChange={(event) => choosePlot(event.target.value)}
            >
              {plots.map((p) => (
                <option key={p.plot_id} value={p.plot_id}>
                  {p.name} · {formatArea(p.area_hectares, p.country, locale, areaUnit).primary}
                </option>
              ))}
              {plots.length === 0 && <option value="">{t('agentsPage.loadingPlots')}</option>}
            </select>
          </label>
          <div className="flex flex-wrap items-center gap-3 md:ml-auto">
            <ReasonerBadge llm={llmOn} provider={provider} />
            <Button
              size="lg"
              onClick={startRun}
              disabled={!plotId || !selectedPlan || pending}
              className="w-full sm:w-auto"
            >
              {pending ? (
                <LoaderCircle size={17} aria-hidden="true" className="animate-spin" />
              ) : (
                <Play size={17} aria-hidden="true" />
              )}
              {pending ? t('agentsPage.runningShort') : t('agentsPage.run')}
            </Button>
          </div>
        </div>

        {catalog ? (
          <PlanPicker
            plans={catalog.plans}
            value={planId}
            onChange={setWantedPlan}
            names={names}
            disabled={pending}
          />
        ) : catalogQuery.error ? (
          <ErrorNotice error={catalogQuery.error} onRetry={() => void catalogQuery.refetch()} />
        ) : (
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <span key={i} className="skeleton h-[104px] rounded-[12px]" />
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[330px_minmax(0,1fr)]">
        <TeamPipeline
          rows={rows}
          planTitle={teamPlanTitle}
          selected={filter}
          onSelect={setAgentFilter}
          names={names}
          catalogAgents={catalog?.agents}
          locale={locale}
        />

        <section
          aria-label={t('agentsPage.conversationTitle')}
          className="flex min-w-0 flex-col gap-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <h2 className="m-0 text-[18px]">{t('agentsPage.conversationTitle')}</h2>
              {statusBadge}
              {run && (
                <span className="font-mono text-[12px] text-muted">
                  {[formatRunDate(run.started_at, locale), formatDuration(run.duration_ms, locale)]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              )}
            </div>
            {runList.length > 1 && (
              <label className="flex items-center gap-2 text-[12px] text-ink-2">
                {t('agentsPage.earlierRuns')}
                <select
                  className="field-input h-9 w-auto max-w-[250px] text-[13px]"
                  value={activeRunId ?? ''}
                  disabled={pending}
                  onChange={(event) => chooseEarlierRun(event.target.value)}
                >
                  {runList.map((item) => (
                    <option key={item.run_id} value={item.run_id}>
                      {[
                        item.plan?.id
                          ? t(`agentsPage.plans.${item.plan.id}.title`, {
                              defaultValue: item.plan.title ?? item.plan.id,
                            })
                          : item.run_id,
                        formatRunDate(item.started_at, locale),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          {actionError != null && <ErrorNotice error={actionError} onRetry={startRun} />}
          {!actionError && runQuery.error != null && !pending && (
            <ErrorNotice error={runQuery.error} />
          )}
          {run?.status === 'failed' && (
            <div
              role="alert"
              className="rounded-[12px] bg-rose-50 p-4 text-[13.5px] leading-relaxed text-rose-900"
            >
              <p className="m-0 font-semibold">{t('agentsPage.runFailed')}</p>
              {failedSteps.map((step) => (
                <p key={`${step.step}-${step.agent}`} className="m-0">
                  {names.title(step.agent)}: {step.summary}
                </p>
              ))}
            </div>
          )}

          {run && !pending && <GuardrailsStrip guardrails={run.guardrails} />}

          <div className="card flex flex-col gap-4 p-4 md:p-5">
            {filter && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-[10px] bg-mint px-3 py-2 text-[13px] text-forest-deep">
                <span>{t('agentsPage.showingOnly', { agent: names.title(filter) })}</span>
                <button
                  type="button"
                  onClick={() => setAgentFilter(null)}
                  className="font-semibold underline underline-offset-2"
                >
                  {t('agentsPage.showEveryone')}
                </button>
              </div>
            )}

            {pending ? (
              <TranscriptSkeleton agents={planAgentIds(teamSteps)} />
            ) : !run ? (
              <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
                <span className="grid h-11 w-11 place-items-center rounded-full bg-mint text-forest-deep">
                  <Sparkles size={21} aria-hidden="true" />
                </span>
                <p className="m-0 text-[15px] font-semibold text-ink">
                  {t('agentsPage.noRunTitle')}
                </p>
                <p className="m-0 max-w-[440px] text-[13.5px] leading-relaxed text-ink-2">
                  {t('agentsPage.noRunBody')}
                </p>
              </div>
            ) : (
              <div
                role="log"
                aria-label={t('agentsPage.conversationTitle')}
                aria-live={filter ? 'off' : 'polite'}
                className="flex flex-col gap-5"
              >
                {lastAsk && lastAsk.runId === run.run_id && (
                  <div className="flex justify-end">
                    <p className="m-0 max-w-[88%] rounded-[12px] rounded-tr-[4px] bg-panel-dark px-4 py-2.5 text-[15px] leading-relaxed text-white">
                      <span className="sr-only">{t('agentsPage.you')}: </span>
                      {lastAsk.question}
                    </p>
                  </div>
                )}
                {groups.length === 0 && (
                  <p className="m-0 text-[13.5px] text-muted">
                    {t('agentsPage.noMessagesForAgent')}
                  </p>
                )}
                {groups.map((group, groupIndex) => (
                  <div
                    key={`${group.step}-${group.agent}-${groupIndex}`}
                    className="flex flex-col gap-3"
                  >
                    {group.step > 0 && (
                      <p className="m-0 font-mono text-[11px] uppercase tracking-[0.08em] text-muted">
                        {t('agentsPage.stepLabel', { step: group.step })}
                      </p>
                    )}
                    {group.messages.map((message) =>
                      message.id === summaryMessage?.id ? (
                        <SummaryPanel
                          key={message.id}
                          message={message}
                          summary={run.summary}
                          names={names}
                          locale={locale}
                        />
                      ) : (
                        <MessageBubble
                          key={message.id}
                          message={message}
                          names={names}
                          locale={locale}
                          index={positionById.get(message.id) ?? 0}
                        />
                      ),
                    )}
                  </div>
                ))}
                {showStandaloneSummary && (
                  <SummaryPanel
                    message={null}
                    summary={run.summary}
                    names={names}
                    locale={locale}
                  />
                )}
              </div>
            )}

            {run && !pending && !summaryShown && run.disclaimer && (
              <p className="m-0 flex items-start gap-2 text-[12.5px] leading-snug text-amber-text">
                <TriangleAlert size={14} aria-hidden="true" className="mt-0.5 shrink-0" />
                {run.disclaimer}
              </p>
            )}
          </div>

          <AskBox onAsk={ask} disabled={!plotId} busy={pending} />
        </section>
      </div>

      <Explainer />
    </div>
  );
}
