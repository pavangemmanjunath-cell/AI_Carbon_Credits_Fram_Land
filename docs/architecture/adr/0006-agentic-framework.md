# ADR-0006: A small in-house agent framework — deterministic by default, LLM optional

- **Status:** accepted
- **Date:** 2026-10-05
- **Deciders:** project lead, back-end engineer
- **Builds on:** [ADR-0003](0003-deterministic-before-ai.md) (deterministic calculations first; language models
  explain, never compute)

## Context

Version 0.2 adds "agents": a team that looks at a plot, explains what the engines found, answers questions such
as "How much carbon if I add 200 trees?" and shows its work — who said what, which tools ran, which checks
passed ([API contract](../api-contract.md), section "Agents"). The project owner also wants the code to be a
place to *learn* how agentic systems are built.

The constraints are the project's non-negotiables ([CLAUDE.md](../../../CLAUDE.md)): estimates are never
credits, every number is a range with provenance, coordinates never reach a language model or a log, and a
language model never computes a number. The API runs offline in demo mode, in CI and on modest servers, and its
dependency list is pinned and short.

Popular agent frameworks were considered: LangGraph, CrewAI, AutoGen (AgentChat), PydanticAI, the OpenAI Agents
SDK and LangChain agents. They are good at what they are built for — letting a model decide which tool or agent
comes next — and they bring large dependency trees, fast-moving APIs and a default execution model in which
every step calls an LLM.

## Decision

1. **A small framework of our own, `atlas_agents`**
   ([packages/agent-framework](../../../packages/agent-framework/README.md)): agents, tools, a blackboard,
   plans, an orchestrator, reasoners, guardrails, a trace and a keyword intent router — about 2,900 lines
   including docstrings and the keyword table, with no third-party dependency (`httpx` only for the optional
   LLM client) and no knowledge of carbon. The AgriCarbon team lives in `apps/api/app/agents/`.
2. **Deterministic by default.** Plans are data written by people; each agent's `run` method is ordinary
   Python; tools call the existing services and engines. The default `TemplateReasoner` keeps each agent's
   template text, so the same inputs give the same transcript.
3. **The LLM is optional and can only rephrase.** With `ATLAS_AGENT_REASONER=llm` and an OpenAI-compatible
   endpoint configured, `LLMReasoner` may reword findings, answers and summaries from redacted text and facts.
   Its answer is used only when every number still matches the template or the engine facts, nothing
   coordinate-like appears and no sentence presents an estimate as a credit; otherwise the template is kept and
   the `llm-rephrase` guardrail warns. Safety sentences ("not a carbon credit") are appended after narration
   and never sent to the model.
4. **Guardrails on every run.** `not-a-credit`, `uncertainty-present`, `provenance-present`, `no-coordinates`
   (including this plot's own centroid and bbox digits), `pending-parameters` and `values-separated` run after
   the last step; a failure marks the run `failed`.
5. **Runs are records.** Each run is stored through the generic repository record API (`kind="agent-run"`,
   linked to the plot) with its transcript, steps, guardrails, summary and provenance.

## Consequences

Positive:

- Every agent statement can be traced to a tool call, a service and a cited source; reviewers read Python, not
  prompts.
- Demo mode, CI and air-gapped deployments work with no model at all; switching a model on changes wording,
  never numbers.
- The privacy rule is enforced in code (redaction in tool summaries, facts, questions and prompts) and checked
  after each run.
- The concepts map one-to-one onto the big frameworks (see the [learning guide](../../agents/README.md),
  section 11), so a later migration is a translation, not a rewrite.
- Small and readable enough to teach from.

Negative:

- No open-ended reasoning: a question the intent router does not recognise falls back to a quick estimate, and
  the coordinator says so. New capabilities need code, a plan entry and tests.
- Template text is plainer than LLM prose, and translations need either templates per language or the optional
  LLM.
- We maintain the framework ourselves (orchestration, tracing, the LLM client) instead of inheriting fixes from
  a large community.

## Alternatives considered

- **LangGraph.** The closest match (explicit graphs, shared state, checkpoints). Rejected for now: heavy
  dependency tree and API churn for a plan that is a straight line with skip rules; the mapping in the learning
  guide keeps the door open.
- **CrewAI / AutoGen.** Role-based teams and group chats where a model drives each turn. Rejected: model-driven
  control flow conflicts with "an LLM never computes a carbon number" and makes transcripts non-reproducible.
- **PydanticAI / OpenAI Agents SDK.** Clean tool and dependency injection, guardrails, hand-offs — but built
  around a model that chooses tools. The `deps` pattern for tools was adopted from PydanticAI.
- **No framework (one service function).** Simplest, but loses what the feature is for: named roles, a
  transcript, declared data flow and per-run guardrails.

## Revisit when

A use case needs open-ended, model-driven planning (for example free-form research questions over documents),
or durable long-running runs with human approval steps. Even then the rules of ADR-0003 stay: numbers come from
tools, and model output passes the same checks.
