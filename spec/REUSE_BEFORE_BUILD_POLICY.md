# Reuse-Before-Build Policy Specification
Status: Draft v0.1

## 1. Purpose
Make capability reuse the default planning path. The policy decides whether a task should reuse one existing capability, compose several, adapt a partial match, defer pending evidence/review, or identify a genuine capability gap.

## 2. Decision actions
- `reuse`: one eligible existing capability meets the task-fit threshold.
- `compose`: multiple eligible and explicitly composable capabilities cover the declared task contract.
- `adapt`: a relevant, otherwise eligible capability has partial interface/runtime compatibility and requires a declared adapter or modification.
- `build_gap`: no candidate is relevant and eligible, and no unresolved candidate could reasonably satisfy the task. This authorizes designing a new capability, not deploying it.
- `defer`: potentially relevant candidates remain blocked by license, security, lifecycle, verification, or compatibility review.
- `reject`: reserved for a candidate-level rejection; the task-level decision may still select another candidate or identify a gap.

## 3. Candidate assessment contract
Each candidate provides:
- stable `id`;
- `fit_score` in [0,1], grounded in task-specific matching/evaluation rather than popularity;
- `lifecycle`: discovered, draft, tested, validated, stable, deprecated;
- `verification_status`: unverified, tested, verified, validated;
- `license_status`: review_required, approved, compatible, incompatible;
- `security_status`: review_required, approved, passed, rejected, blocked;
- `compatibility`: unknown, compatible, partial, incompatible;
- optional `capabilities` and explicit `composable=true` for set-cover composition.

## 4. Gate order
1. Reject deprecated, license-incompatible, security-rejected, or runtime-incompatible candidates.
2. Defer candidates with unresolved license, security, lifecycle, verification, or compatibility status.
3. Apply the minimum task-fit threshold.
4. Prefer a single verified capability when it satisfies the task contract.
5. Compose only when declared required capabilities are all covered by eligible candidates that explicitly opt into composition.
6. Adapt only when a relevant candidate passed trust gates but needs explicit compatibility work.
7. Permit a build-gap decision only when no eligible candidate and no unresolved plausible candidate remain.

## 5. Safety invariants
- Discovery does not imply trust; trust does not imply execution authorization.
- This policy never executes source code, prompts, dependencies, tools, or agents.
- `execution_authorized` is always false in the policy result.
- Execution requires a separate adapter registry, least-privilege permissions, sandbox, budget, and approval gate.
- Unknown license or security status must not be silently treated as approved.
- Popularity, stars, downloads, or model-generated confidence alone are not evidence of quality.

## 6. Output
The deterministic decision contains policy version, task ID, action, selected IDs, per-candidate assessments, rejected/deferred/not-fit candidates, rationale, uncovered requirements, and explicit authorization flags.

## 7. Evaluation
Compare reuse-first against a generate-first baseline on the same tasks. Report task success, quality, latency, token/tool cost, integration effort, maintenance burden, security findings, and reuse rate. Reuse rate is not an optimization target by itself; quality and safety are constraints.
