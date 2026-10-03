"""Verify all nested boundaries and resumed checkpoints without training models."""

import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from cargo_forecast.data import load_bps_data
from cargo_forecast.walkforward import TARGET_DATES, validate_row, walk_forward


class WalkForwardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_bps_data()

    def test_nested_fit_boundaries_and_checkpoint_resume(self):
        def fit(frame, target, lag, **kwargs):
            return {"last_fit": frame["ds"].max(), "target": target, "lag": lag}

        def predict(model, available, target, start):
            self.assertLess(model["last_fit"], start)
            self.assertEqual(len(available.loc[available["ds"] >= start]), 12)
            result = available.loc[available["ds"] >= start, ["ds", target]].rename(columns={target: "aktual"}).copy()
            result["prediksi"] = result["aktual"] + model["lag"]
            return result

        def forecast(model, available, target):
            self.assertEqual(model["last_fit"], available["ds"].max())
            return {"ds": (available["ds"].max() + pd.DateOffset(months=1)).strftime("%Y-%m"),
                    "prediksi": float(available[target].iloc[-1])}

        Path(".tmp").mkdir(exist_ok=True)
        checkpoint = Path(".tmp/test_walk_forward_checkpoint.json")
        checkpoint.unlink(missing_ok=True)
        try:
            with patch("cargo_forecast.walkforward._fit", side_effect=fit) as fits, patch("cargo_forecast.walkforward._predict_range", side_effect=predict), patch("cargo_forecast.walkforward._forecast_next", side_effect=forecast), patch("cargo_forecast.walkforward.gc.collect"):
                result = walk_forward(self.data, report_sha256="test", checkpoint=checkpoint)
            self.assertEqual(fits.call_count, 336)
            for target in ("bongkar", "muat"):
                rows = result["series"][target]["monthly"]
                self.assertEqual(len(rows), 42)
                self.assertEqual(rows[0]["inner_train_months"], 60)
                self.assertEqual(rows[0]["inner_validation_start"], "2022-01")
                self.assertEqual(rows[-1]["origin"], "2026-05")
                self.assertTrue(all(r["selected_n_lags"] == 3 for r in rows))
            with patch("cargo_forecast.walkforward._fit", side_effect=AssertionError("resume must not refit")):
                self.assertEqual(walk_forward(self.data, report_sha256="test", checkpoint=checkpoint, workers=4), result)
            with self.assertRaises(ValueError):
                walk_forward(self.data, report_sha256="different", checkpoint=checkpoint)
        finally:
            checkpoint.unlink(missing_ok=True)

    @unittest.skipUnless(Path("artifacts/walk_forward.json").exists(), "Backtest nyata belum tersedia")
    def test_real_artifact_has_all_months_and_correct_past_only_boundaries(self):
        result = json.loads(Path("artifacts/walk_forward.json").read_text(encoding="utf-8"))
        self.assertEqual(result["source"]["report_sha256"], hashlib.sha256(Path("artifacts/report.json").read_bytes()).hexdigest())
        for target in ("bongkar", "muat"):
            rows = result["series"][target]["monthly"]
            self.assertEqual(len(rows), 42)
            for row, month in zip(rows, TARGET_DATES, strict=True):
                validate_row(row, self.data, target, month)
            official = json.loads(Path("artifacts/report.json").read_text(encoding="utf-8"))["series"][target]
            first_test = next(r for r in rows if r["ds"] == "2025-01")
            self.assertEqual(first_test["selected_n_lags"], official["selected_n_lags"])
            self.assertAlmostEqual(first_test["neuralprophet"], official["test_predictions"][0]["prediksi"], delta=1e-5)
            for method in ("neuralprophet", "last_month"):
                mae = sum(abs(r[method] - r["actual"]) for r in rows) / 42
                self.assertAlmostEqual(result["series"][target]["metrics"]["all_42"][method]["MAE"], mae, places=8)


if __name__ == "__main__":
    unittest.main()
