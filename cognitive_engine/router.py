"""Cognitive Router v0.1: deterministic, logged, explainable.

Pipeline (spec/COGNITIVE_ROUTER_SPEC.md §4): normalize -> classify -> clarify? -> retrieve ->
filter -> rank (rules + evidence) -> select/abstain -> record.
"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from .registry import Registry
from .reuse_policy import decide_reuse

POLICY_VERSION = "rules-0.1"

# task class -> (keyword patterns, preferred families in composition order)
TASK_CLASSES = {
    "city_observation": ([r"公众号|城市|年轻人|周末|流行|打卡|City ?Walk|现象"],
                         ["反转揭底", "命名", "典型画像", "分类拆解", "金句断语", "不收的收尾"]),
    "commentary": ([r"时评|评论|社论|观点|政论|批评|杂文|短评"],
                   ["小处起笔", "预设驳论", "换层级", "数据压舱", "金句断语", "号召落点"]),
    "feature": ([r"特稿|人物|采访|深度报道|群像"],
                ["冷笔白描", "典型画像", "小处起笔", "不收的收尾"]),
    "official_doc": ([r"通知|请示|报告|函|纪要|公文"], ["分类拆解", "排比/三段"]),
    "narrative": ([r"小说|故事|叙事|散文|随笔|武侠"], ["冷笔白描", "比喻", "回环呼应", "不收的收尾"]),
    "argument_analysis": ([r"论证|漏洞|反驳|驳斥|辩论|为什么|原因|因果"],
                          ["预设驳论", "分类拆解", "换层级", "反转揭底"]),
    "research_summary": ([r"研究|摘要|综述|总结|分析"], ["分类拆解", "数据压舱", "换层级", "金句断语"]),
}
ENGINE_HINT = {"city_observation": "sanlian-writing", "commentary": "zhexuan-writing", "feature": "feature-writing",
               "official_doc": "gongwen-writing"}
HIGH_RISK = re.compile(r"医疗|法律意见|投资建议|诊断|处方")


def normalize(task: dict | str) -> dict:
    if isinstance(task, str):
        task = {"objective": task}
    t = {"id": task.get("id") or f"task-{uuid.uuid4().hex[:8]}", "objective": task["objective"].strip(),
         "inputs": task.get("inputs", {}), "constraints": task.get("constraints", {}),
         "risk_class": task.get("risk_class"), "success_criteria": task.get("success_criteria", []),
         "required_capabilities": task.get("required_capabilities", []),
         "budget": task.get("budget", {"max_steps": 6})}
    if not t["objective"]:
        raise ValueError("empty objective")
    return t


def classify(task: dict) -> dict:
    text = task["objective"] + " " + json.dumps(task["constraints"], ensure_ascii=False)
    scores = {c: sum(len(re.findall(p, text, re.I)) for p in pats) for c, (pats, _) in TASK_CLASSES.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    return {"task_class": best if scores[best] else "unknown",
            "confidence": round(scores[best] / total, 2) if total else 0.0, "scores": scores,
            "risk": task["risk_class"] or ("high" if HIGH_RISK.search(text) else "low"),
            "has_material": bool(task["inputs"].get("material"))}


class EvidenceStore:
    """Per (task_class, strategy) win stats from evaluation runs. JSON file."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.stats: dict = json.loads(self.path.read_text(encoding="utf-8")) if self.path and self.path.exists() else {}

    def lift(self, task_class: str, strategy: str) -> tuple[float, int]:
        s = self.stats.get(task_class, {}).get(strategy)
        if not s:
            return 0.0, 0
        return (s["wins"] + 1) / (s["n"] + 2) - 0.5, s["n"]

    def record(self, task_class: str, strategy: str, win: bool) -> None:
        s = self.stats.setdefault(task_class, {}).setdefault(strategy, {"wins": 0, "n": 0})
        s["n"] += 1
        s["wins"] += int(win)
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.stats, ensure_ascii=False, indent=1), encoding="utf-8")


