# Cognitive Engine Architecture

## 1. Purpose
Define a modular architecture for turning cognitive capabilities into reusable, composable, executable, measurable, and improvable software assets. Each capability must earn promotion through evaluation.

## 2. System model
The system accepts a task, context, constraints, and success criteria. It produces an answer or action with an execution trace, evidence references, resource use, and evaluation record.

## 3. Six layers
### 3.1 Cognitive Primitives
A primitive is the smallest independently specified cognitive operation with a clear purpose, contract, and evaluation method. Examples: hypothesis generation, decomposition, causal analysis, counterexample search, source triangulation, and uncertainty calibration. A primitive is an operation, not a reusable sentence template.

### 3.2 Cognitive Composition
Composition defines how primitives work together. Initial patterns: sequential pipeline; parallel branches with synthesis; conditional branch; bounded iteration; hierarchical decomposition and recursion with explicit depth and termination limits. Every composition declares inputs, outputs, dependencies, ordering constraints, failure behavior, and resource budget.

### 3.3 Cognitive Planning and Routing
The planner converts a task into a structured representation, identifies constraints and success criteria, selects primitives or compositions, and produces an execution plan. The router chooses among eligible strategies using task features, historical evidence, cost, latency, and risk. Routing decisions must be logged and explainable.

### 3.4 Cognitive Runtime
The runtime manages model adapters; tool invocation and permission checks; working state and bounded memory; evidence and provenance; retries, timeouts, and budgets; cancellation and human approval; structured traces and error handling. Models generate and interpret; tools retrieve or act; primitives specify cognitive operations; runtime coordinates execution.

### 3.5 Cognitive Evaluation
Measure task success, correctness, evidence quality, reasoning validity, calibration, robustness, transfer, latency, token and tool cost, and safety. Compare against controlled baselines.

### 3.6 Cognitive Evolution
Propose changes to primitives, compositions, routing policies, or architecture. Version each candidate, test on held-out tasks, check regressions and safety, promote only after explicit gates, and preserve rollback.

## 4. Contracts and data flow
Minimal contracts: TaskSpec (objective, inputs, context references, constraints, risk class, success criteria, budget); Plan (strategy, steps, dependencies, stop conditions, estimated cost); ExecutionTrace (events, selected components, tool calls, evidence, timings, errors, approvals); Result (output, evidence map, uncertainty, trace reference); Evaluation (metrics, judge protocol, baseline comparison, confidence, decision). All artifacts carry stable IDs, schema versions, timestamps, and provenance.

## 5. Cross-cutting concerns
Security and privacy; least-privilege tool access; prompt-injection resistance; secret handling; data retention; auditability; reproducibility; accessibility; and human oversight for consequential operations.

## 6. Design constraints
No permanent-best-model assumption; no execution of untrusted retrieved instructions; no unbounded recursion or self-modification; no promotion based solely on model self-score; no silent mutation of production strategies; explicit resource and risk budgets.

## 7. First prototype
Build a narrow vertical slice: task specification -> primitive selection -> sequential composition -> runtime execution -> trace capture -> benchmark evaluation. Start with writing/research as an applied domain while keeping interfaces domain-neutral.
