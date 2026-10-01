"""Verify BPS dimension mapping and secret-safe API failures."""

import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from cargo_forecast.bps_api import BpsApiError, fetch_bps_cargo, parse_bps_response


def sample_payload():
    airports = [
        {"val": 1, "label": "Kualanamu-Medan"},
        {"val": 2, "label": "Soekarno Hatta-Jakarta"},
        {"val": 3, "label": "Juanda-Surabaya"},
        {"val": 4, "label": "Hasanudin-Makassar"},
        {"val": 5, "label": "Ngurah Rai-Bali"},
        {"val": 6, "label": "Bandara Lainnya"},
        {"val": 7, "label": "TOTAL"},
    ]
    content = {}
    for airport_id in range(1, 6):
        for month in range(1, 13):
            content[f"{airport_id}2351207117{month}"] = airport_id * 100 + month
            content[f"{airport_id}2351208117{month}"] = airport_id * 200 + month
    return {
        "status": "OK",
        "last_update": "2026-09-02 08:39:21",
        "var": [{"val": 2351, "label": "Bongkar/Muat Barang Angkutan Udara Dalam Negeri di 5 Bandara Utama", "unit": "Ton"}],
        "turvar": [{"val": 207, "label": "Barang yang Dibongkar"}, {"val": 208, "label": "Barang yang dimuat"}],
        "vervar": airports,
        "tahun": [{"val": 117, "label": "2017"}],
        "turtahun": [{"val": month, "label": str(month)} for month in range(1, 13)] + [{"val": 13, "label": "Tahunan"}],
        "datacontent": content,
    }


class BpsApiTests(unittest.TestCase):
    def test_parser_maps_airports_targets_and_months(self):
        result = parse_bps_response(sample_payload(), fetched_at="2026-10-01T00:00:00+00:00", source_url="https://webapi.bps.go.id/test")
        self.assertEqual(len(result["frame"]), 60)
        self.assertEqual(result["last_month"], "2017-12")
        self.assertIn("Ngurah Rai-Bali", result["airports"])
        bali = result["frame"].loc[result["frame"]["bandara"] == "Ngurah Rai-Bali"]
        self.assertEqual((bali.iloc[-1]["bongkar"], bali.iloc[-1]["muat"]), (512, 1012))
        self.assertNotIn("TOTAL", result["airports"])

    def test_parser_rejects_missing_month_or_target(self):
        payload = sample_payload()
        del payload["datacontent"]["5235120811712"]
        with self.assertRaisesRegex(BpsApiError, "pasangan|lengkap"):
            parse_bps_response(payload, fetched_at="now", source_url="safe")

    def test_key_is_not_in_api_error(self):
        key = "secret1234567890"
        with patch("cargo_forecast.bps_api.urlopen", side_effect=HTTPError(f"https://webapi.bps.go.id/key/{key}", 403, "Forbidden", {}, None)):
            with self.assertRaises(BpsApiError) as raised:
                fetch_bps_cargo(key, current_year=2026)
        self.assertNotIn(key, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
