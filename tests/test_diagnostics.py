"""Audit the supplementary baselines and seed results against frozen data."""

import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev
import unittest
from unittest.mock import patch

import pandas as pd

from cargo_forecast.data import load_bps_data
from cargo_forecast.diagnostics import build_diagnostics
from cargo_forecast.modeling import evaluate_seed_sensitivity


REPORT = Path("artifacts/report.json")
DIAGNOSTICS = Path("artifacts/diagnostics.json")


@unittest.skipUnless(REPORT.exists() and DIAGNOSTICS.exists(), "Artefak penelitian belum tersedia")
class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_bps_data().set_index("ds")
        cls.report_bytes = REPORT.read_bytes()
        cls.report = json.loads(cls.report_bytes)
        cls.saved = json.loads(DIAGNOSTICS.read_text(encoding="utf-8"))

    def test_baselines_use_past_months_on_exact_test_period(self):
        self.assertEqual(self.saved["source"]["report_sha256"], hashlib.sha256(self.report_bytes).hexdigest())
        manifest = json.loads(Path("artifacts/provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(self.saved["source"]["data_sha256"], manifest["research_dataset"]["canonical_csv_sha256"])
        for target in ("bongkar", "muat"):
            item = self.saved["series"][target]
            self.assertEqual(len(item["monthly"]), 18)
            for row in item["monthly"]:
                month = pd.Timestamp(row["ds"] + "-01")
                self.assertEqual(row["actual"], self.data.loc[month, target])
                self.assertEqual(row["last_month"], self.data.loc[month - pd.DateOffset(months=1), target])
                self.assertEqual(row["same_month_last_year"], self.data.loc[month - pd.DateOffset(months=12), target])
            for method in ("last_month", "same_month_last_year"):
                errors = [row[method] - row["actual"] for row in item["monthly"]]
                self.assertAlmostEqual(item["metrics"][method]["MAE"], mean(abs(error) for error in errors), places=8)
                self.assertAlmostEqual(item["metrics"][method]["RMSE"], math.sqrt(mean(error * error for error in errors)), places=8)
                self.assertAlmostEqual(item["metrics"][method]["MAPE"], 100 * mean(abs(error) / row["actual"] for error, row in zip(errors, item["monthly"], strict=True)), places=8)

    def test_seed_runs_and_official_report_reproduce(self):
        rebuilt = build_diagnostics(
            self.data.reset_index(),
            self.report,
            {target: self.saved["series"][target]["seed_runs"] for target in ("bongkar", "muat")},
            report_sha256=hashlib.sha256(self.report_bytes).hexdigest(),
        )
        for target in ("bongkar", "muat"):
            item = self.saved["series"][target]
            self.assertEqual([run["seed"] for run in item["seed_runs"]], [7, 21, 42, 123, 2026])
            self.assertEqual(item["seed_42_max_forecast_difference_from_official"], 0)
            self.assertEqual(rebuilt["series"][target]["metrics"], item["metrics"])
            values = [run["metrics"]["MAE"] for run in item["seed_runs"]]
            self.assertAlmostEqual(item["seed_summary"]["MAE"]["mean"], mean(values), places=8)
            self.assertAlmostEqual(item["seed_summary"]["MAE"]["sample_std"], stdev(values), places=8)

    def test_seed_fits_stop_before_test_period(self):
        def fake_predict(_model, frame, target, start):
            subset = frame.loc[frame["ds"] >= start, ["ds", target]].copy()
            subset = subset.rename(columns={target: "aktual"})
            subset["prediksi"] = subset["aktual"]
            return subset.reset_index(drop=True)

        with patch("cargo_forecast.modeling._fit", return_value=object()) as fit, patch("cargo_forecast.modeling._predict_range", side_effect=fake_predict):
            result = evaluate_seed_sensitivity(self.data.reset_index(), {"bongkar": 6, "muat": 3}, seeds=(7, 42, 123))
        self.assertEqual(fit.call_count, 6)
        for call in fit.call_args_list:
            self.assertEqual(call.args[0]["ds"].max(), pd.Timestamp("2024-12-01"))
        self.assertEqual(len(result["bongkar"]), 3)


if __name__ == "__main__":
    unittest.main()
