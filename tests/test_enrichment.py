"""Audit scaling and interpretation against the unchanged research artifacts."""

import hashlib
import json
from pathlib import Path
import unittest

from cargo_forecast.data import load_bps_data
from cargo_forecast.enrichment import residual_acf, supplementary_metrics


class EnrichmentTests(unittest.TestCase):
    def test_mase_uses_only_95_training_differences(self):
        data = load_bps_data()
        diagnostics = json.loads(Path("artifacts/diagnostics.json").read_text(encoding="utf-8"))
        result = supplementary_metrics(data, diagnostics)
        for target, expected in (("bongkar", 1111.4), ("muat", 1768.5894736842106)):
            item = result[target]["mase"]
            self.assertEqual(item["training_differences"], 95)
            self.assertEqual(item["scale_end"], "2024-12")
            self.assertAlmostEqual(item["scale_ton"], expected, places=8)
            self.assertAlmostEqual(item["methods"]["neuralprophet"], diagnostics["series"][target]["metrics"]["neuralprophet"]["MAE"] / expected)

    def test_acf_centres_residuals_and_handles_constant_errors(self):
        self.assertAlmostEqual(residual_acf([11, 9, 11, 9])[0]["acf"], -0.75)
        self.assertTrue(all(r["acf"] == 0 for r in residual_acf([5, 5, 5, 5])))

    @unittest.skipUnless(Path("artifacts/enrichment.json").exists(), "Artefak interpretasi belum tersedia")
    def test_components_reproduce_evaluated_model_and_reconstruct_forecast(self):
        item = json.loads(Path("artifacts/enrichment.json").read_text(encoding="utf-8"))
        raw = Path("artifacts/report.json").read_bytes()
        report = json.loads(raw)
        self.assertEqual(item["source"]["report_sha256"], hashlib.sha256(raw).hexdigest())
        for target in ("bongkar", "muat"):
            components = item["series"][target]["components"]
            self.assertLessEqual(components["max_forecast_difference_ton"], 1e-5)
            self.assertEqual(len(components["timeline"]), 114)
            self.assertEqual(len(components["potential_changepoints"]), 10)
            self.assertEqual([r["lag"] for r in components["ar_weights"]], list(range(1, report["series"][target]["selected_n_lags"] + 1)))
            for component, forecast in zip(components["timeline"][-18:], report["series"][target]["test_predictions"], strict=True):
                self.assertEqual(component["ds"], forecast["ds"])
                self.assertAlmostEqual(component["trend"] + component["yearly"] + component["ar"], forecast["prediksi"], delta=0.01)


if __name__ == "__main__":
    unittest.main()
