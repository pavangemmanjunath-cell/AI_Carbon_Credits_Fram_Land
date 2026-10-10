/**
 * Types for the agentic AI framework (`/agents`, `/plots/{id}/agents/run`,
 * `/agents/ask`, `/agents/runs`). They mirror the "v0.2 additions → Agents"
 * section of docs/architecture/api-contract.md. Field names stay snake_case
 * exactly as on the wire.
 */
import type { Confidence, CostInputs, Provenance, Range } from '@/types/api';

/** The nine agents in the contract. Any other id is still rendered (generic avatar). */
export type KnownAgentId =
  | 'coordinator'
  | 'land'
  | 'imagery'
  | 'trees'
  | 'carbon'
  | 'policy'
  | 'market'
  | 'review'
  | 'report';
export type AgentId = KnownAgentId | (string & {});

/** The three plans in the contract. Any other id is still rendered. */
export type KnownPlanId = 'full-assessment' | 'quick-estimate' | 'tree-age-check';
export type PlanId = KnownPlanId | (string & {});

// ─── GET /agents ─────────────────────────────────────────────────────────────

export interface AgentTool {
  name: string;
  description: string;
}

export interface AgentInfo {
  id: AgentId;
  title: string;
  role: string;
  /** "what this agent reports" */
  says: string;
  tools: AgentTool[];
  reads: string[];
  writes: string[];
}

export interface AgentPlanInfo {
  id: PlanId;
  title: string;
  /** Ordered agent ids; the coordinator appears first and last. */
  steps: AgentId[];
  /** Not in the contract today; used when the API provides one. */
  description?: string;
}

export interface AgentFramework {
  name: string;
  version: string;
  reasoner: 'template' | 'llm' | (string & {});
  llm_enabled: boolean;
}

export interface AgentCatalog {
  framework: AgentFramework;
  agents: AgentInfo[];
  plans: AgentPlanInfo[];
}

// ─── AgentRun ────────────────────────────────────────────────────────────────

/** `running` is not in the contract today; it is handled so a streaming API would still render. */
export type RunStatus = 'completed' | 'completed-with-warnings' | 'failed' | 'running';
export type StepStatus = 'done' | 'warning' | 'skipped' | 'failed';
/** What the Team column shows for one agent. */
export type PipelineStatus = 'pending' | 'running' | 'done' | 'warning' | 'failed' | 'skipped';
export type MessageKind = 'plan' | 'finding' | 'warning' | 'handoff' | 'answer' | 'summary';
export type ToolCallStatus = 'ok' | 'error' | 'skipped';
export type GuardrailStatus = 'pass' | 'warn' | 'fail';

/** Tool `input`/`output` are summaries: never coordinates or geometry. */
export interface AgentToolCall {
  tool: string;
  status: ToolCallStatus;
  duration_ms: number | null;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
}

export interface AgentEvidence {
  label: string;
  source?: string | null;
  url?: string | null;
}

export interface AgentMessage {
  id: string;
  step: number;
  agent: AgentId;
  agent_title: string;
  /** `team`, an agent id (hand-offs) or null. */
  to: string | null;
  kind: MessageKind;
  text: string;
  facts: Record<string, unknown>;
  tool_calls: AgentToolCall[];
  evidence: AgentEvidence[];
  confidence: Confidence | null;
  created_at: string;
}

export interface AgentStep {
  step: number;
  agent: AgentId;
  status: StepStatus;
  duration_ms: number | null;
  summary: string;
}

export interface AgentRunSummary {
  headline: string;
  estimate: Range | null;
  /** 0–100 programme-readiness score. */
  readiness: number | null;
  next_steps: string[];
  /** Always false: an estimate is never a credit. */
  certified: boolean;
}

export interface Guardrail {
  id: string;
  status: GuardrailStatus;
  detail: string;
}

export interface AgentReasoner {
  mode: 'template' | 'llm' | (string & {});
  llm_enabled: boolean;
  provider: string | null;
}

export interface AgentRunPlan {
  id: PlanId;
  title: string;
  steps: AgentId[];
}

export interface AgentRun {
  run_id: string;
  plot_id: string;
  plan: AgentRunPlan;
  status: RunStatus;
  reasoner: AgentReasoner;
  started_at: string;
  finished_at: string;
  duration_ms: number | null;
  steps: AgentStep[];
  messages: AgentMessage[];
  summary: AgentRunSummary | null;
  guardrails: Guardrail[];
  certified: false;
  disclaimer: string;
  provenance?: Provenance;
}

/** What `GET /agents/runs?plot_id=` returns per run ("summaries"); every field but the id is optional. */
export interface AgentRunListItem {
  run_id: string;
  plot_id?: string;
  plan?: { id: PlanId; title?: string };
  status?: RunStatus;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number | null;
  headline?: string | null;
}

// ─── Request bodies ──────────────────────────────────────────────────────────

export interface AgentRunBody {
  plan: PlanId;
  question?: string | null;
  locale?: string;
}

export interface AgentAskBody {
  question: string;
  plot_id: string;
  locale?: string;
  /** Your own costs; the Market agent then adds a break-even carbon price. */
  costs?: CostInputs;
}

// ─── Raw wire shapes (everything optional → normalised by `normalizeRun`) ────

export interface RawAgentRun {
  run_id: string;
  plot_id?: string;
  plan?: Partial<AgentRunPlan> | null;
  status?: RunStatus;
  reasoner?: Partial<AgentReasoner> | null;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number | null;
  steps?: Partial<AgentStep>[] | null;
  messages?: Partial<AgentMessage>[] | null;
  summary?: Partial<AgentRunSummary> | null;
  guardrails?: Partial<Guardrail>[] | null;
  disclaimer?: string;
  provenance?: Provenance;
}
