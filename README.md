# Cognitive Engine

An open, extensible architecture for engineering, composing, evaluating, and evolving reusable cognitive capabilities.

## Vision
Explore whether useful cognitive operations can be represented as reusable primitives, composed into strategies, selected by a planner, executed by a runtime, measured against rigorous evaluations, and improved through controlled feedback.

This repository defines the architecture and specifications. The companion project [writing-engines](https://github.com/Greatbeing/writing-engines) is an applied laboratory for writing capabilities. Keep both repositories independently maintainable and connect them through stable interfaces.

## Six-layer architecture
1. Cognitive Primitives — typed, testable units of cognitive work.
2. Cognitive Composition — sequential, parallel, conditional, and recursive composition.
3. Cognitive Planning and Routing — task decomposition and strategy selection.
4. Cognitive Runtime — execution, state, tools, memory, provenance, and safety.
5. Cognitive Evaluation — task success, quality, transfer, cost, and regression measurement.
6. Cognitive Evolution — evidence-gated updates to primitives, compositions, and routing policies.

## Principles
Model-agnostic; inspectable; composable; measurable; conservative learning; reversible changes; least-privilege and human oversight for consequential actions.

## Feedback-loop hypothesis
Let S_t be a versioned library of cognitive primitives and strategies, T_t the task, E_t external evidence, X_t execution, and V_t evaluation. Explore X_t = F(S_t,T_t,E_t), V_t = G(X_t,E_t,T_t), and S_(t+1) = U(S_t,X_t,V_t). This is a testable engineering abstraction, not a claim that a philosophical account of consciousness is equivalent to a computational architecture.

## Repository map
- docs/: architecture and evolution
- spec/: normative interface specifications
- eval/: evaluation methodology
- ROADMAP.md: staged delivery plan

## Milestones
- v0.1: primitive schema, architecture boundaries, reproducible baselines.
- v0.2: minimal router and composition executor.
- v1.0: model-agnostic runtime with traces and evaluation hooks.
- v2.0: evidence-gated learning and controlled strategy evolution.

## Status
Early research and engineering specifications. No claim of a validated general-purpose cognitive engine is made. Priorities are schema consistency, reproducible evaluation, and a minimal end-to-end prototype.
