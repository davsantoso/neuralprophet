"""Check the DM test arithmetic and its link to the frozen research artifacts."""

import hashlib
import json
from pathlib import Path
import unittest

from cargo_forecast.data import load_bps_data
from cargo_forecast.significance import build_significance, diebold_mariano, t_two_sided_p


class SignificanceTests(unittest.TestCase):
    def test_t_p_values_match_reference_table(self):
        self.assertAlmostEqual(t_two_sided_p(2.110, 17), 0.05, places=3)
        self.assertAlmostEqual(t_two_sided_p(2.0, 10), 0.07339, places=5)
        self.assertAlmostEqual(t_two_sided_p(1.0, 1), 0.5, places=10)
        self.assertEqual(t_two_sided_p(0.0, 5), 1.0)
        self.assertAlmostEqual(t_two_sided_p(-2.110, 17), t_two_sided_p(2.110, 17), places=12)

    def test_dm_is_antisymmetric_and_applies_small_sample_correction(self):
        actual = [10, 12, 11, 13, 12, 14]
        a = [11, 12, 12, 12, 13, 13]
        b = [9, 14, 10, 15, 10, 16]
        forward = diebold_mariano(actual, a, b, loss="absolute")
        backward = diebold_mariano(actual, b, a, loss="absolute")
        self.assertAlmostEqual(forward["dm_hln"], -backward["dm_hln"], places=12)
        self.assertAlmostEqual(forward["p_value"], backward["p_value"], places=12)
        self.assertAlmostEqual(forward["dm_hln"], forward["dm"] * (5 / 6) ** 0.5, places=12)
        self.assertLess(forward["mean_loss_difference"], 0)
        with self.assertRaises(ValueError):
            diebold_mariano(actual, a, a, loss="absolute")

    def test_artifact_matches_frozen_forecasts(self):
        raw = Path("artifacts/report.json").read_bytes()
        diagnostics = json.loads(Path("artifacts/diagnostics.json").read_text(encoding="utf-8"))
        walk_forward = json.loads(Path("artifacts/walk_forward.json").read_text(encoding="utf-8"))
        result = build_significance(load_bps_data(), diagnostics, walk_forward, report_sha256=hashlib.sha256(raw).hexdigest())
        for target in ("bongkar", "muat"):
            item = result["series"][target]
            self.assertEqual(item["test_18"]["comparisons"]["last_month"]["absolute"]["n"], 18)
            self.assertEqual(item["walk_forward_42"]["comparisons"]["last_month"]["absolute"]["n"], 42)
            # Seasonal naive on the 18 overlapping months must equal the official diagnostics baseline.
            seasonal = {row["ds"]: row["prediksi"] for row in item["walk_forward_42"]["same_month_last_year"]}
            for row in diagnostics["series"][target]["monthly"]:
                self.assertEqual(seasonal[row["ds"]], row["same_month_last_year"])
            self.assertAlmostEqual(item["walk_forward_42"]["metrics"]["neuralprophet"]["MAE"],
                                   walk_forward["series"][target]["metrics"]["all_42"]["neuralprophet"]["MAE"], places=9)
        saved = Path("artifacts/significance.json")
        if saved.exists():
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8")), json.loads(json.dumps(result)))


if __name__ == "__main__":
    unittest.main()
