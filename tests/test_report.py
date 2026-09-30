"""Independent checks of the saved thesis experiment."""

import json
import math
from pathlib import Path
import unittest

import pandas as pd

from cargo_forecast.data import load_bps_data


REPORT_PATH = Path("artifacts/report.json")


@unittest.skipUnless(REPORT_PATH.exists(), "Laporan model belum dibuat")
class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.data = load_bps_data().set_index("ds")

    def test_dates_and_selected_configuration(self):
        self.assertEqual(self.report["n_observations"], 114)
        self.assertEqual(self.report["cutoff"], "2026-06")
        self.assertEqual(self.report["horizon_months"], 1)
        for target in ("bongkar", "muat"):
            series = self.report["series"][target]
            candidates = series["validation_candidates"]
            self.assertEqual([item["n_lags"] for item in candidates], [3, 6, 12])
            best = min(candidates, key=lambda item: (item["metrics"]["MAE"], item["n_lags"]))
            self.assertEqual(series["selected_n_lags"], best["n_lags"])
            self.assertEqual([row["ds"] for row in series["test_predictions"]], list(pd.period_range("2025-01", "2026-06", freq="M").astype(str)))
            self.assertEqual(series["next_month"]["ds"], "2026-07")

    def test_actuals_and_metrics(self):
        for target in ("bongkar", "muat"):
            series = self.report["series"][target]
            errors = []
            percentage_errors = []
            for row in series["test_predictions"]:
                observed = self.data.loc[pd.Timestamp(row["ds"] + "-01"), target]
                self.assertEqual(row["aktual"], observed)
                self.assertTrue(math.isfinite(row["prediksi"]))
                error = row["prediksi"] - observed
                errors.append(error)
                percentage_errors.append(abs(error) / observed)
            expected = {
                "MAE": sum(abs(error) for error in errors) / len(errors),
                "RMSE": math.sqrt(sum(error * error for error in errors) / len(errors)),
                "MAPE": 100 * sum(percentage_errors) / len(percentage_errors),
            }
            for metric, value in expected.items():
                self.assertAlmostEqual(series["test_metrics"][metric], value, places=8)


if __name__ == "__main__":
    unittest.main()

