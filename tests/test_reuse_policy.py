import unittest

from cognitive_engine.reuse_policy import decide_reuse
from cognitive_engine.router import route_with_reuse
from cognitive_engine.registry import Registry


def candidate(cid, **overrides):
    value = {
        "id": cid,
        "fit_score": 0.9,
        "lifecycle": "validated",
        "verification_status": "verified",
        "license_status": "approved",
        "security_status": "approved",
        "compatibility": "compatible",
        "capabilities": [],
        "composable": False,
    }
    value.update(overrides)
    return value


class ReusePolicyTests(unittest.TestCase):
    def test_reuses_existing_verified_capability(self):
        result = decide_reuse({"id": "t1", "objective": "summarize a report"},
                              [candidate("tool.summary")])
        self.assertEqual(result["action"], "reuse")
        self.assertEqual(result["selected"], ["tool.summary"])
        self.assertFalse(result["execution_authorized"])

    def test_composes_complementary_capabilities(self):
        result = decide_reuse(
            {"id": "t2", "objective": "research and verify", "required_capabilities": ["research", "verify"]},
            [
                candidate("a.research", capabilities=["research"], composable=True, fit_score=0.91),
                candidate("b.verify", capabilities=["verify"], composable=True, fit_score=0.88),
            ],
        )
        self.assertEqual(result["action"], "compose")
        self.assertEqual(set(result["selected"]), {"a.research", "b.verify"})

    def test_adapts_partial_compatibility(self):
        result = decide_reuse({"objective": "transform data"},
                              [candidate("tool.transform", compatibility="partial")])
        self.assertEqual(result["action"], "adapt")
        self.assertEqual(result["selected"], ["tool.transform"])

    def test_unknown_license_defers_instead_of_building_duplicate(self):
        result = decide_reuse({"objective": "parse a document"},
                              [candidate("tool.parser", license_status="review_required")])
        self.assertEqual(result["action"], "defer")
        self.assertEqual(result["deferred"], ["tool.parser"])
        self.assertFalse(result["build_authorized"])

    def test_unverified_candidate_is_not_selected(self):
        result = decide_reuse({"objective": "classify a task"},
                              [candidate("agent.classifier", lifecycle="draft", verification_status="unverified")])
        self.assertEqual(result["action"], "defer")

    def test_builds_only_when_no_viable_or_unresolved_candidate_exists(self):
        result = decide_reuse({"objective": "specialized task"}, [])
        self.assertEqual(result["action"], "build_gap")
        self.assertTrue(result["build_authorized"])

    def test_rejects_known_incompatible_candidate(self):
        result = decide_reuse({"objective": "process data"},
                              [candidate("unsafe.tool", security_status="rejected")])
        self.assertEqual(result["action"], "build_gap")
        self.assertEqual(result["rejected"], ["unsafe.tool"])

    def test_low_fit_candidate_does_not_block_gap(self):
        result = decide_reuse({"objective": "specialized task"},
                              [candidate("weak.match", fit_score=0.2)])
        self.assertEqual(result["action"], "build_gap")
        self.assertEqual(result["not_fit"], ["weak.match"])

    def test_deterministic_tie_breaking(self):
        result = decide_reuse({"objective": "do task"},
                              [candidate("z.tool"), candidate("a.tool")])
        self.assertEqual(result["selected"], ["a.tool"])

    def test_router_uses_external_capability_before_internal_primitives(self):
        result = route_with_reuse(
            {"id": "t3", "objective": "summarize a report"},
            Registry(),
            [candidate("external.summarizer")],
        )
        self.assertEqual(result["strategy_source"], "external_capability")
        self.assertEqual(result["plan"][0]["capability"], "external.summarizer")
        self.assertFalse(result["execution_authorized"])

    def test_router_abstains_when_reuse_candidate_needs_review(self):
        result = route_with_reuse(
            {"id": "t4", "objective": "summarize a report"},
            Registry(),
            [candidate("external.summarizer", license_status="review_required")],
        )
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["strategy_source"], "human_review")

    def test_router_falls_back_to_internal_primitives_only_after_gap(self):
        result = route_with_reuse(
            {"id": "t5", "objective": "写一篇公众号文章：年轻人周末流行逛菜市场"},
            Registry(),
            [],
        )
        self.assertEqual(result["strategy_source"], "internal_cognitive_primitives")
        self.assertEqual(result["reuse_decision"]["action"], "build_gap")
        self.assertFalse(result["execution_authorized"])


    def test_incomplete_composition_does_not_silently_select_partial_candidate(self):
        result = decide_reuse(
            {"objective": "research and verify", "required_capabilities": ["research", "verify"]},
            [candidate("a.research", capabilities=["research"], composable=True)],
        )
        self.assertEqual(result["action"], "build_gap")
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["required_capabilities_uncovered"], ["research", "verify"])

    def test_invalid_candidate_and_duplicate_ids_fail_closed(self):
        with self.assertRaises(ValueError):
            decide_reuse({"objective": "x"}, [candidate("bad", fit_score=1.5)])
        with self.assertRaises(ValueError):
            decide_reuse({"objective": "x"}, [candidate("same"), candidate("same")])


if __name__ == "__main__":
    unittest.main()
