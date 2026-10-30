"""Verify BPS dimension mapping and secret-safe API failures."""

import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from cargo_forecast.bps_api import BpsApiError, fetch_bps_cargo, merge_bps_payloads, parse_bps_response, year_requests


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

    def test_month_released_for_some_airports_is_held_back(self):
        payload = sample_payload()
        del payload["datacontent"]["5235120711712"], payload["datacontent"]["5235120811712"]
        result = parse_bps_response(payload, fetched_at="now", source_url="safe")
        self.assertEqual(result["last_month"], "2017-11")
        self.assertEqual(result["partial_months"], ["2017-12"])
        self.assertEqual(len(result["frame"]), 55)

    def test_gap_before_last_common_month_is_still_rejected(self):
        payload = sample_payload()
        del payload["datacontent"]["523512071176"], payload["datacontent"]["523512081176"]
        with self.assertRaisesRegex(BpsApiError, "tidak lengkap"):
            parse_bps_response(payload, fetched_at="now", source_url="safe")

    def test_year_requests_respect_three_year_limit(self):
        self.assertEqual(year_requests(2017, 2026), ["117:119", "120:122", "123:125", "126"])
        self.assertEqual(year_requests(2017, 2019), ["117:119"])

    def test_year_range_responses_are_merged_before_parsing(self):
        first, second = sample_payload(), sample_payload()
        second["tahun"] = [{"val": 118, "label": "2018"}]
        # Key = airport (1) + variable (4) + cargo kind (3) + year (3) + month.
        second["datacontent"] = {f"{key[:8]}118{key[11:]}": value for key, value in first["datacontent"].items()}
        responses = [json.dumps(item).encode("utf-8") for item in (first, second)]
        opened = []

        def fake_urlopen(request, timeout):
            opened.append(request.full_url)
            response = MagicMock()
            response.__enter__.return_value.read.return_value = responses[len(opened) - 1]
            return response

        with patch("cargo_forecast.bps_api.year_requests", return_value=["117", "118"]), \
                patch("cargo_forecast.bps_api.urlopen", side_effect=fake_urlopen):
            result = fetch_bps_cargo("secret1234567890", current_year=2018)
        self.assertEqual([url.split("/th/")[1].split("/")[0] for url in opened], ["117", "118"])
        self.assertEqual(result["last_month"], "2018-12")
        self.assertEqual(len(result["frame"]), 120)
        self.assertEqual(result["year_requests"], ["117", "118"])

    def test_conflicting_year_range_metadata_is_rejected(self):
        second = sample_payload()
        second["vervar"] = second["vervar"][:-1]
        with self.assertRaisesRegex(BpsApiError, "Metadata"):
            merge_bps_payloads([sample_payload(), second])

    def test_key_is_not_in_api_error(self):
        key = "secret1234567890"
        with patch("cargo_forecast.bps_api.urlopen", side_effect=HTTPError(f"https://webapi.bps.go.id/key/{key}", 403, "Forbidden", {}, None)):
            with self.assertRaises(BpsApiError) as raised:
                fetch_bps_cargo(key, current_year=2026)
        self.assertNotIn(key, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
