import unittest

import pandas as pd

from cargo_forecast.data import load_bps_data, validate_monthly


class BpsDataTests(unittest.TestCase):
    def test_research_cutoff_and_july_exclusion(self):
        thesis = load_bps_data()
        latest = load_bps_data(through=pd.Timestamp("2026-07-01"))
        self.assertEqual((len(thesis), thesis["ds"].max()), (114, pd.Timestamp("2026-06-01")))
        self.assertEqual((len(latest), latest["ds"].max()), (115, pd.Timestamp("2026-07-01")))
        self.assertEqual(thesis.iloc[-1]["bongkar"], 9612)
        self.assertEqual(thesis.iloc[-1]["muat"], 14855)

    def test_months_must_be_contiguous(self):
        thesis = load_bps_data()
        gap = pd.concat([thesis, pd.DataFrame({"ds": [pd.Timestamp("2026-08-01")], "bongkar": [10000], "muat": [15000]})])
        with self.assertRaisesRegex(ValueError, "berurutan"):
            validate_monthly(gap)
        duplicate = pd.concat([thesis, thesis.tail(1)])
        with self.assertRaisesRegex(ValueError, "berurutan"):
            validate_monthly(duplicate)

    def test_zero_negative_missing_and_empty_inputs_are_rejected(self):
        thesis = load_bps_data()
        for bad in (0, -5, None):
            frame = thesis.copy()
            frame["muat"] = frame["muat"].astype(object)
            frame.loc[10, "muat"] = bad
            with self.assertRaisesRegex(ValueError, "positif"):
                validate_monthly(frame)
        with self.assertRaisesRegex(ValueError, "dimulai"):
            validate_monthly(thesis.iloc[0:0])
        mid_month = thesis.copy()
        mid_month.loc[5, "ds"] = pd.Timestamp("2017-06-15")
        with self.assertRaisesRegex(ValueError, "hari pertama"):
            validate_monthly(mid_month)
        with self.assertRaisesRegex(ValueError, "Kolom wajib"):
            validate_monthly(thesis.drop(columns="bongkar"))

    def test_experiment_rejects_empty_or_short_history(self):
        from cargo_forecast.modeling import retrain_target_for_next_month

        thesis = load_bps_data()
        with self.assertRaisesRegex(ValueError, "kosong"):
            retrain_target_for_next_month(thesis.iloc[0:0], "bongkar", 3)
        with self.assertRaisesRegex(ValueError, "60 bulan"):
            retrain_target_for_next_month(thesis.tail(59), "bongkar", 3)


if __name__ == "__main__":
    unittest.main()
