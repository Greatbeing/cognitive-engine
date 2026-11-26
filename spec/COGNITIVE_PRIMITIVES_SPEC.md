# Cognitive Primitives Specification
Status: Draft v0.1

## 1. Definition
A cognitive primitive is a reusable, independently identifiable operation that transforms a defined input into a defined output to advance a task. It specifies what cognitive work is performed, when it is appropriate, and how its result can be evaluated. It is not merely a prompt, style instruction, chain-of-thought transcript, or domain-specific template.

## 2. Required schema
Each primitive MUST define: id (stable unique identifier); name; version (semantic version); purpose; trigger_conditions; preconditions; inputs (typed); procedure (bounded steps); outputs (typed); postconditions; evaluation (observable criteria and test method); failure_modes and mitigations; resource_profile (model/tool/time budget); safety_constraints (permissions, prohibited operations, escalation); provenance (author, source, evidence, change history).

## 3. Optional metadata
 tags, domain, language, composability, dependencies, alternatives, examples, limitations, and retirement_status.

## 4. Lifecycle
Proposed -> Draft -> Tested -> Validated -> Stable -> Deprecated. Promotion requires tests and documented evidence. Deprecation requires a replacement or rationale and migration note.

## 5. Quality requirements
A primitive should be atomic enough to evaluate, useful across more than one prompt formulation, composable through explicit inputs and outputs, and distinguishable from a generic instruction. Avoid meaningless micro-steps.

## 6. Evaluation
Evaluate primitives individually where possible and within compositions. Use held-out examples, multiple prompt formulations, appropriate baselines, and independent or blinded judging where feasible. Record uncertainty and inter-rater agreement.

## 7. Illustrative example: counterexample_search
Purpose: challenge a candidate claim by finding plausible counterexamples. Trigger: broad, causal, universal, or consequential claim. Inputs: claim, domain, evidence set, search budget. Procedure: identify scope and quantifiers; derive necessary conditions; search boundary cases; assess validity; revise claim scope. Outputs: counterexamples, validity assessment, revised claim, unresolved uncertainties. Failure modes: straw-man examples, cherry-picking, confusing absence of evidence with disproof. Evaluation: valid counterexamples found on a curated challenge set and false-positive rate.

## 8. Interoperability
Definitions SHOULD be machine-readable (initially YAML or JSON) and MUST declare schema version. Implementations SHOULD reject unknown required fields and preserve unknown optional metadata.
