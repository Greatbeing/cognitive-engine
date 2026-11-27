"""Evaluation Engine: run conditions x tasks x trials, score with objective assertions,
compute paired strategy_lift with Wilson / bootstrap intervals, export blind packs."""
from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

from .registry import Registry
from .router import route, EvidenceStore
from .runtime import execute

CONDITIONS = ["baseline", "strong", "strong_long", "single", "composition"]
# `strong_long` is the length/coverage-matched baseline: it neutralises the confound that a
# multi-step prompt simply produces longer, more thorough output. Primary reference.
REFERENCES = ("strong_long", "strong")
DEV_IDS = {"t01", "t02", "t03"}  # tune prompts/primitives only on these; report on the held-out rest
CLICHE = r"在这个[^。]{0,10}时代|总而言之|不难发现|毋庸置疑|赋能|抓手|综上所述|值得一提的是"


# ------------------------------------------------------------ tasks
def load_we_tasks(we_root: str | Path) -> list[dict]:
    """writing-engines eval/prompts.json -> TaskSpecs with default objective assertions."""
    d = json.loads((Path(we_root) / "eval" / "prompts.json").read_text(encoding="utf-8"))
    tasks = []
    for t in d["topics"]:
        m = re.search(r"(\d+)", t.get("constraints", {}).get("length", ""))
        n = int(m.group(1)) if m else 800
        names = [x["name"] for x in t.get("material", []) if x.get("name")]
        tasks.append({"id": t["id"], "objective": t["prompt"], "constraints": t.get("constraints", {}),
                      "inputs": {"material": t.get("material", [])}, "domain": "writing",
                      "category": t.get("category"), "hypothesis": t.get("hypothesis"),
                      "split": "dev" if t["id"] in DEV_IDS else "test",
                      "assertions": [
                          {"type": "min_chars", "value": int(n * 0.8)},
                          {"type": "max_chars", "value": int(n * 1.6)},
                          {"type": "no_regex", "value": CLICHE},
                          {"type": "uses_all", "value": names, "note": "material coverage"},
                          {"type": "no_leak", "value": r"原子(技法|操作|\s*\d)|步骤\s*\d|认知操作|【[^】]{1,12}】"},
                      ]})
    return tasks


def load_task_file(path) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d["tasks"] if isinstance(d, dict) else d


# ------------------------------------------------------------ objective scoring
def usage_tokens(usage: dict) -> int:
    """Prefer the provider's total; never add prompt+completion on top of it (double counting)."""
    if isinstance(usage.get("total_tokens"), int):
        return usage["total_tokens"]
    return sum(v for k, v in usage.items() if isinstance(v, int))


def _chars(text):
    return len(re.sub(r"\s|[#*>`\-]", "", text))


def check(assertion: dict, text: str) -> bool | None:
    t, v = assertion["type"], assertion.get("value")
    if t == "min_chars": return _chars(text) >= v
    if t == "max_chars": return _chars(text) <= v
    if t in ("no_regex", "no_leak"): return not re.search(v, text)
    if t in ("any_regex", "must_regex"): return bool(re.search(v, text))
    if t == "uses_all": return all(x in text for x in v)
    if t == "numbers_from_material":
        allowed = set(re.findall(r"\d+(?:\.\d+)?", v or ""))
        return not (set(re.findall(r"\d+(?:\.\d+)?", text)) - allowed)
    if t == "max_named_people":
        cands = set(re.findall(r"(?:名叫|一位叫|有个叫|叫做)([\u4e00-\u9fa5]{2,3})", text))
        cands |= set(re.findall(r"([\u4e00-\u9fa5]{2,3})(?:告诉我|笑着说|回忆说)", text))
        allowed = assertion.get("allowed", [])
        return not {c for c in cands if not any(c in a or a in c for a in allowed)}
    if t == "count_min" and assertion.get("target") == "quotes": return len(re.findall(r"[“「]", text)) >= v
    return None  # manual / unsupported -> excluded from score


def score_output(task: dict, text: str) -> dict:
    res = [(a, check(a, text)) for a in task.get("assertions", [])]
    auto = [r for _, r in res if r is not None]
    return {"pass_rate": round(sum(auto) / len(auto), 3) if auto else None,
            "success": bool(auto) and all(auto),
            "failed": [a["type"] for a, r in res if r is False]}


# ------------------------------------------------------------ stats
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def bootstrap_mean_ci(xs, iters=2000, seed=1):
    if not xs: return (0.0, 0.0, 0.0)
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(iters))
    return (round(sum(xs) / len(xs), 3), round(means[int(.025 * iters)], 3), round(means[int(.975 * iters)], 3))


