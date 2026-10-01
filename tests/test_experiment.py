"""Exercise the optional retraining path with the July BPS observation."""

import json
import math
from pathlib import Path
import unittest

import pandas as pd

from cargo_forecast.data import load_bps_data
from cargo_forecast.modeling import retrain_target_for_next_month


REPORT_PATH = Path("artifacts/report.json")


@unittest.skipUnless(REPORT_PATH.exists(), "Laporan model belum dibuat")
class RetrainingTests(unittest.TestCase):
    def test_july_data_produces_august_forecasts(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        lags = {target: report["series"][target]["selected_n_lags"] for target in ("bongkar", "muat")}
        frame = load_bps_data(through=pd.Timestamp("2026-07-01"))
        for target in ("bongkar", "muat"):
            result = retrain_target_for_next_month(frame, target, lags[target])
            self.assertEqual(result["n_observations"], 115)
            self.assertEqual(result["last_observation"], "2026-07")
            self.assertEqual(result["target"], target)
            forecast = result["forecast"]
            self.assertEqual(forecast["ds"], "2026-08")
            self.assertTrue(math.isfinite(forecast["prediksi"]))


if __name__ == "__main__":
    unittest.main()

