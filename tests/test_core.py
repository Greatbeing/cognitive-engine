import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cognitive_engine.registry import Registry, validate, import_writing_engines  # noqa: E402
from cognitive_engine.router import route, normalize, EvidenceStore  # noqa: E402
from cognitive_engine.evaluation import check, wilson, run_benchmark, load_we_tasks  # noqa: E402
from cognitive_engine.runtime import MockModel, compile_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WE = ROOT.parent / "writing-engines"


def prim(pid, fam, **kw):
    p = {"schema_version": "0.1", "id": pid, "name": pid, "version": "0.1.0", "purpose": "do a thing",
         "family": fam, "procedure": ["step"], "lifecycle": "draft", "provenance": {"source": "test"}}
    p.update(kw)
    return p


class T(unittest.TestCase):
    def reg(self):
        r = Registry()
        for i, f in enumerate(["反转揭底", "命名", "典型画像", "小处起笔", "预设驳论", "金句断语"]):
            r.add(prim(f"t.p{i}", f))
        return r

    def test_schema(self):
        self.assertEqual(validate(prim("a.b", "x")), [])
        self.assertTrue(validate(prim("Bad Id", "x")))
        self.assertTrue(validate({**prim("a.b", "x"), "procedure": []}))

    def test_duplicate(self):
        r = self.reg()
        with self.assertRaises(ValueError):
            r.add(prim("t.p0", "x"))

    def test_route_and_abstain(self):
        d = route("写一篇公众号文章：年轻人周末流行逛菜市场", self.reg())
        self.assertEqual(d["status"], "selected")
        self.assertEqual(d["features"]["task_class"], "city_observation")
        self.assertEqual(d["plan"][0]["family"], "反转揭底")
        self.assertEqual(route("你好", self.reg())["status"], "abstain")
        self.assertEqual(route("写一篇时评：给出投资建议", self.reg())["status"], "escalate")
        self.assertEqual(len(route("写一篇时评", self.reg(), mode="single")["plan"]), 1)

    def test_evidence_changes_rank(self):
        r = self.reg(); r.add(prim("t.alt", "反转揭底"))
        ev = EvidenceStore()
        for _ in range(5): ev.record("city_observation", "t.alt", True)
        self.assertEqual(route("公众号 城市 现象", r, ev)["plan"][0]["primitive"], "t.alt")

    def test_checks_and_stats(self):
        self.assertTrue(check({"type": "no_regex", "value": "赋能"}, "正常"))
        self.assertFalse(check({"type": "uses_all", "value": ["沈可"]}, "郑姐"))
        lo, hi = wilson(12, 20)
        self.assertTrue(lo < .5 < hi)

    def test_strong_long_controls_length_and_coverage(self):
        from cognitive_engine.runtime import STRONG_PROMPT, STRONG_LONG_PROMPT, compile_prompt
        self.assertTrue(STRONG_LONG_PROMPT.startswith(STRONG_PROMPT))
        self.assertIn("原样引用其原话", STRONG_LONG_PROMPT)
        self.assertIn("字数上限", STRONG_LONG_PROMPT)
        t = normalize({"objective": "写点东西"})
        self.assertEqual(compile_prompt(t, "strong_long")[0], STRONG_LONG_PROMPT)

    def test_composition_is_two_pass(self):
        from cognitive_engine.runtime import execute, _strip_checklist

        class Counting(MockModel):
            def __init__(self):
                self.calls = 0; self.name = "counting"

            def complete(self, prompt, system=None):
                self.calls += 1
                if system and "严格的审核者" in system:
                    return {"text": "问题清单：无。\n\n修订全文\n\n# 修好的稿子\n正文。", "usage": {"total_tokens": 10}}
                return {"text": "# 草稿\n正文。", "usage": {"total_tokens": 10}}

        t = normalize({"objective": "写点东西", "inputs": {"material": [{"name": "甲", "quote": "乙"}]}})
        m = Counting()
        rec = execute(m, t, "composition", plan=[], verify=True)
        self.assertEqual(m.calls, 2)
        self.assertEqual([p["stage"] for p in rec["passes"]], ["draft", "verify"])
        self.assertTrue(rec["output"].startswith("# 修好的稿子"))
        self.assertNotIn("问题清单", rec["output"])
        self.assertEqual(_strip_checklist("没有标记的文本"), "没有标记的文本")
        m2 = Counting(); execute(m2, t, "composition", plan=[]); self.assertEqual(m2.calls, 1)
        from cognitive_engine.runtime import _merge_usage
        from cognitive_engine.evaluation import usage_tokens
        self.assertEqual(_merge_usage({"total_tokens": 5, "d": {"x": 1}}, {"total_tokens": 7, "d": {"x": 2}}),
                         {"total_tokens": 12, "d": {"x": 2}})
        self.assertEqual(usage_tokens({"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7}), 7)
        self.assertEqual(usage_tokens({"prompt_tokens": 3, "completion_tokens": 4}), 7)

    def test_no_leak_in_compiled_user_prompt(self):
        r = self.reg()
        t = normalize({"objective": "公众号 城市"})
        sysmsg, user = compile_prompt(t, "composition", registry=r, plan=route(t, r)["plan"])
        self.assertIn("不要在正文中提及", sysmsg)
        self.assertNotIn("【", user)

    @unittest.skipUnless((WE / "atoms" / "index.json").exists(), "writing-engines not cloned")
    def test_import_and_bench_smoke(self):
        reg = import_writing_engines(WE)
        self.assertEqual(len(reg), 182)
        self.assertEqual(reg.lint(), {})
        with tempfile.TemporaryDirectory() as d:
            rep = run_benchmark(load_we_tasks(WE)[:2], reg, MockModel(), d)
            self.assertIn("composition", rep["lift"]["strong_long"])
            self.assertTrue((Path(d) / "traces.jsonl").exists())

    def test_general_and_contracts(self):
        import json
        from cognitive_engine.registry import _check
        reg = Registry.load(ROOT / "registry" / "general.json")
        self.assertEqual(reg.lint(), {})
        r = self.reg()
        for p in reg.primitives.values(): r.add(p)
        d = route({"objective": "公众号 城市 现象", "inputs": {"material": [{"name": "x"}]}}, r)
        self.assertEqual([s["primitive"] for s in d["plan"][-2:]], ["ce.general.evidence_grounding", "ce.general.redline_audit"])
        defs = json.loads((ROOT / "schema" / "contracts.schema.json").read_text(encoding="utf-8"))["$defs"]
        errs = []; _check(d, defs["RoutingDecision"], "$", errs); self.assertEqual(errs, [])

if __name__ == "__main__":
    unittest.main()