# ------------------------------------------------------------ runner
def run_benchmark(tasks, registry: Registry, model, out_dir: str | Path, conditions=CONDITIONS,
                  trials: int = 1, evidence: EvidenceStore | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    trace, rows = out / "traces.jsonl", []
    for task in tasks:
        decisions = {m: route(task, registry, evidence, mode=m, log_path=out / "routing.jsonl")
                     for m in ("single", "composition")}
        for cond in conditions:
            plan = decisions[cond]["plan"] if cond in decisions else None
            if cond in decisions and decisions[cond]["status"] != "selected":
                cond_eff, plan = "strong", None  # declared fallback
            else:
                cond_eff = cond
            for trial in range(trials):
                # composition is a genuine two-pass run (draft -> independent verify -> repair),
                # not only a longer prompt. The extra call is a real cost and is reported as such.
                rec = execute(model, task, cond_eff, trace, verify=(cond_eff == "composition"),
                              registry=registry, plan=plan)
                s = score_output(task, rec["output"]) if not rec["error"] else {"pass_rate": 0.0, "success": False, "failed": ["error"]}
                rows.append({"task": task["id"], "condition": cond, "effective": cond_eff, "trial": trial,
                             "tokens": usage_tokens(rec["usage"]), **s})
    (out / "scores.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    report = summarize(rows)
    (out / "REPORT.md").write_text(render_report(report), encoding="utf-8")
    return report


def summarize(rows, references=REFERENCES) -> dict:
    by = defaultdict(list)
    for r in rows:
        by[(r["condition"], r["task"])].append(r)
    conds = sorted({r["condition"] for r in rows}, key=lambda c: CONDITIONS.index(c) if c in CONDITIONS else 99)
    tasks = sorted({r["task"] for r in rows})
    summary = {}
    for c in conds:
        rs = [r for r in rows if r["condition"] == c]
        k = sum(r["success"] for r in rs)
        tok = sum(r["tokens"] for r in rs)
        summary[c] = {"n": len(rs), "task_success_rate": round(k / len(rs), 3) if rs else 0,
                      "success_ci": wilson(k, len(rs)),
                      "mean_pass_rate": round(sum(r["pass_rate"] or 0 for r in rs) / max(len(rs), 1), 3),
                      "cost_per_success_tokens": round(tok / k) if k else None,
                      "fallbacks": sum(r["effective"] != r["condition"] for r in rs)}
    refs = [r for r in references if r in conds]
    lifts = {}
    for ref in refs:
        per = {}
        for c in conds:
            if c == ref: continue
            diffs = []
            for t in tasks:
                a, b = by.get((c, t)), by.get((ref, t))
                if a and b:
                    diffs.append(sum(x["pass_rate"] or 0 for x in a) / len(a) - sum(x["pass_rate"] or 0 for x in b) / len(b))
            m, lo, hi = bootstrap_mean_ci(diffs)
            per[c] = {"lift": m, "ci95": [lo, hi], "paired_tasks": len(diffs),
                      "verdict": "lift" if lo > 0 else ("harm" if hi < 0 else "inconclusive")}
        lifts[ref] = per
    return {"conditions": summary, "lift": lifts, "references": refs,
            "reference": refs[0] if refs else None}


def render_report(rep: dict) -> str:
    L = ["# Benchmark report", "", "Objective assertions only. Blind human ranking is separate (see blind pack).", "",
         "| condition | n | success | 95% CI | mean pass | tokens/success | fallbacks |", "|---|---|---|---|---|---|---|"]
    for c, s in rep["conditions"].items():
        L.append(f"| {c} | {s['n']} | {s['task_success_rate']} | {s['success_ci']} | {s['mean_pass_rate']} | "
                 f"{s['cost_per_success_tokens']} | {s['fallbacks']} |")
    for ref, per in rep["lift"].items():
        L += ["", f"## Paired strategy lift vs `{ref}` (bootstrap 95% CI)", "",
              "| condition | lift | CI | tasks | verdict |", "|---|---|---|---|---|"]
        for c, l in per.items():
            L.append(f"| {c} | {l['lift']} | {l['ci95']} | {l['paired_tasks']} | {l['verdict']} |")
    L += ["", "Pre-registered falsification rule: if `composition` is not `lift` vs `strong_long` "
          "(the length- and coverage-matched baseline), explicit composition has no demonstrated "
          "independent value at this scale. Beating only `strong` is not enough."]
    return "\n".join(L) + "\n"


def export_blind(out_dir: str | Path, seed: int = 20261126, trial_only: int | None = None) -> Path:
    """traces.jsonl -> blind/<task>/<label>.md + key.json (keep key away from raters).

    trial_only: keep only the n-th attempt of each (task, condition); None keeps all,
    which is only useful for a small number of conditions.
    """
    out = Path(out_dir)
    recs = [json.loads(l) for l in (out / "traces.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rng, key = random.Random(seed), {}
    seen: dict[tuple, int] = {}
    by = defaultdict(list)
    for r in recs:
        k = (r["task_id"], r["condition"])
        r["trial"] = seen.get(k, 0)
        seen[k] = r["trial"] + 1
        if r["error"] or (trial_only is not None and r["trial"] != trial_only):
            continue
        by[r["task_id"]].append(r)
    for tid, rs in by.items():
        rng.shuffle(rs)
        key[tid] = {}
        for i, r in enumerate(rs):
            lab = chr(65 + i)
            p = out / "blind" / tid / f"{lab}.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(r["output"], encoding="utf-8")
            key[tid][lab] = {"condition": r["condition"], "prompt_sha": r["prompt_sha"]}
    (out / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    return out / "blind"
