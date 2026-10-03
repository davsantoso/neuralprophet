"""Black-box checks of visible Streamlit behaviour with controlled BPS/model responses.

The BPS response and training result are fixtures. These tests exercise the user
interface, not network availability or NeuralProphet forecast accuracy.
"""

import os
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from cargo_forecast.bps_api import BpsApiError
from cargo_forecast.data import load_bps_data


AIRPORTS = [
    "Kualanamu-Medan",
    "Soekarno Hatta-Jakarta",
    "Juanda-Surabaya",
    "Hasanudin-Makassar",
    "Ngurah Rai-Bali",
]


def bps_fixture():
    """Provide 115 months per label to test navigation; values are fixture data."""
    base = load_bps_data(through=pd.Timestamp("2026-07-01"))
    parts = [base.assign(bandara=airport) for airport in AIRPORTS]
    return {
        "frame": pd.concat(parts, ignore_index=True),
        "airports": AIRPORTS,
        "fetched_at": "2026-10-01T00:00:00+00:00",
        "last_update": "2026-09-02 08:39:21",
        "source_url": "https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/2351/th/117,126",
        "last_month": "2026-07",
    }


def select(app, label):
    return next(item for item in app.selectbox if item.label == label)


def metric(app, label):
    return next(item for item in app.metric if item.label == label)


class BlackBoxTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def open_app(self, response=None, error=None):
        with patch.dict(os.environ, {"BPS_API_KEY": "test-key"}):
            with patch(
                "cargo_forecast.bps_api.fetch_bps_cargo",
                return_value=response,
                side_effect=error,
            ):
                app = AppTest.from_file("app.py").run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def test_bb01_research_snapshot_is_visible(self):
        app = self.open_app(response=bps_fixture())
        self.assertEqual(metric(app, "Observasi per deret").value, "114")
        self.assertTrue(any("Prediksi Juli 2026" in item.value for item in app.subheader))
        self.assertEqual(
            [tab.label for tab in app.tabs],
            ["Ringkasan", "Data", "Evaluasi model", "Diagnostik penelitian", "Eksperimen"],
        )

    def test_bb02_live_data_and_airport_selection(self):
        app = self.open_app(response=bps_fixture())
        self.assertTrue(any("Data langsung BPS tersedia sampai 2026-07" in item.value for item in app.success))
        self.assertIn("Ngurah Rai-Bali", select(app, "Kategori bandara").options)
        select(app, "Kategori bandara").set_value("Ngurah Rai-Bali").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("Ngurah Rai-Bali" in item.value and "115 bulan" in item.value for item in app.caption))

    def test_bb03_series_and_year_filter_update_visible_table(self):
        app = self.open_app(response=bps_fixture())
        select(app, "Deret yang ditampilkan").set_value("Muat")
        next(item for item in app.slider if item.label == "Rentang tahun").set_value((2025, 2026))
        app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("19 bulan ditampilkan" in item.value for item in app.caption))
        displayed = [item.value for item in app.dataframe]
        self.assertTrue(any("Muat (ton)" in frame.columns and "Bongkar (ton)" not in frame.columns for frame in displayed))

    def test_bb04_official_evaluation_switches_series(self):
        app = self.open_app(response=bps_fixture())
        bongkar = metric(app, "MAE uji").value
        select(app, "Deret evaluasi").set_value("muat").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotEqual(metric(app, "MAE uji").value, bongkar)
        self.assertTrue(any("Lookback terpilih" in item.value for item in app.markdown))

    def test_bb05_diagnostics_switches_series(self):
        app = self.open_app(response=bps_fixture())
        bongkar = metric(app, "Rata-rata galat bertanda").value
        select(app, "Deret diagnostik").set_value("muat").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotEqual(metric(app, "Rata-rata galat bertanda").value, bongkar)

    def test_bb06_api_failure_keeps_archive_and_disables_experiment(self):
        app = self.open_app(error=BpsApiError("API sementara gagal"))
        self.assertEqual(metric(app, "Observasi per deret").value, "114")
        self.assertTrue(any("arsip penelitian" in item.value for item in app.info))
        self.assertTrue(any("Pelatihan dengan data terbaru belum tersedia" in item.value for item in app.warning))
        self.assertFalse(any(item.label == "Latih model dan prediksi satu bulan" for item in app.button))

    def test_bb07_parameter_changes_do_not_start_training(self):
        app = self.open_app(response=bps_fixture())
        with patch("cargo_forecast.modeling.retrain_target_for_next_month") as train:
            select(app, "Kategori bandara untuk eksperimen").set_value("Ngurah Rai-Bali")
            select(app, "Deret untuk eksperimen").set_value("muat")
            select(app, "Riwayat pelatihan").set_value("60 bulan terakhir")
            select(app, "Lookback (bulan)").set_value(3)
            select(app, "Epoch").set_value(25)
            app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(train.call_count, 0)
        self.assertTrue(any("Ngurah Rai-Bali" in item.value and "Muat" in item.value and "60 bulan" in item.value for item in app.caption))

    def test_bb08_training_result_is_shown_and_same_input_is_not_retrained(self):
        app = self.open_app(response=bps_fixture())
        result = {"forecast": {"ds": "2026-08", "prediksi": 1234.0}, "duration_seconds": 0.1}
        with patch("cargo_forecast.modeling.retrain_target_for_next_month", return_value=result) as train:
            next(item for item in app.button if item.label == "Latih model dan prediksi satu bulan").click().run(timeout=30)
            app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(train.call_count, 1)
        self.assertEqual(metric(app, "Prediksi Bongkar · 2026-08").value, "1.234 ton")
        self.assertTrue(next(item for item in app.button if item.label == "Latih model dan prediksi satu bulan").disabled)

    def test_bb09_changed_input_hides_previous_prediction(self):
        app = self.open_app(response=bps_fixture())
        result = {"forecast": {"ds": "2026-08", "prediksi": 1234.0}, "duration_seconds": 0.1}
        with patch("cargo_forecast.modeling.retrain_target_for_next_month", return_value=result):
            next(item for item in app.button if item.label == "Latih model dan prediksi satu bulan").click().run(timeout=30)
        self.assertEqual(metric(app, "Prediksi Bongkar · 2026-08").value, "1.234 ton")
        select(app, "Kategori bandara untuk eksperimen").set_value("Ngurah Rai-Bali").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(any(item.label == "Prediksi Bongkar · 2026-08" for item in app.metric))

    def test_bb10_training_failure_shows_safe_message(self):
        app = self.open_app(response=bps_fixture())
        with patch("cargo_forecast.modeling.retrain_target_for_next_month", side_effect=RuntimeError("private detail")):
            next(item for item in app.button if item.label == "Latih model dan prediksi satu bulan").click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(any("Pelatihan eksperimen gagal" in item.value for item in app.error))
        self.assertFalse(any("private detail" in item.value for item in app.error))

    def test_bb16_additional_metrics_and_components_switch_series(self):
        app = self.open_app(response=bps_fixture())
        first = metric(app, "MASE NeuralProphet").value
        select(app, "Deret diagnostik").set_value("muat").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotEqual(metric(app, "MASE NeuralProphet").value, first)
        self.assertTrue(any("Komponen tren, musiman, dan AR linear" == item.label for item in app.expander))
        self.assertTrue(any("Lag dengan bobot absolut terbesar" in item.value for item in app.caption))

    def test_bb17_walk_forward_is_precomputed_and_visible(self):
        with patch("cargo_forecast.modeling._fit", side_effect=AssertionError("UI must not fit")):
            app = self.open_app(response=bps_fixture())
        self.assertTrue(any("Walk-forward 42 bulan" in item.label for item in app.expander))
        self.assertTrue(any("Frekuensi lag terpilih" in item.value for item in app.caption))

    def test_bb18_missing_extra_artifacts_keeps_official_results_visible(self):
        original = Path.exists
        def exists(path):
            return False if path.name in ("enrichment.json", "walk_forward.json") else original(path)
        with patch("pathlib.Path.exists", exists):
            app = self.open_app(response=bps_fixture())
        self.assertEqual(metric(app, "Observasi per deret").value, "114")
        self.assertTrue(any("MASE dan interpretasi komponen belum tersedia" in item.value for item in app.info))

    def test_bb19_mismatched_analysis_is_rejected_and_official_results_remain(self):
        original = Path.read_text
        def read_text(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path.name == "enrichment.json":
                item = json.loads(value)
                item["source"]["report_sha256"] = "mismatched"
                return json.dumps(item)
            return value
        with patch("pathlib.Path.read_text", read_text):
            app = self.open_app(response=bps_fixture())
        self.assertEqual(metric(app, "Observasi per deret").value, "114")
        self.assertTrue(any("Analisis tambahan tidak cocok" in item.value for item in app.error))


if __name__ == "__main__":
    unittest.main()
