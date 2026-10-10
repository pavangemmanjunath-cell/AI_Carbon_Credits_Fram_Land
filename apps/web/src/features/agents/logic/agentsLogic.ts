/**
 * Pure helpers for the AI-agents page. Nothing here fetches, renders or calls an
 * engine: it only groups, orders and formats what the API already returned.
 */
import type {
  AgentInfo,
  AgentMessage,
  AgentPlanInfo,
  AgentRun,
  Guardrail,
  GuardrailStatus,
  MessageKind,
  PipelineStatus,
  StepStatus,
} from '../types';

export const MAX_QUESTION_LENGTH = 500;
export const DEFAULT_PLAN_ID = 'full-assessment';
export const AGENTS_DOCS_URL =
  'https://github.com/pavangemmanjunath-cell/Carbon_Credits_Fram_Land/blob/main/docs/agents/README.md';

export const SUGGESTED_QUESTION_KEYS = ['carbon', 'programmes', 'plant', 'old'] as const;
export type SuggestionKey = (typeof SUGGESTED_QUESTION_KEYS)[number];

// ─── Agent visuals ───────────────────────────────────────────────────────────

export type AgentIconKey =
  'compass' | 'map' | 'satellite' | 'tree' | 'leaf' | 'scale' | 'coins' | 'shield' | 'file' | 'bot';
export type AgentTone =
  'indigo' | 'amber' | 'blue' | 'green' | 'teal' | 'violet' | 'yellow' | 'rose' | 'slate';

export interface AgentVisual {
  icon: AgentIconKey;
  tone: AgentTone;
}

const AGENT_VISUALS: Record<string, AgentVisual> = {
  coordinator: { icon: 'compass', tone: 'indigo' },
  land: { icon: 'map', tone: 'amber' },
  imagery: { icon: 'satellite', tone: 'blue' },
  trees: { icon: 'tree', tone: 'green' },
  carbon: { icon: 'leaf', tone: 'teal' },
  policy: { icon: 'scale', tone: 'violet' },
  market: { icon: 'coins', tone: 'yellow' },
  review: { icon: 'shield', tone: 'rose' },
  report: { icon: 'file', tone: 'slate' },
};

/** Icon + soft colour for an agent. Unknown agents get a neutral robot so nothing breaks. */
export function agentVisual(agentId: string): AgentVisual {
  return AGENT_VISUALS[agentId] ?? { icon: 'bot', tone: 'slate' };
}

export function isKnownAgent(agentId: string): boolean {
  return agentId in AGENT_VISUALS;
}

/** "land_use" → "Land use"; a few acronyms stay upper-case. */
const ACRONYMS = new Set([
  'ndvi',
  'ndmi',
  'ndre',
  'dbh',
  'gcp',
  'ccts',
  'crcf',
  'llm',
  'api',
  'id',
]);
export function humanizeKey(key: string): string {
  const words = key
    .replace(/[_\-.]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => (ACRONYMS.has(word.toLowerCase()) ? word.toUpperCase() : word.toLowerCase()));
  if (words.length === 0) return '';
  const [first, ...rest] = words;
  const head = ACRONYMS.has(first.toLowerCase())
    ? first
    : first.charAt(0).toUpperCase() + first.slice(1);
  return [head, ...rest].join(' ');
}

/**
 * Display name for an agent id: translated title (if the caller has one) → catalog title →
 * the `agent_title` carried by a message → a humanised id.
 */
export function agentTitle(
  agentId: string,
  sources: { catalog?: AgentInfo[]; messages?: AgentMessage[]; translated?: string | null } = {},
): string {
  if (sources.translated) return sources.translated;
  const fromCatalog = sources.catalog?.find((a) => a.id === agentId)?.title;
  if (fromCatalog) return fromCatalog;
  const fromMessage = sources.messages?.find(
    (m) => m.agent === agentId && m.agent_title,
  )?.agent_title;
  if (fromMessage) return fromMessage;
  return humanizeKey(agentId) || agentId;
}

// ─── Plans and the Team column ───────────────────────────────────────────────

/** Unique agent ids in order of first appearance (the coordinator opens *and* closes a plan). */
export function planAgentIds(steps: string[]): string[] {
  return Array.from(new Set(steps));
}

