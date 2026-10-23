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


if __name__ == "__main__":
    unittest.main()
