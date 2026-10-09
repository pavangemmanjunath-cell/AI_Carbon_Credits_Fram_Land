/**
 * The API is developed in parallel with the UI, so every list or object that may be
 * omitted is defaulted here once. Components can then rely on arrays being arrays.
 * Nothing is computed or invented: missing text stays empty, `certified` stays false.
 */
import type {
  AgentMessage,
  AgentRun,
  AgentRunListItem,
  AgentStep,
  Guardrail,
  RawAgentRun,
} from '../types';

const asArray = <T>(value: T[] | null | undefined): T[] => (Array.isArray(value) ? value : []);

function normalizeMessage(raw: Partial<AgentMessage>, index: number): AgentMessage {
  return {
    id: raw.id ?? `M${index + 1}`,
    step: typeof raw.step === 'number' ? raw.step : 0,
    agent: raw.agent ?? 'coordinator',
    agent_title: raw.agent_title ?? '',
    to: raw.to ?? null,
    kind: raw.kind ?? 'finding',
    text: raw.text ?? '',
    facts: raw.facts && typeof raw.facts === 'object' ? raw.facts : {},
    tool_calls: asArray(raw.tool_calls).map((call) => ({
      tool: call.tool,
      status: call.status ?? 'ok',
      duration_ms: call.duration_ms ?? null,
      input: call.input ?? null,
      output: call.output ?? null,
    })),
    evidence: asArray(raw.evidence),
    confidence: raw.confidence ?? null,
    created_at: raw.created_at ?? '',
  };
}

function normalizeStep(raw: Partial<AgentStep>, index: number): AgentStep {
  return {
    step: typeof raw.step === 'number' ? raw.step : index + 1,
    agent: raw.agent ?? 'coordinator',
    status: raw.status ?? 'done',
    duration_ms: raw.duration_ms ?? null,
    summary: raw.summary ?? '',
  };
}

function normalizeGuardrail(raw: Partial<Guardrail>): Guardrail {
  return { id: raw.id ?? 'unknown', status: raw.status ?? 'pass', detail: raw.detail ?? '' };
}

export function normalizeRun(raw: RawAgentRun): AgentRun {
  return {
    run_id: raw.run_id,
    plot_id: raw.plot_id ?? '',
    plan: {
      id: raw.plan?.id ?? 'unknown',
      title: raw.plan?.title ?? raw.plan?.id ?? '',
      steps: asArray(raw.plan?.steps),
    },
    status: raw.status ?? 'completed',
    reasoner: {
      mode: raw.reasoner?.mode ?? 'template',
      llm_enabled: raw.reasoner?.llm_enabled ?? false,
      provider: raw.reasoner?.provider ?? null,
    },
    started_at: raw.started_at ?? '',
    finished_at: raw.finished_at ?? '',
    duration_ms: raw.duration_ms ?? null,
    steps: asArray(raw.steps).map(normalizeStep),
    messages: asArray(raw.messages).map(normalizeMessage),
    summary: raw.summary
      ? {
          headline: raw.summary.headline ?? '',
          estimate: raw.summary.estimate ?? null,
          readiness: raw.summary.readiness ?? null,
          next_steps: asArray(raw.summary.next_steps),
          certified: false,
        }
      : null,
    guardrails: asArray(raw.guardrails).map(normalizeGuardrail),
    certified: false,
    disclaimer: raw.disclaimer ?? '',
    provenance: raw.provenance,
  };
}

/** `GET /agents/runs?plot_id=` may answer with a bare array or `{ items: [...] }`. */
export function normalizeRunList(raw: unknown): AgentRunListItem[] {
  const list: unknown = Array.isArray(raw) ? raw : (raw as { items?: unknown } | null)?.items;
  if (!Array.isArray(list)) return [];
  return list.filter(
    (item): item is AgentRunListItem =>
      Boolean(item) &&
      typeof item === 'object' &&
      typeof (item as AgentRunListItem).run_id === 'string',
  );
}

/** Newest first by `started_at`; items without a timestamp keep the server order after dated ones. */
export function sortRunsNewestFirst(items: AgentRunListItem[]): AgentRunListItem[] {
  const time = (item: AgentRunListItem): number => {
    const parsed = item.started_at ? Date.parse(item.started_at) : Number.NaN;
    return Number.isNaN(parsed) ? Number.NEGATIVE_INFINITY : parsed;
  };
  return items
    .map((item, index) => ({ item, index }))
    .sort((a, b) => time(b.item) - time(a.item) || a.index - b.index)
    .map(({ item }) => item);
}