export function resolvePlanId(plans: AgentPlanInfo[] | undefined, wanted: string | null): string {
  if (!plans || plans.length === 0) return wanted ?? DEFAULT_PLAN_ID;
  if (wanted && plans.some((p) => p.id === wanted)) return wanted;
  return plans.find((p) => p.id === DEFAULT_PLAN_ID)?.id ?? plans[0].id;
}

/** URL `?plot=` wins, then the stored selection, then the first plot. */
export function resolvePlotId(
  fromUrl: string | null,
  fromStore: string | null,
  plotIds: string[],
): string | null {
  if (fromUrl && plotIds.includes(fromUrl)) return fromUrl;
  if (fromStore && plotIds.includes(fromStore)) return fromStore;
  return plotIds[0] ?? null;
}

export interface PipelineRow {
  agent: string;
  status: PipelineStatus;
  durationMs: number | null;
  messageCount: number;
}

export function messageCountsByAgent(messages: AgentMessage[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const message of messages) counts[message.agent] = (counts[message.agent] ?? 0) + 1;
  return counts;
}

/** failed > warning > skipped (only when every step was skipped) > done. */
function aggregateStatus(statuses: StepStatus[]): PipelineStatus {
  if (statuses.includes('failed')) return 'failed';
  if (statuses.includes('warning')) return 'warning';
  if (statuses.every((s) => s === 'skipped')) return 'skipped';
  return 'done';
}

/**
 * One row per agent of the plan, in plan order.
 * - no run yet: everyone is pending (while a run is being requested the coordinator, who always
 *   starts first, is shown as running);
 * - with a run: the API's per-step status wins; an agent without a step falls back to its messages;
 *   the coordinator is not a worker step in the API, so it is done as soon as the run exists.
 */
export function pipelineRows(input: {
  planSteps: string[];
  run: AgentRun | null;
  pending: boolean;
}): PipelineRow[] {
  const { planSteps, run, pending } = input;
  const ids = planAgentIds(planSteps);
  const counts = messageCountsByAgent(run?.messages ?? []);
  let runningAssigned = false;

  return ids.map((agent, index) => {
    const messageCount = counts[agent] ?? 0;
    if (!run) {
      return {
        agent,
        status: pending && index === 0 ? 'running' : 'pending',
        durationMs: null,
        messageCount,
      };
    }
    const steps = run.steps.filter((s) => s.agent === agent);
    const durations = steps.map((s) => s.duration_ms).filter((d): d is number => d != null);
    const durationMs = durations.length ? durations.reduce((a, b) => a + b, 0) : null;

    if (steps.length) {
      return {
        agent,
        status: aggregateStatus(steps.map((s) => s.status)),
        durationMs,
        messageCount,
      };
    }
    if (messageCount > 0) {
      const warned = run.messages.some((m) => m.agent === agent && m.kind === 'warning');
      return { agent, status: warned ? 'warning' : 'done', durationMs, messageCount };
    }
    if (agent === 'coordinator') return { agent, status: 'done', durationMs, messageCount };
    if (run.status === 'running') {
      const status: PipelineStatus = runningAssigned ? 'pending' : 'running';
      runningAssigned = true;
      return { agent, status, durationMs, messageCount };
    }
    return { agent, status: 'skipped', durationMs, messageCount };
  });
}

// ─── Transcript ──────────────────────────────────────────────────────────────

export function filterMessagesByAgent(
  messages: AgentMessage[],
  agentId: string | null,
): AgentMessage[] {
  return agentId ? messages.filter((m) => m.agent === agentId) : messages;
}

export interface StepGroup {
  step: number;
  agent: string;
  messages: AgentMessage[];
}

/** Consecutive messages of the same step and agent form one group (order is preserved). */
export function groupMessagesByStep(messages: AgentMessage[]): StepGroup[] {
  const groups: StepGroup[] = [];
  for (const message of messages) {
    const last = groups[groups.length - 1];
    if (last && last.step === message.step && last.agent === message.agent)
      last.messages.push(message);
    else groups.push({ step: message.step, agent: message.agent, messages: [message] });
  }
  return groups;
}

export function groupMessagesByAgent(
  messages: AgentMessage[],
): { agent: string; messages: AgentMessage[] }[] {
  const order: string[] = [];
  const byAgent = new Map<string, AgentMessage[]>();
  for (const message of messages) {
    if (!byAgent.has(message.agent)) {
      byAgent.set(message.agent, []);
      order.push(message.agent);
    }
    byAgent.get(message.agent)?.push(message);
  }
  return order.map((agent) => ({ agent, messages: byAgent.get(agent) ?? [] }));
}

