# Cognitive Evolution: Evidence-Gated Improvement

## 1. Objective
Improve reusable cognitive assets without uncontrolled self-modification or unverified claims of learning.

## 2. Evolution targets
Primitive content and parameters; compositions and dependency graphs; routing and planning policies; runtime and architecture components.

## 3. Feedback loop
For each task, capture task features, selected strategy, execution trace, evidence, outcome, evaluator protocol, resource use, and uncertainty. Generate candidate updates from recurring failure patterns or validated successes.

Conceptual loop: X_t = F(S_t, T_t, E_t); V_t = G(X_t, E_t, T_t); S_(t+1) = U(S_t, X_t, V_t). S is the versioned strategy/primitive library, T the task, E external evidence, X execution, and V evaluation. This is a testable engineering abstraction, not an equivalence claim between a philosophical doctrine and machine cognition.

## 4. Controlled update pipeline
1. Detect recurring error or opportunity.
2. Form a specific change hypothesis.
3. Generate a versioned candidate.
4. Run unit, integration, benchmark, safety, and regression tests.
5. Evaluate on held-out tasks.
6. Compare with stable version and baseline.
7. Require human approval for early-release promotion.
8. Canary deploy, monitor, and roll back if thresholds are breached.
9. Preserve provenance and decision records.

## 5. Learning methods by maturity
Early: curated rules, error taxonomies, supervised examples, evidence-weighted selection. Intermediate: offline contextual bandits and controlled online experiments. Advanced: reinforcement learning or model post-training only when reward validity, data quality, attribution, and safety controls are established.

## 6. Anti-patterns
Treating model self-critique as ground truth; training on unverified synthetic feedback; optimizing proxy metrics while harming task success; unbounded recursive self-editing; silently replacing stable strategies; discarding negative results.

## 7. Required records
Every update stores parent version, diff, hypothesis, supporting evidence, benchmark results, safety review, approver, deployment status, and rollback reference.

## 8. Success criteria
Improvement must be durable over time, repeatable across trials, transferable beyond training examples, and worth its resource cost.
