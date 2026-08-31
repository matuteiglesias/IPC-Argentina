import json
import math
import unittest
from pathlib import Path

from arg_price.v2 import (
    build_consensus,
    conversion_factor,
    eligibility_status,
    load_policy,
    member_for_source,
    normalize_source_rows,
)

ROOT = Path(__file__).parents[1]
POLICY = load_policy(ROOT / "contracts/panel_v2.json")


def obs(source_id, period, value):
    return {
        "source_id": source_id,
        "period": period,
        "source_index": value,
        "source_base_or_vintage": "fixture",
        "value_status": "observed",
        "source_snapshot_sha256": "fixture-" + source_id,
        "parser_id": source_id + "/fixture",
    }


class V2ConstitutionTests(unittest.TestCase):
    def test_fixed_five_member_roster(self):
        self.assertEqual(
            [m["member_id"] for m in POLICY["panel_members"]],
            ["indec", "caba", "cordoba", "san_luis", "neuquen"],
        )
        self.assertFalse(POLICY["aggregation"]["dynamic_source_substitution"])

    def test_indec_eligibility_calendar(self):
        self.assertEqual(eligibility_status("indec_ipc_gba_historical", "2006-12-01", POLICY), "eligible")
        self.assertEqual(eligibility_status("indec_ipc_gba_historical", "2007-01-01", POLICY), "excluded_by_policy")
        self.assertEqual(eligibility_status("indec_ipc_national", "2014-06-01", POLICY), "excluded_by_policy")
        self.assertEqual(eligibility_status("indec_ipc_national", "2016-07-01", POLICY), "transition_unapproved")
        self.assertEqual(eligibility_status("indec_ipc_national", "2017-01-01", POLICY), "eligible")

    def test_unknown_source_cannot_enter_panel(self):
        with self.assertRaisesRegex(ValueError, "source_not_uniquely_bound_to_panel"):
            member_for_source("some_other_province", POLICY)


class V2NormalizationTests(unittest.TestCase):
    def test_rate_requires_consecutive_eligible_observations(self):
        rows = normalize_source_rows(
            [
                obs("indec_ipc_national", "2016-12-01", 100),
                obs("indec_ipc_national", "2017-01-01", 110),
                obs("indec_ipc_national", "2017-02-01", 121),
            ],
            POLICY,
        )
        by_period = {r["period"]: r for r in rows}
        self.assertEqual(by_period["2016-12-01"]["eligibility_status"], "transition_unapproved")
        self.assertEqual(by_period["2017-01-01"]["monthly_change_status"], "previous_period_not_eligible")
        self.assertEqual(by_period["2017-02-01"]["monthly_change_status"], "eligible_rate")
        self.assertAlmostEqual(float(by_period["2017-02-01"]["monthly_inflation_pct"]), 10.0)

    def test_source_base_scale_does_not_change_monthly_rate(self):
        original = normalize_source_rows(
            [obs("cordoba_ipc", "2025-01-01", 100), obs("cordoba_ipc", "2025-02-01", 104)],
            POLICY,
        )
        rebased = normalize_source_rows(
            [obs("cordoba_ipc", "2025-01-01", 700), obs("cordoba_ipc", "2025-02-01", 728)],
            POLICY,
        )
        self.assertAlmostEqual(float(original[-1]["monthly_inflation_pct"]), float(rebased[-1]["monthly_inflation_pct"]))


class V2ConsensusTests(unittest.TestCase):
    def fixture_rows(self, include_neuquen=True, include_san_luis=True):
        sources = [
            ("idecba_ipc_level_general_empalmed", 100.0, 1.02, 1.03),
            ("cordoba_ipc", 200.0, 1.025, 1.02),
        ]
        if include_san_luis:
            sources.append(("san_luis_ipc_provincial", 300.0, 1.015, 1.025))
        if include_neuquen:
            sources.append(("neuquen_ipc_provincial", 400.0, 1.03, 1.02))
        rows = []
        for sid, base, jan_factor, feb_factor in sources:
            dec = base
            jan = dec * jan_factor
            feb = jan * feb_factor
            rows.extend([
                obs(sid, "2015-12-01", dec),
                obs(sid, "2016-01-01", jan),
                obs(sid, "2016-02-01", feb),
            ])
        return normalize_source_rows(rows, POLICY)

    def test_four_sources_produce_strong_coverage_at_base(self):
        consensus = build_consensus(self.fixture_rows(), POLICY)
        base = next(r for r in consensus if r["period"] == "2016-01-01")
        self.assertEqual(base["contributing_source_count"], "4")
        self.assertEqual(base["coverage_class"], "strong_coverage")
        self.assertEqual(base["approved_mode_eligible"], "true")
        self.assertEqual(base["consensus_index"], "100")
        self.assertIn("indec:unavailable", base["noncontributing_member_reasons"])

    def test_three_sources_are_acceptable(self):
        consensus = build_consensus(self.fixture_rows(include_neuquen=False), POLICY)
        base = next(r for r in consensus if r["period"] == "2016-01-01")
        self.assertEqual(base["contributing_source_count"], "3")
        self.assertEqual(base["coverage_class"], "acceptable_coverage")
        self.assertEqual(base["approved_mode_eligible"], "true")

    def test_two_sources_are_thin_and_not_approved_mode(self):
        consensus = build_consensus(self.fixture_rows(include_neuquen=False, include_san_luis=False), POLICY)
        base = next(r for r in consensus if r["period"] == "2016-01-01")
        self.assertEqual(base["contributing_source_count"], "2")
        self.assertEqual(base["coverage_class"], "thin_coverage")
        self.assertEqual(base["approved_mode_eligible"], "false")

    def test_consensus_is_simple_equal_weight_mean(self):
        consensus = build_consensus(self.fixture_rows(), POLICY)
        base = next(r for r in consensus if r["period"] == "2016-01-01")
        expected = (2.0 + 2.5 + 1.5 + 3.0) / 4
        self.assertAlmostEqual(float(base["consensus_monthly_inflation_pct"]), expected)
        self.assertGreater(float(base["population_std_monthly_inflation_pct"]), 0)

    def test_index_and_conversion_chain(self):
        consensus = build_consensus(self.fixture_rows(), POLICY)
        feb = next(r for r in consensus if r["period"] == "2016-02-01")
        self.assertEqual(feb["index_status"], "anchored")
        factor = conversion_factor(consensus, "2016-01-01", "2016-02-01")
        self.assertAlmostEqual(factor, float(feb["consensus_index"]) / 100.0)


if __name__ == "__main__":
    unittest.main()
