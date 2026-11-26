"""Primitive Registry: load, validate, import, index."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "primitive.schema.json"
OPTIONAL_SPEC_FIELDS = ["trigger_conditions", "preconditions", "inputs", "outputs", "postconditions",
                        "evaluation", "failure_modes", "resource_profile", "safety_constraints", "transfer"]


# ------------------------------------------------------------ validation (minimal JSON-Schema subset)
def _check(value, schema, path, errors):
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "number": (int, float)}
    if t and not isinstance(value, types[t]):
        errors.append(f"{path}: expected {t}")
        return
    if t == "string":
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: too short")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} !~ {schema['pattern']}")
    if t == "number":
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            errors.append(f"{path}: out of range")
    if t == "array":
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs >= {schema['minItems']} items")
        for i, v in enumerate(value):
            _check(v, schema.get("items", {}), f"{path}[{i}]", errors)
    if t == "object":
        for r in schema.get("required", []):
            if r not in value:
                errors.append(f"{path}.{r}: required")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _check(v, props[k], f"{path}.{k}", errors)
            elif isinstance(schema.get("additionalProperties"), dict):
                _check(v, schema["additionalProperties"], f"{path}.{k}", errors)


def validate(prim: dict, schema: dict | None = None) -> list[str]:
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    _check(prim, schema, "$", errors)
    return errors


def completeness(prim: dict) -> float:
    return round(sum(1 for f in OPTIONAL_SPEC_FIELDS if prim.get(f)) / len(OPTIONAL_SPEC_FIELDS), 2)


# ------------------------------------------------------------ registry
@dataclass
class Registry:
    primitives: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "Registry":
        path = Path(path)
        files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
        reg = cls()
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            for p in data if isinstance(data, list) else data.get("primitives", [data]):
                reg.add(p)
        return reg

    def add(self, prim: dict) -> None:
        if prim["id"] in self.primitives:
            raise ValueError(f"duplicate id {prim['id']}")
        self.primitives[prim["id"]] = prim

    def get(self, pid: str) -> dict:
        return self.primitives[pid]

    def __len__(self):
        return len(self.primitives)

    def lint(self) -> dict[str, list[str]]:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        return {pid: e for pid, p in self.primitives.items() if (e := validate(p, schema))}

    def families(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for pid, p in self.primitives.items():
            out.setdefault(p["family"], []).append(pid)
        return out

    def search(self, *, family=None, tag=None, domain=None, kind=None, min_lifecycle=None):
        order = ["proposed", "draft", "tested", "validated", "stable"]
        for p in self.primitives.values():
            if family and p["family"] != family: continue
            if tag and tag not in p.get("tags", []): continue
            if domain and p.get("domain") != domain: continue
            if kind and p.get("kind") != kind: continue
            if min_lifecycle and (p["lifecycle"] not in order or order.index(p["lifecycle"]) < order.index(min_lifecycle)): continue
            yield p

    def dump(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({"schema_version": "0.1", "primitives": list(self.primitives.values())},
                                         ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------ importer: writing-engines atoms -> primitives
FIELD_RE = re.compile(r"\*\*(族|定义|原文证据|白话示范|常见错误|触发|何时用|适用|操作|步骤)\*\*[：:]\s*(.+?)(?=\n\*\*[^*]+\*\*[：:]|\n#|\n---|\Z)", re.S)


def _section(text: str, heading: str) -> str:
    h = heading.strip()
    i = text.find(h)
    if i < 0:
        return ""
    level = len(h) - len(h.lstrip("#"))
    rest = text[i + len(h):]
    m = re.search(r"\n#{1,%d}[ \d]" % max(level, 1), rest)
    return rest[: m.start()] if m else rest


def _table_fields(text: str, num: str, name: str) -> dict:
    """Fallback for table-format atom files: | n | name | definition | example | family | and
    misuse rows | n name | error | fix |."""
    out = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == num and cells[1] == name and "定义" not in out:
            out["定义"] = cells[2]
            out["白话示范"] = cells[3]
        elif len(cells) >= 3 and cells[0] == f"{num} {name}" and "常见错误" not in out:
            out["常见错误"] = cells[1] + "——" + cells[2]
    return out


def _split_steps(definition: str) -> list[str]:
    parts = [s.strip(" 。；;") for s in re.split(r"[。；;]|→|->", definition) if s.strip(" 。；;")]
    return parts or [definition.strip()]


def import_writing_engines(we_root: str | Path) -> Registry:
    we_root = Path(we_root)
    atoms = json.loads((we_root / "atoms" / "index.json").read_text(encoding="utf-8"))
    reg = Registry()
    cache: dict[str, str] = {}
    for a in atoms:
        f = a["file"]
        if f not in cache:
            fp = we_root / f
            cache[f] = fp.read_text(encoding="utf-8") if fp.exists() else ""
        fields = {k: " ".join(v.split()) for k, v in FIELD_RE.findall(_section(cache[f], a["heading"]))}
        if not fields.get("定义"):
            fields.update(_table_fields(cache[f], a["id"].split(".")[1], a["name"].strip()))
        definition = fields.get("定义") or a["name"]
        engine, num = a["id"].split(".")
        prim = {
            "schema_version": "0.1",
            "id": f"we.{engine}.a{num}",
            "name": a["name"].strip(),
            "version": "0.1.0",
            "purpose": definition,
            "family": a["family"],
            "kind": "domain",
            "domain": "writing",
            "tags": [a["engine"], f"family:{a['family']}"],
            "procedure": _split_steps(definition),
            "failure_modes": [fields["常见错误"]] if fields.get("常见错误") else [],
            "examples": [fields["白话示范"]] if fields.get("白话示范") else [],
            "lifecycle": "draft",
            "provenance": {"source": "writing-engines", "source_ref": f"{f}#{a['heading'].strip()}",
                           "evidence": fields.get("原文证据", "")},
        }
        trig = fields.get("触发") or fields.get("何时用") or fields.get("适用")
        if trig:
            prim["trigger_conditions"] = [trig]
        prim["completeness"] = completeness(prim)
        reg.add(prim)
    return reg
