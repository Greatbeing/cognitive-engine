"""Minimal runtime: model adapters, prompt compilation per condition, JSONL traces."""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path

from .registry import Registry

STRONG_PROMPT = ("你是一位资深作者兼编辑。动笔前先想清楚读者是谁、核心观点是什么；"
                 "只使用给定素材，不编造人物与数据；结构清楚，开头抓人，细节具体，避免套话与空洞总结；"
                 "写完自查一遍再输出。")


class MockModel:
    """Deterministic offline adapter for pipeline tests. Not a quality signal."""
    name = "mock"

    def complete(self, prompt: str, system: str | None = None) -> dict:
        h = hashlib.sha256(((system or "") + prompt).encode()).hexdigest()
        body = "不是热闹而是确认。他说：“" + h[:8] + "”。"
        return {"text": f"# 标题\n\n{body}\n" + "具体的早晨，七点。" * (40 + int(h[:2], 16) % 80),
                "usage": {"prompt_tokens": len(prompt) // 2, "completion_tokens": 400}}


class OpenAICompatModel:
    """Any OpenAI-compatible /chat/completions endpoint. Env: CE_BASE_URL, CE_API_KEY, CE_MODEL."""

    def __init__(self, model=None, base_url=None, api_key=None, temperature=0.7, seed=7):
        self.name = model or os.environ["CE_MODEL"]
        self.base = (base_url or os.environ.get("CE_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.key = api_key or os.environ.get("CE_API_KEY", "")
        self.temperature, self.seed = temperature, seed

    def complete(self, prompt: str, system: str | None = None) -> dict:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = json.dumps({"model": self.name, "messages": msgs, "temperature": self.temperature,
                           "seed": self.seed}).encode()
        req = urllib.request.Request(f"{self.base}/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.loads(r.read())
        return {"text": d["choices"][0]["message"]["content"], "usage": d.get("usage", {})}


def render_task(task: dict) -> str:
    lines = [task["objective"]]
    for k, v in task.get("constraints", {}).items():
        lines.append(f"{k}：{v}")
    mats = task.get("inputs", {}).get("material", [])
    if mats:
        lines.append("\n素材（只能使用以下素材）：")
        for m in mats:
            lines.append("- " + "｜".join(str(m[k]) for k in ("tag", "name", "scene", "quote") if k in m))
    return "\n".join(lines)


def compile_prompt(task: dict, condition: str, registry: Registry | None = None, plan: list | None = None,
                   engine_text: str | None = None) -> tuple[str | None, str]:
    """Returns (system, user). Conditions: baseline | strong | single | composition | engine."""
    user = render_task(task)
    if condition == "baseline":
        return None, user
    if condition == "strong":
        return STRONG_PROMPT, user
    if condition == "engine":
        return engine_text, user
    steps = []
    for s in plan or []:
        p = registry.get(s["primitive"])
        ops = "；".join(p["procedure"])
        avoid = (" 避免：" + p["failure_modes"][0]) if p.get("failure_modes") else ""
        steps.append(f"{s['step']}. 【{p['name']}】{ops}。{avoid}")
    system = (STRONG_PROMPT + "\n\n按以下认知操作顺序组织全文（内部使用，不要在正文中提及步骤名或编号）：\n"
              + "\n".join(steps))
    return system, user


def execute(model, task: dict, condition: str, trace_path: str | Path | None = None, **kw) -> dict:
    system, user = compile_prompt(task, condition, **kw)
    t0 = time.time()
    err, out = None, {"text": "", "usage": {}}
    try:
        out = model.complete(user, system=system)
    except Exception as e:  # failure is a result
        err = repr(e)
    rec = {"schema_version": "0.1", "type": "ExecutionTrace", "task_id": task["id"], "condition": condition,
           "model": getattr(model, "name", "?"), "plan": kw.get("plan"),
           "prompt_sha": hashlib.sha256(((system or "") + user).encode()).hexdigest()[:12],
           "latency_s": round(time.time() - t0, 3), "usage": out.get("usage", {}), "error": err,
           "output": out["text"], "timestamp": t0}
    if trace_path:
        Path(trace_path).parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
