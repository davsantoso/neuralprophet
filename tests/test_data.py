import unittest

import pandas as pd

from cargo_forecast.data import load_bps_data, parse_additional_csv


class BpsDataTests(unittest.TestCase):
    def test_research_cutoff_and_july_exclusion(self):
        thesis = load_bps_data()
        latest = load_bps_data(through=pd.Timestamp("2026-07-01"))
        self.assertEqual((len(thesis), thesis["ds"].max()), (114, pd.Timestamp("2026-06-01")))
        self.assertEqual((len(latest), latest["ds"].max()), (115, pd.Timestamp("2026-07-01")))
        self.assertEqual(thesis.iloc[-1]["bongkar"], 9612)
        self.assertEqual(thesis.iloc[-1]["muat"], 14855)

    def test_uploaded_months_must_be_contiguous(self):
        thesis = load_bps_data()
        with self.assertRaisesRegex(ValueError, "dimulai"):
            parse_additional_csv(b"ds,bongkar,muat\n2026-08,10000,15000\n", thesis)
        appended = parse_additional_csv(b"ds,bongkar,muat\n2026-07,10633,15496\n", thesis)
        self.assertEqual(len(appended), 115)


if __name__ == "__main__":
    unittest.main()

