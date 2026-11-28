"""Reuse-before-build policy for capability selection.

This module makes discovery-first a deterministic planning decision. It does not
install, execute, or authorize any candidate. Execution authorization remains a
separate runtime and human-approval concern.
"""
from __future__ import annotations

from typing import Any

POLICY_VERSION = "reuse-first-0.1"
ELIGIBLE_LIFECYCLES = {"tested", "validated", "stable"}
ELIGIBLE_VERIFICATION = {"tested", "verified", "validated"}
APPROVED_LICENSE = {"approved", "compatible"}
APPROVED_SECURITY = {"approved", "passed"}
VALID_ACTIONS = {"reuse", "compose", "adapt", "build_gap", "defer", "reject"}


def _candidate_id(candidate: dict[str, Any]) -> str:
    value = candidate.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("every candidate must have a non-empty id")
    return value


def _assess(candidate: dict[str, Any], min_fit: float) -> dict[str, Any]:
    cid = _candidate_id(candidate)
    fit = candidate.get("fit_score", 0.0)
    if isinstance(fit, bool) or not isinstance(fit, (int, float)) or not 0 <= fit <= 1:
        raise ValueError(f"{cid}: fit_score must be a number between 0 and 1")

    lifecycle = candidate.get("lifecycle", "discovered")
    verification = candidate.get("verification_status", "unverified")
    license_status = candidate.get("license_status", "review_required")
    security_status = candidate.get("security_status", "review_required")
    compatibility = candidate.get("compatibility", "unknown")
    reasons: list[str] = []
    blockers: list[str] = []

    if lifecycle == "deprecated":
        return {"id": cid, "status": "rejected", "fit_score": fit, "reasons": ["deprecated capability"]}
    if license_status == "incompatible":
        return {"id": cid, "status": "rejected", "fit_score": fit, "reasons": ["license incompatible"]}
    if security_status in {"rejected", "blocked"}:
        return {"id": cid, "status": "rejected", "fit_score": fit, "reasons": ["security review rejected"]}
    if compatibility == "incompatible":
        return {"id": cid, "status": "rejected", "fit_score": fit, "reasons": ["interface or runtime incompatible"]}

    if license_status not in APPROVED_LICENSE:
        blockers.append("license review required")
    if security_status not in APPROVED_SECURITY:
        blockers.append("security review required")
    if lifecycle not in ELIGIBLE_LIFECYCLES:
        blockers.append("lifecycle is not tested or better")
    if verification not in ELIGIBLE_VERIFICATION:
        blockers.append("verification evidence is insufficient")
    if compatibility == "unknown":
        blockers.append("compatibility has not been established")
    if blockers:
        return {"id": cid, "status": "deferred", "fit_score": fit, "reasons": blockers}

    if fit < min_fit:
        return {"id": cid, "status": "not_fit", "fit_score": fit,
                "reasons": [f"fit score {fit:.3f} is below threshold {min_fit:.3f}"]}
    if compatibility == "partial":
        return {"id": cid, "status": "adapt", "fit_score": fit,
                "reasons": ["capability is relevant but requires an explicit adapter or modification"]}
    if compatibility != "compatible":
        return {"id": cid, "status": "rejected", "fit_score": fit, "reasons": ["unsupported compatibility state"]}
    return {"id": cid, "status": "eligible", "fit_score": fit,
            "reasons": ["task fit, lifecycle, verification, license, security and compatibility gates passed"]}


def decide_reuse(
    task: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    min_fit: float = 0.70,
) -> dict[str, Any]:
    """Return a transparent reuse/compose/adapt/build/defer decision.

    Candidate fields are intentionally explicit:
      id, fit_score, lifecycle, verification_status, license_status,
      security_status, compatibility, capabilities, composable.

    No candidate is ever made executable by this decision. The caller must
    perform separate adapter, permission, sandbox and approval checks.
    """
    if not isinstance(task, dict) or not isinstance(task.get("objective"), str) or not task["objective"].strip():
        raise ValueError("task.objective must be a non-empty string")
    if isinstance(min_fit, bool) or not isinstance(min_fit, (int, float)) or not 0 <= min_fit <= 1:
        raise ValueError("min_fit must be a number between 0 and 1")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")

    assessments = [_assess(candidate, float(min_fit)) for candidate in candidates]
    by_id = {_candidate_id(candidate): candidate for candidate in candidates}
    if len(by_id) != len(candidates):
        raise ValueError("candidate ids must be unique")

    eligible = [a for a in assessments if a["status"] == "eligible"]
    adaptable = [a for a in assessments if a["status"] == "adapt"]
    deferred = [a for a in assessments if a["status"] == "deferred"]
    rejected = [a for a in assessments if a["status"] == "rejected"]
    not_fit = [a for a in assessments if a["status"] == "not_fit"]

    eligible.sort(key=lambda item: (-item["fit_score"], item["id"]))
    adaptable.sort(key=lambda item: (-item["fit_score"], item["id"]))
    required = set(task.get("required_capabilities", []))
    selected: list[str] = []
    action = "build_gap"
    rationale: list[str] = []

    if required and eligible:
        remaining = set(required)
        pool = list(eligible)
        while remaining:
            choices = []
            for assessment in pool:
                candidate = by_id[assessment["id"]]
                coverage = remaining.intersection(candidate.get("capabilities", []))
                if coverage and candidate.get("composable") is True:
                    choices.append((len(coverage), assessment["fit_score"], assessment["id"], coverage))
            if not choices:
                break
            choices.sort(key=lambda item: (-item[0], -item[1], item[2]))
            _, _, chosen_id, coverage = choices[0]
            selected.append(chosen_id)
            remaining -= coverage
            pool = [item for item in pool if item["id"] != chosen_id]
        if not remaining:
            action = "compose" if len(selected) > 1 else "reuse"
            rationale.append("selected capabilities cover all required task capabilities")
        else:
            selected = []
            rationale.append("eligible capabilities do not cover the full task contract; do not silently select a partial substitute")

    if not selected and adaptable and not required:
        selected = [adaptable[0]["id"]]
        action = "adapt"
        rationale.append("best relevant capability requires an explicit adaptation step")
    elif not selected and eligible and not required and action != "compose":
        selected = [eligible[0]["id"]]
        action = "reuse"
        rationale.append("best eligible existing capability meets the fit threshold")
    elif not selected and deferred:
        action = "defer"
        rationale.append("potentially relevant candidates remain blocked by unresolved trust or compatibility checks")
    elif not selected and not deferred:
        action = "build_gap"
        rationale.append("no existing candidate passed the relevance and eligibility gates; a new capability may be designed")

    if action == "build_gap" and not rationale:
        rationale.append("no candidate was supplied; discovery results are insufficient to justify reuse")

    return {
        "schema_version": "0.1",
        "policy_version": POLICY_VERSION,
        "task_id": task.get("id"),
        "action": action,
        "selected": selected,
        "candidate_assessments": assessments,
        "rejected": [item["id"] for item in rejected],
        "deferred": [item["id"] for item in deferred],
        "not_fit": [item["id"] for item in not_fit],
        "rationale": rationale,
        "build_authorized": action == "build_gap",
        "execution_authorized": False,
        "required_capabilities_uncovered": sorted(required) if action == "build_gap" else [],
        "guardrails": [
            "discovery is not trust",
            "trust is not execution authorization",
            "no repository code, prompt, tool or dependency is executed by this policy",
            "execution requires separate adapter, permission, sandbox and approval checks",
        ],
    }
