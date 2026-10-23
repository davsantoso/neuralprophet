"""Audit the supplementary loss curve and epoch-sensitivity artifact."""

import hashlib
import json
from pathlib import Path
import unittest

from cargo_forecast.data import load_bps_data
from cargo_forecast.enrichment import data_sha256


ARTIFACT = Path("artifacts/training_diagnostics.json")


@unittest.skipUnless(ARTIFACT.exists(), "Artefak diagnostik pelatihan belum tersedia")
class TrainingDiagnosticsTests(unittest.TestCase):
    def test_artifact_reproduces_official_model_and_uses_validation_only(self):
        item = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        raw = Path("artifacts/report.json").read_bytes()
        report = json.loads(raw)
        self.assertEqual(item["source"], {"report_sha256": hashlib.sha256(raw).hexdigest(), "data_sha256": data_sha256(load_bps_data())})
        for target in ("bongkar", "muat"):
            series = item["series"][target]
            official = report["series"][target]
            self.assertEqual(series["selected_n_lags"], official["selected_n_lags"])
            self.assertLessEqual(series["max_forecast_difference_ton"], 1e-5)
            self.assertEqual([row["epoch"] for row in series["loss_curve"]], list(range(1, 101)))
            self.assertEqual([row["epochs"] for row in series["epoch_sensitivity"]], [25, 50, 100, 150, 200])
            official_validation = next(c["metrics"]["MAE"] for c in official["validation_candidates"] if c["n_lags"] == official["selected_n_lags"])
            at_100 = next(row for row in series["epoch_sensitivity"] if row["epochs"] == 100)
            self.assertAlmostEqual(at_100["validation"]["MAE"], official_validation, delta=1e-4)


if __name__ == "__main__":
    unittest.main()
