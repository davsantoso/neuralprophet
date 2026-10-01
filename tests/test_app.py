"""Exercise live-data choices while keeping model training out of UI tests."""

import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from cargo_forecast.bps_api import BpsApiError
from cargo_forecast.data import load_bps_data


def live_fixture():
    base = load_bps_data(through=pd.Timestamp("2026-07-01"))
    frames = []
    airports = ["Kualanamu-Medan", "Soekarno Hatta-Jakarta", "Juanda-Surabaya", "Hasanudin-Makassar", "Ngurah Rai-Bali"]
    for airport in airports:
        part = base.copy()
        part["bandara"] = airport
        frames.append(part)
    return {
        "frame": pd.concat(frames, ignore_index=True),
        "airports": airports,
        "fetched_at": "2026-10-01T00:00:00+00:00",
        "last_update": "2026-09-02 08:39:21",
        "source_url": "https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/2351/th/117,126",
        "last_month": "2026-07",
    }


class AppWorkflowTests(unittest.TestCase):
    def test_api_failure_keeps_research_visible_and_disables_training(self):
        st.cache_data.clear()
        with patch("cargo_forecast.bps_api.fetch_bps_cargo", side_effect=BpsApiError("API sementara gagal")):
            app = AppTest.from_file("app.py").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "114")
        self.assertTrue(any("arsip penelitian" in item.value for item in app.info))
        self.assertFalse(any(item.label == "Latih model dan prediksi satu bulan" for item in app.button))

    def test_live_data_and_experiment_inputs(self):
        st.cache_data.clear()
        with patch("cargo_forecast.bps_api.fetch_bps_cargo", return_value=live_fixture()):
            app = AppTest.from_file("app.py").run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual([tab.label for tab in app.tabs], ["Ringkasan", "Data", "Evaluasi model", "Eksperimen"])
            self.assertEqual(app.metric[0].value, "114")
            self.assertFalse(app.file_uploader)
            next(item for item in app.selectbox if item.label == "Kategori bandara").set_value("Ngurah Rai-Bali")
            next(item for item in app.selectbox if item.label == "Kategori bandara untuk eksperimen").set_value("Ngurah Rai-Bali")
            next(item for item in app.selectbox if item.label == "Riwayat pelatihan").set_value("60 bulan terakhir")
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertTrue(any("Ngurah Rai-Bali" in item.value and "60 bulan" in item.value for item in app.caption))

            fake_result = {
                "forecast": {"ds": "2026-08", "prediksi": 1234.0},
                "duration_seconds": 0.1,
            }
            with patch("cargo_forecast.modeling.retrain_target_for_next_month", return_value=fake_result) as train:
                next(item for item in app.button if item.label == "Latih model dan prediksi satu bulan").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(train.call_count, 1)
            self.assertTrue(any("Prediksi Bongkar" in item.label and "2026-08" in item.label for item in app.metric))

            next(item for item in app.selectbox if item.label == "Kategori bandara untuk eksperimen").set_value("Juanda-Surabaya").run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(any("Prediksi Bongkar" in item.label and "2026-08" in item.label for item in app.metric))


if __name__ == "__main__":
    unittest.main()