/** The message that is rendered as the forest-green panel: the last `summary`. */
export function findSummaryMessage(messages: AgentMessage[]): AgentMessage | null {
  for (let i = messages.length - 1; i >= 0; i -= 1)
    if (messages[i].kind === 'summary') return messages[i];
  return null;
}

/** A recipient chip ("→ Carbon agent") is shown only for a specific agent, not for the whole team. */
export function recipientAgentId(to: string | null | undefined): string | null {
  if (!to) return null;
  const lowered = to.toLowerCase();
  return lowered === 'team' || lowered === 'all' || lowered === 'user' ? null : to;
}

export type BadgeTone = 'blue' | 'mint' | 'amber' | 'grey' | 'forest' | 'dark' | 'rose';
export type KindIconKey = 'plan' | 'finding' | 'warning' | 'handoff' | 'answer' | 'summary';

export function kindStyle(kind: MessageKind | string): { tone: BadgeTone; icon: KindIconKey } {
  switch (kind) {
    case 'plan':
      return { tone: 'blue', icon: 'plan' };
    case 'warning':
      return { tone: 'amber', icon: 'warning' };
    case 'handoff':
      return { tone: 'grey', icon: 'handoff' };
    case 'answer':
      return { tone: 'forest', icon: 'answer' };
    case 'summary':
      return { tone: 'dark', icon: 'summary' };
    default:
      return { tone: 'mint', icon: 'finding' };
  }
}

export function guardrailTone(status: GuardrailStatus | string): {
  tone: BadgeTone;
  mark: '✓' | '!' | '✕';
} {
  if (status === 'fail') return { tone: 'rose', mark: '✕' };
  if (status === 'warn') return { tone: 'amber', mark: '!' };
  return { tone: 'mint', mark: '✓' };
}

/** The guardrail a person should see first: fail, then warn, otherwise none. */
export function firstAttentionGuardrail(guardrails: Guardrail[]): Guardrail | null {
  return (
    guardrails.find((g) => g.status === 'fail') ??
    guardrails.find((g) => g.status === 'warn') ??
    null
  );
}

// ─── Facts, tool summaries, links ────────────────────────────────────────────

const FACT_UNIT_SUFFIXES: [string, string][] = [
  ['_tco2e_yr', 'tCO₂e/yr'],
  ['_tco2e', 'tCO₂e'],
  ['_hectares', 'ha'],
  ['_acres', 'ac'],
  ['_years', 'years'],
  ['_percent', '%'],
  ['_m2', 'm²'],
  ['_pct', '%'],
  ['_cm', 'cm'],
  ['_ha', 'ha'],
  ['_kg', 'kg'],
  ['_m', 'm'],
];

/** `area_hectares` → { base: 'area', unit: 'ha' }; `ndvi` → { base: 'ndvi', unit: null }. */
export function splitFactKey(key: string): { base: string; unit: string | null } {
  const lowered = key.toLowerCase();
  for (const [suffix, unit] of FACT_UNIT_SUFFIXES) {
    if (lowered.endsWith(suffix) && lowered.length > suffix.length) {
      return { base: key.slice(0, key.length - suffix.length), unit };
    }
  }
  return { base: key, unit: null };
}

const HIDDEN_WORDS = new Set([
  'lat',
  'lon',
  'lng',
  'latitude',
  'longitude',
  'geometry',
  'geom',
  'coordinates',
  'coords',
  'polygon',
  'centroid',
  'bbox',
  'wkt',
  'geojson',
]);
/**
 * Defence in depth: the API never sends coordinates, and the page never shows them either. A key
 * is hidden when any word in it is a location word (`lat`, `centroid_lat`, `plotLon`, `bbox`).
 */
export function isHiddenKey(key: string): boolean {
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .some((word) => HIDDEN_WORDS.has(word));
}

function isRangeLike(value: unknown): value is { low: number; high: number; central?: number } {
  return (
    !!value &&
    typeof value === 'object' &&
    typeof (value as { low?: unknown }).low === 'number' &&
    typeof (value as { high?: unknown }).high === 'number'
  );
}

