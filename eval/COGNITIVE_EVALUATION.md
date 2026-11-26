# Cognitive Evaluation Framework

## 1. Objective
Determine whether primitives, compositions, and routing policies improve outcomes over credible baselines and generalize without unacceptable cost or safety regressions.

## 2. Evaluation dimensions
Task success and correctness; evidence accuracy, coverage, and provenance; reasoning validity and constraint adherence; uncertainty calibration and abstention; robustness to paraphrase, noise, and adversarial inputs; transfer to held-out tasks and domains; latency, token use, tool calls, and cost per success; safety, privacy, and policy compliance.

## 3. Experimental design
Compare: (1) base model with neutral task prompt; (2) base model with strong general-purpose prompt; (3) primitive or composition enabled; (4) router-selected strategy where relevant. Control model version, decoding, tools, context, and task inputs. Use paired tasks and repeated trials where stochasticity matters. Separate development, validation, and held-out test sets; prevent benchmark leakage.

## 4. Scoring
Define task-specific rubrics before experiments. Prefer objective checks. Use blinded independent evaluators for subjective dimensions and report inter-rater agreement. Model-based judges may assist but must not be sole authority for high-stakes claims.

## 5. Core metrics
- task_success_rate: proportion meeting predeclared criteria.
- strategy_lift: performance difference against strongest relevant baseline.
- transfer_gain: held-out task/domain performance relative to baseline.
- self_correction_rate: detected errors successfully corrected.
- regression_rate: tasks materially harmed by a change.
- cost_per_success: total inference/tool cost divided by successful tasks.
- calibration_error: discrepancy between stated confidence and observed correctness.

## 6. Reporting
Publish sample size, task selection, model/version, prompts, tools, scoring rubric, raw or appropriately anonymized outputs, judge protocol, uncertainty intervals, failures, and deviations. Do not report a single aggregate without breakdowns.

## 7. Promotion gates
A candidate must beat the strongest baseline by a predeclared meaningful margin; remain within regression and safety thresholds; demonstrate repeatability on held-out data; have acceptable cost and latency; and include rollback.

## 8. First benchmark
Start with a small reproducible benchmark in the companion writing-engines domain. Preserve a neutral baseline and compare selected engines under blinded evaluation. Existing plans remain plans until the experiment is run and results recorded.
