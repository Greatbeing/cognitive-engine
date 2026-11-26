"""CLI: python -m cognitive_engine <import|lint|route|bench|blind>"""
import argparse
import json
import sys

from .registry import Registry, import_writing_engines
from .router import route, EvidenceStore
from .evaluation import load_we_tasks, run_benchmark, export_blind, CONDITIONS
from .runtime import MockModel, OpenAICompatModel

DEFAULT_REG = "registry"


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="cognitive_engine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("import"); a.add_argument("we_root"); a.add_argument("--out", default="registry/writing-engines.json")
    l = sub.add_parser("lint"); l.add_argument("--registry", default=DEFAULT_REG)
    r = sub.add_parser("route"); r.add_argument("objective"); r.add_argument("--registry", default=DEFAULT_REG)
    r.add_argument("--mode", default="composition")
    b = sub.add_parser("bench"); b.add_argument("we_root"); b.add_argument("--registry", default=DEFAULT_REG)
    b.add_argument("--out", default="runs/exp-001"); b.add_argument("--model", default="mock")
    b.add_argument("--trials", type=int, default=1); b.add_argument("--limit", type=int)
    b.add_argument("--conditions", default=",".join(CONDITIONS)); b.add_argument("--split", choices=["dev", "test"])
    x = sub.add_parser("blind"); x.add_argument("out")
    args = ap.parse_args(argv)

    if args.cmd == "import":
        reg = import_writing_engines(args.we_root)
        reg.dump(args.out)
        errs = reg.lint()
        avg = sum(p["completeness"] for p in reg.primitives.values()) / len(reg)
        print(f"imported {len(reg)} primitives, {len(reg.families())} families, "
              f"{len(errs)} invalid, mean completeness {avg:.2f} -> {args.out}")
        return 1 if errs else 0
    if args.cmd == "lint":
        errs = Registry.load(args.registry).lint()
        for pid, e in errs.items():
            print(pid, e)
        print("OK" if not errs else f"{len(errs)} invalid")
        return 1 if errs else 0
    if args.cmd == "route":
        print(json.dumps(route(args.objective, Registry.load(args.registry), mode=args.mode), ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "bench":
        reg = Registry.load(args.registry)
        tasks = [t for t in load_we_tasks(args.we_root) if not args.split or t["split"] == args.split][: args.limit]
        model = MockModel() if args.model == "mock" else OpenAICompatModel(args.model)
        rep = run_benchmark(tasks, reg, model, args.out, args.conditions.split(","), args.trials,
                            EvidenceStore(f"{args.out}/evidence.json"))
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "blind":
        print(export_blind(args.out))
        return 0


if __name__ == "__main__":
    sys.exit(main())