def route(task: dict | str, registry: Registry, evidence: EvidenceStore | None = None,
          *, mode: str = "composition", log_path: str | Path | None = None) -> dict:
    """mode: composition | single. Returns a RoutingDecision."""
    evidence = evidence or EvidenceStore()
    t = normalize(task)
    feats = classify(t)
    decision = {"schema_version": "0.1", "id": f"rd-{uuid.uuid4().hex[:8]}", "task_id": t["id"],
                "policy_version": POLICY_VERSION, "features": feats, "timestamp": time.time(),
                "selected": None, "plan": [], "rejected": [], "rationale": [], "fallback": "strong"}

    if feats["task_class"] == "unknown" or feats["confidence"] < 0.34:
        decision.update(status="abstain", rationale=["task class unclear; ask for genre/purpose or use fallback"])
        return _log(decision, log_path)
    if feats["risk"] == "high":
        decision.update(status="escalate", rationale=["high-risk task: unvalidated strategies need human approval"])
        return _log(decision, log_path)

    _, families = TASK_CLASSES[feats["task_class"]]
    hint = ENGINE_HINT.get(feats["task_class"])
    budget = t["budget"].get("max_steps", 6)
    plan, used = [], set()
    for fam in families:
        cands = [p for p in registry.search(family=fam) if p["lifecycle"] != "deprecated"]
        if not cands:
            decision["rejected"].append({"family": fam, "reason": "no eligible primitive"})
            continue

        def score(p):
            lift, _n = evidence.lift(feats["task_class"], p["id"])
            return (lift, hint in p.get("tags", []), p.get("completeness", 0), -len(p["procedure"]), p["id"])
        cands.sort(key=score, reverse=True)
        pick = cands[0]
        if pick["id"] in used:
            continue
        used.add(pick["id"])
        plan.append({"step": len(plan) + 1, "primitive": pick["id"], "family": fam, "name": pick["name"]})
        decision["rejected"] += [{"primitive": c["id"], "reason": f"lower rank in family {fam}"} for c in cands[1:3]]
        if len(plan) >= budget:
            break

    if not plan:
        decision.update(status="abstain", rationale=["no primitives matched"])
        return _log(decision, log_path)
    if mode == "single":
        plan = plan[:1]
    elif mode == "composition":
        # verification tail: what single-pass generation is weakest at (grounding, constraint checks)
        tail = ["ce.general.redline_audit"]
        if feats["has_material"]:
            tail.insert(0, "ce.general.evidence_grounding")
        for pid in tail:
            if pid in registry.primitives and pid not in used:
                p = registry.get(pid)
                plan.append({"step": len(plan) + 1, "primitive": pid, "family": p["family"], "name": p["name"],
                             "role": "verify"})
    decision.update(status="selected", selected=f"{mode}:{feats['task_class']}", plan=plan,
                    engine_hint=hint,
                    rationale=[f"class={feats['task_class']} (conf {feats['confidence']})",
                               f"families={families}", "rank=(evidence lift, engine affinity, completeness, brevity)"])
    return _log(decision, log_path)


def _log(decision: dict, log_path):
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")
    return decision


def route_with_reuse(
    task: dict | str,
    registry: Registry,
    capability_candidates: list[dict],
    evidence: EvidenceStore | None = None,
    *,
    mode: str = "composition",
    log_path: str | Path | None = None,
) -> dict:
    """Apply reuse-first before falling back to internal cognitive primitives.

    A selected external capability is only a planning reference. This function
    never invokes an adapter or authorizes execution. A build_gap result means
    no eligible external capability was found; the existing internal router may
    still plan cognitive primitives for the task, not generate repository code.
    """
    normalized = normalize(task)
    reuse = decide_reuse(normalized, capability_candidates)

    if reuse["action"] in {"reuse", "compose", "adapt"}:
        plan = [
            {"step": index, "primitive": capability_id, "family": "external_capability",
             "source": "external_catalog", "reuse_action": reuse["action"]}
            for index, capability_id in enumerate(reuse["selected"], start=1)
        ]
        result = {
            "schema_version": "0.1",
            "id": f"rd-{uuid.uuid4().hex[:8]}",
            "task_id": normalized["id"],
            "policy_version": POLICY_VERSION,
            "status": "selected",
            "strategy_source": "external_capability",
            "features": classify(normalized),
            "rejected": reuse["rejected"],
            "reuse_decision": reuse,
            "plan": plan,
            "rationale": ["reuse-first policy selected existing capability assets"],
            "fallback": "human_review",
            "execution_authorized": False,
        }
    elif reuse["action"] == "defer":
        result = {
            "schema_version": "0.1",
            "id": f"rd-{uuid.uuid4().hex[:8]}",
            "task_id": normalized["id"],
            "policy_version": POLICY_VERSION,
            "status": "abstain",
            "strategy_source": "human_review",
            "features": classify(normalized),
            "rejected": reuse["rejected"],
            "reuse_decision": reuse,
            "plan": [],
            "rationale": ["potentially relevant capabilities require unresolved review"],
            "fallback": "human_review",
            "execution_authorized": False,
        }
    else:
        internal = route(normalized, registry, evidence, mode=mode, log_path=log_path)
        internal["strategy_source"] = "internal_cognitive_primitives"
        internal["reuse_decision"] = reuse
        internal["execution_authorized"] = False
        internal["rationale"] = ["no eligible external capability; using the internal cognitive strategy library"] + internal.get("rationale", [])
        return internal

    return _log(result, log_path)
