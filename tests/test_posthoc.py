"""Memeriksa koreksi Holm dan rata-rata lima seed terhadap artefak yang dibekukan."""

import hashlib
import json
from pathlib import Path
import unittest

from cargo_forecast.posthoc import build_holm, build_seed_ensemble, holm_adjust
try:  # discover -s tests (CI) vs python -m unittest tests.test_posthoc
    import test_significance
except ModuleNotFoundError:
    from tests import test_significance


class PosthocTests(unittest.TestCase):
    assert_close = test_significance.SignificanceTests.assert_close

    def test_holm_matches_textbook_example(self):
        self.assertEqual([round(p, 4) for p in holm_adjust([0.01, 0.04, 0.03, 0.005])], [0.03, 0.06, 0.06, 0.02])
        self.assertEqual(holm_adjust([0.9, 0.8]), [1.0, 1.0])

    def test_artifact_matches_recomputation(self):
        significance = json.loads(Path("artifacts/significance.json").read_text(encoding="utf-8"))
        diagnostics = json.loads(Path("artifacts/diagnostics.json").read_text(encoding="utf-8"))
        stored = json.loads(Path("artifacts/posthoc.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["source"]["significance_sha256"],
                         hashlib.sha256(Path("artifacts/significance.json").read_bytes()).hexdigest())
        self.assert_close(stored["holm"]["uji"], build_holm(significance))
        self.assertEqual(len(stored["holm"]["uji"]), 16)
        self.assert_close(stored["rata_rata_lima_seed"], json.loads(json.dumps(build_seed_ensemble(diagnostics))))

    def test_numbers_reported_in_thesis(self):
        stored = json.loads(Path("artifacts/posthoc.json").read_text(encoding="utf-8"))
        holm = {(r["deret"], r["protokol"], r["pembanding"], r["loss"]): r for r in stored["holm"]["uji"]}
        self.assertAlmostEqual(holm[("muat", "test_18", "same_month_last_year", "absolute")]["p_holm"], 0.126, places=3)
        self.assertAlmostEqual(holm[("bongkar", "walk_forward_42", "same_month_last_year", "absolute")]["p_holm"], 0.057, places=3)
        significant = [key for key, row in holm.items() if row["signifikan_setelah_holm"]]
        self.assertTrue(all(key[0] == "muat" and key[1] == "walk_forward_42" for key in significant))
        ens = stored["rata_rata_lima_seed"]
        self.assertAlmostEqual(ens["bongkar"]["metrics"]["MAE"], 1085.42, places=2)
        self.assertAlmostEqual(ens["muat"]["metrics"]["MAE"], 1188.98, places=2)
        self.assertAlmostEqual(ens["bongkar"]["dm_absolut_vs_pembanding_terbaik"]["p_value"], 0.940, places=3)
        self.assertAlmostEqual(ens["muat"]["dm_absolut_vs_pembanding_terbaik"]["p_value"], 0.882, places=3)


if __name__ == "__main__":
    unittest.main()
