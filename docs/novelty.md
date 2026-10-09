# What is different

Most tree-carbon calculators return one number. This project contributes a combination, each part testable:

1. **Evidence readiness.** The result sits beside a readiness score and a list of the evidence still missing for a
   recognised programme, rather than a price.
2. **Parameter provenance gate.** Every parameter has a source, unit and verification status; `pending` values are
   flagged to users and refused in production.
3. **Tree-age model.** Carbon held by existing trees is kept apart from the rules that decide whether any credit is
   possible, since old trees can hold much carbon and still earn none.
4. **Agents that cannot calculate.** Nine deterministic agents explain engine results; six guardrails must pass; an
   optional LLM may only rephrase redacted text.
5. **Privacy boundary.** Exact polygons are private; no coordinates in logs or model calls.

Claims are limited to the implementation; field validation is planned. See [benchmarks/](../benchmarks/README.md).
