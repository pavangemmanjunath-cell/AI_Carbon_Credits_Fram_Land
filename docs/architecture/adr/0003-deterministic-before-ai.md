# ADR-0003: Deterministic calculations before AI; language models explain, never compute

- **Status:** accepted
- **Date:** 2026-10-04
- **Deciders:** project lead

## Context

It is tempting to let a large language model fill the gaps in a carbon
tool: estimate growth for a species without a table entry, judge whether
a farm "qualifies" for a programme, or produce a single tidy number from
messy inputs. The project's purpose argues against this. Farmers,
reviewers and researchers must be able to trace every figure to an
equation, a parameter with a source, and an input they supplied. A
language model cannot provide that trace, can produce different numbers
for the same inputs, can fabricate citations, and would require sending
plot data to a third-party service.

At the same time, plain-language explanation has value: a paragraph that
says what a range means, why confidence is medium and which evidence is
missing helps a user more than a table alone.

## Decision

1. **All numbers are deterministic.** Carbon estimates, land-cover shares,
   vegetation indices, policy screening statuses, market scenarios and
   readiness scores are computed by code that applies published equations
   to configuration with provenance. No language model participates in
   any calculation, classification or eligibility decision.
2. **Explanation is a separate, optional, privacy-bounded step.**
   `POST /explain` produces text from *derived indicators only* (area,
   counts, index values, the estimate range, confidence, missing-evidence
   ids). The default provider is a deterministic template; an LLM provider
   is opt-in via `ATLAS_EXPLAIN_PROVIDER=llm`, receives the same payload
   and nothing else, and its output is labelled as an explanation, never
   as a result.
3. **The explain schema rejects location.** Any key named `lat`, `lon`,
   `latitude`, `longitude`, `geometry`, `coordinates` or `polygon` is a
   validation error, so a client cannot accidentally forward geometry.
4. **Missing knowledge is a typed gap, not a guess.** When a species,
   equation or rule is absent, the engine returns a typed error or a
   `TODO` naming the authoritative source required (CLAUDE.md principle
   13), and the UI says so.

## Consequences

Positive:

- Reproducibility: the same inputs and configuration always yield the same
  result, which makes validation
  ([../../../research/validation/README.md](../../../research/validation/README.md))
  and regression tests meaningful.
- Auditability: `parameters_used` and `provenance` fully determine the
  output.
- Privacy: no third-party AI service ever receives coordinates
  ([../../privacy/privacy-design.md](../../privacy/privacy-design.md)).
- Honesty: an estimate's confidence reflects data and parameter quality,
  not a model's fluency.

Negative:

- Coverage grows only as fast as reviewed configuration does; a species
  without a table entry is unsupported until someone adds and verifies it.
- Explanations from the template provider are plainer than LLM prose.
  That is acceptable.

## Alternatives considered

- **LLM-assisted parameter lookup** ("find the IPCC increment for teak").
  Rejected: the lookup is exactly where fabrication is most harmful. A
  human-reviewed configuration change with a citation is the only path.
- **LLM-generated eligibility assessments.** Rejected: programme rules
  change, differ by jurisdiction and have legal consequences; they are
  encoded as reviewed configuration with references
  ([0004-config-driven-regions-and-policies.md](0004-config-driven-regions-and-policies.md)).
- **LLM as a chat interface over results.** Possible later, under the same
  constraints as `/explain` (derived indicators only, clearly labelled).

## Revisit when

Never for the computation rule. The explanation provider list may be
extended, and a local, self-hosted model may become the default explainer
if it meets the same payload constraint.
