"""Ambil dan validasi data bulanan kargo domestik dari Web API BPS."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from .data import validate_monthly


BASE_URL = "https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/2351"
START_YEAR = 2017
EXPECTED_VARIABLE = 2351
MAX_RESPONSE_BYTES = 2_000_000


class BpsApiError(ValueError):
    """Kesalahan yang aman ditampilkan tanpa membocorkan key API."""


def _dimension(items: object, label: str) -> dict[int, str]:
    if not isinstance(items, list) or not items:
        raise BpsApiError(f"Dimensi {label} pada respons BPS tidak tersedia.")
    try:
        result = {int(item["val"]): str(item["label"]).strip() for item in items}
    except (KeyError, TypeError, ValueError) as exc:
        raise BpsApiError(f"Dimensi {label} pada respons BPS tidak valid.") from exc
    if len(result) != len(items) or any(not value for value in result.values()):
        raise BpsApiError(f"Dimensi {label} pada respons BPS tidak valid.")
    return result


def parse_bps_response(payload: object, *, fetched_at: str, source_url: str) -> dict:
    """Normalize metadata and datacontent; key IDs are joined in BPS dimension order."""
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise BpsApiError("BPS tidak mengembalikan data yang tersedia.")
    variables = _dimension(payload.get("var"), "variabel")
    if list(variables) != [EXPECTED_VARIABLE] or "angkutan udara" not in variables[EXPECTED_VARIABLE].lower():
        raise BpsApiError("Variabel respons BPS bukan kargo udara domestik yang diharapkan.")
    var_meta = payload["var"][0]
    if str(var_meta.get("unit", "")).strip().lower() != "ton":
        raise BpsApiError("Satuan respons BPS bukan ton.")

    kinds = _dimension(payload.get("turvar"), "jenis kargo")
    bongkar_ids = [code for code, label in kinds.items() if "dibongkar" in label.lower()]
    muat_ids = [code for code, label in kinds.items() if "dimuat" in label.lower()]
    if len(bongkar_ids) != 1 or len(muat_ids) != 1:
        raise BpsApiError("Label bongkar dan muat pada respons BPS tidak dikenali.")
    target_ids = {"bongkar": bongkar_ids[0], "muat": muat_ids[0]}

    airports_all = _dimension(payload.get("vervar"), "bandara")
    airports = {
        code: label for code, label in airports_all.items()
        if label.casefold() != "total" and "lainnya" not in label.casefold()
    }
    if len(airports) != 5:
        raise BpsApiError("Respons BPS tidak memuat lima kategori bandara utama.")
    years = _dimension(payload.get("tahun"), "tahun")
    months = _dimension(payload.get("turtahun"), "bulan")
    month_ids = {code: code for code, label in months.items() if 1 <= code <= 12}
    if len(month_ids) != 12:
        raise BpsApiError("Respons BPS tidak memuat 12 label bulan.")
    content = payload.get("datacontent")
    if not isinstance(content, dict) or not content:
        raise BpsApiError("Nilai bulanan pada respons BPS kosong.")

    records = []
    for year_id, year_label in years.items():
        try:
            year = int(year_label)
        except ValueError as exc:
            raise BpsApiError("Label tahun pada respons BPS tidak valid.") from exc
        if year < START_YEAR or year > datetime.now(timezone.utc).year + 1:
            raise BpsApiError("Tahun pada respons BPS di luar rentang yang diharapkan.")
        for month_id in month_ids:
            for airport_id, airport in airports.items():
                values = {}
                for target, target_id in target_ids.items():
                    item_key = f"{airport_id}{EXPECTED_VARIABLE}{target_id}{year_id}{month_id}"
                    raw = content.get(item_key)
                    if raw is None:
                        continue
                    try:
                        value = float(raw)
                    except (TypeError, ValueError) as exc:
                        raise BpsApiError("Nilai kargo pada respons BPS bukan angka.") from exc
                    if not math.isfinite(value) or value <= 0:
                        raise BpsApiError("Nilai kargo pada respons BPS harus positif.")
                    values[target] = value
                if values:
                    if len(values) != 2:
                        raise BpsApiError("Pasangan bongkar dan muat pada respons BPS tidak lengkap.")
                    records.append({"ds": pd.Timestamp(year, month_id, 1), "bandara": airport, **values})

    if not records:
        raise BpsApiError("Tidak ada nilai bulanan lima bandara pada respons BPS.")
    frame = pd.DataFrame(records).sort_values(["bandara", "ds"]).reset_index(drop=True)
    if frame.duplicated(["bandara", "ds"]).any():
        raise BpsApiError("Respons BPS memuat bulan bandara duplikat.")
    latest = frame["ds"].max()
    expected_months = pd.date_range(pd.Timestamp(START_YEAR, 1, 1), latest, freq="MS")
    for airport in airports.values():
        subset = frame.loc[frame["bandara"] == airport, ["ds", "bongkar", "muat"]]
        if len(subset) != len(expected_months):
            raise BpsApiError(f"Deret bulanan {airport} pada respons BPS tidak lengkap.")
        try:
            validate_monthly(subset)
        except ValueError as exc:
            raise BpsApiError(f"Deret bulanan {airport} pada respons BPS tidak valid.") from exc

    return {
        "frame": frame,
        "airports": list(airports.values()),
        "fetched_at": fetched_at,
        "last_update": str(payload.get("last_update", "")),
        "source_url": source_url,
        "last_month": latest.strftime("%Y-%m"),
    }


def fetch_bps_cargo(api_key: str, *, current_year: int | None = None) -> dict:
    """One multi-year request; never include the secret-bearing URL in errors."""
    if not api_key or not api_key.isalnum():
        raise BpsApiError("BPS_API_KEY belum dikonfigurasi dengan benar.")
    year = current_year or datetime.now(timezone.utc).year
    if year < START_YEAR or year > 2100:
        raise BpsApiError("Tahun permintaan BPS tidak valid.")
    year_ids = f"{START_YEAR - 1900},{year - 1900}"
    public_url = f"{BASE_URL}/th/{year_ids}"
    request = Request(f"{public_url}/key/{api_key}", headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise BpsApiError("Respons BPS terlalu besar.")
            payload = json.loads(raw)
            return parse_bps_response(
                payload,
                fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                source_url=public_url,
            )
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise BpsApiError("Akses API BPS ditolak. Periksa key dan izin aksesnya.") from None
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise BpsApiError(f"Permintaan API BPS gagal (HTTP {exc.code}).") from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise BpsApiError("API BPS tidak dapat dihubungi saat ini.") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise BpsApiError("Respons API BPS bukan JSON yang valid.") from None
        time.sleep(0.5 * (attempt + 1))
    raise BpsApiError("API BPS tidak dapat dihubungi saat ini.")
