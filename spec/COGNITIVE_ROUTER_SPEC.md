# Cognitive Router Specification
Status: Draft v0.1

## 1. Purpose
Select an appropriate primitive or composition for a task under quality, risk, latency, and cost constraints. The router is a policy component, not an opaque claim of intelligence.

## 2. Inputs
Normalized task description and class; context availability and quality; success criteria and constraints; risk and permission class; candidate strategies and declared capabilities; historical evaluation statistics; resource budgets.

## 3. Output
RoutingDecision: selected strategy; rejected alternatives; rationale and features; expected quality and cost ranges; risk assessment; fallback; policy version.

## 4. Initial routing pipeline
1. Validate and normalize TaskSpec.
2. Classify task type, complexity, ambiguity, and risk.
3. Identify missing information and decide whether clarification is required.
4. Retrieve eligible primitives and compositions by capability and preconditions.
5. Filter strategies that violate constraints or budget.
6. Rank candidates using evaluation evidence, task similarity, uncertainty, latency, and cost.
7. Select a strategy or abstain/escalate if evidence is insufficient.
8. Record decision and expected outcomes.
9. Monitor execution and invoke fallback only under declared conditions.

## 5. Policy evolution
Begin with deterministic rules and evidence-weighted ranking. With sufficient logged outcomes, test contextual bandits offline or in guarded experiments. Reinforcement learning is a later option only when reward definitions, exploration safety, attribution, and rollback are credible.

## 6. Guardrails
Never select an unvalidated strategy for high-impact tasks without explicit human approval. Respect tool permissions and data boundaries. Do not infer capability from a name or description alone. Track uncertainty and out-of-distribution tasks. Support abstention and clarification. Maintain a deterministic fallback.

## 7. Metrics
Task success by class; strategy lift over baseline; calibration; abstention quality; cost per successful task; latency; fallback rate; regression rate.

## 8. Minimal API sketch
Input: TaskSpec, StrategyRegistry, EvaluationStore, Budget. Output: RoutingDecision. Formalize API and serialized schema after the first prototype.
