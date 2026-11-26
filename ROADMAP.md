# Roadmap

This roadmap is hypothesis-driven. Dates are planning windows, not commitments; milestones depend on evaluation evidence and engineering capacity.

## Phase 0 — Foundation (0–90 days)
- [ ] Define and validate the primitive schema.
- [ ] Build a machine-readable registry and asset index.
- [ ] Reconcile the companion writing-engines inventory and naming.
- [ ] Define a benchmark protocol and run the first controlled evaluation.
- [ ] Implement minimal task specification and execution trace formats.

Exit criteria: schema validated by examples; registry passes lint; benchmark is reproducible and reports baseline comparisons.

## Phase 1 — Minimal Cognitive Engine (3–9 months)
- [ ] Implement a small primitive library.
- [ ] Add sequential and parallel composition.
- [ ] Build a deterministic rule-based router.
- [ ] Add runtime adapters for at least one model and one tool.
- [ ] Capture provenance, budgets, and structured traces.

Exit criteria: end-to-end execution is reproducible, inspectable, and measurably better than baseline on a defined task set.

## Phase 2 — Adaptive Planning (9–18 months)
- [ ] Add conditional plans, bounded iteration, and fallback handling.
- [ ] Rank strategies using empirical evaluation data.
- [ ] Add uncertainty-aware abstention and clarification.
- [ ] Run held-out transfer evaluations.

Exit criteria: routing improves task success or cost-quality trade-offs without unacceptable regressions.

## Phase 3 — Evidence-Gated Evolution (18–36 months)
- [ ] Generate candidate primitive and composition revisions from error analysis.
- [ ] Automate test, benchmark, and regression pipelines.
- [ ] Introduce guarded offline contextual-bandit experiments.
- [ ] Add versioned promotion, canary, and rollback workflows.

Exit criteria: promoted changes demonstrate repeatable held-out gains and preserve auditability.

## Phase 4 — Cross-Domain Generalization (3–5 years)
- [ ] Validate architecture across writing, research, analysis, and planning.
- [ ] Develop domain adapters without fragmenting the core schema.
- [ ] Publish reproducible benchmarks and limitations.

Exit criteria: measurable transfer across multiple domains and independent replications where feasible.

## Near-term priorities
The first bottleneck is not a sophisticated self-learning algorithm. It is a consistent representation of cognitive primitives and credible evidence that composition improves performance. Prioritize schema, registry, benchmark, and a minimal end-to-end prototype before expanding scope.