/** Adaptive precision so a single young tree (0.012 t) does not show as "0.0". */
export function formatQuantity(value: number, locale: string): string {
  if (!Number.isFinite(value)) return '—';
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 0 : abs >= 10 ? 1 : abs >= 0.1 ? 2 : 3;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(value);
}

/** Formats one fact value; returns null for values that should not become a chip (objects, null). */
export function formatFactValue(
  key: string,
  value: unknown,
  locale: string,
  labels: { yes: string; no: string } = { yes: 'yes', no: 'no' },
): string | null {
  if (value === null || value === undefined || value === '') return null;
  const { base, unit } = splitFactKey(key);
  if (typeof value === 'boolean') return value ? labels.yes : labels.no;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return null;
    if (!unit && /(share|fraction)$/i.test(base) && value >= 0 && value <= 1) {
      return new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 0 }).format(
        value,
      );
    }
    const text = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value);
    return unit ? `${text} ${unit}` : text;
  }
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    const items = value.filter((v) => typeof v === 'string' || typeof v === 'number').map(String);
    if (items.length === 0) return null;
    return items.length > 3
      ? `${items.slice(0, 3).join(', ')} +${items.length - 3}`
      : items.join(', ');
  }
  if (isRangeLike(value)) {
    const range = `${formatQuantity(value.low, locale)} – ${formatQuantity(value.high, locale)}`;
    const rangeUnit = (value as { unit?: unknown }).unit;
    return typeof rangeUnit === 'string' ? `${range} ${rangeUnit.replace('CO2', 'CO₂')}` : range;
  }
  return null;
}

export interface FactChip {
  key: string;
  base: string;
  value: string;
}

/** At most `max` compact chips; `hidden` is how many more facts exist. */
export function factChips(
  facts: Record<string, unknown> | null | undefined,
  locale: string,
  max = 6,
  labels?: { yes: string; no: string },
): { chips: FactChip[]; hidden: number } {
  const all: FactChip[] = [];
  for (const [key, raw] of Object.entries(facts ?? {})) {
    if (isHiddenKey(key)) continue;
    const value = formatFactValue(key, raw, locale, labels);
    if (value === null) continue;
    all.push({ key, base: splitFactKey(key).base, value });
  }
  return { chips: all.slice(0, max), hidden: Math.max(0, all.length - max) };
}

function compactValue(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return value.length > 48 ? `${value.slice(0, 47)}…` : value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) {
    const shown = value.slice(0, 4).map(compactValue).join(', ');
    return `[${shown}${value.length > 4 ? ', …' : ''}]`;
  }
  try {
    const json = JSON.stringify(value);
    return json.length > 60 ? `${json.slice(0, 59)}…` : json;
  } catch {
    return '…';
  }
}

/** "area_hectares=2.13, crs=EPSG:4326" — small mono text for tool inputs and outputs. */
export function summarizeRecord(
  record: Record<string, unknown> | null | undefined,
  max = 180,
): string {
  if (!record || typeof record !== 'object') return '';
  const parts = Object.entries(record).map(([key, value]) =>
    isHiddenKey(key) ? `${key}=[hidden]` : `${key}=${compactValue(value)}`,
  );
  const text = parts.join(', ');
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

/** Only http(s) links are rendered as links (a `javascript:` URL from any source is dropped). */
export function safeHttpUrl(url: unknown): string | null {
  if (typeof url !== 'string' || !url.trim()) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? url : null;
  } catch {
    return null;
  }
}

// ─── Time, questions ─────────────────────────────────────────────────────────

export function formatDuration(ms: number | null | undefined, locale = 'en'): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return '';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(ms / 1000);
  return `${seconds} s`;
}

export function formatClock(
  iso: string | null | undefined,
  locale: string,
  timeZone?: string,
): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone,
  }).format(date);
}

export function formatRunDate(
  iso: string | null | undefined,
  locale: string,
  timeZone?: string,
): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone,
  }).format(date);
}

export type QuestionCheck =
  { ok: true; question: string } | { ok: false; reason: 'empty' | 'too-long' };

export function validateQuestion(raw: string): QuestionCheck {
  const question = raw.trim();
  if (!question) return { ok: false, reason: 'empty' };
  if (question.length > MAX_QUESTION_LENGTH) return { ok: false, reason: 'too-long' };
  return { ok: true, question };
}
