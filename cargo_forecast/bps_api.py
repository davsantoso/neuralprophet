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
# Since October 2026 the API rejects more than three years per request and
# requires ":" for a range instead of ",".
MAX_YEARS_PER_REQUEST = 3
SHARED_DIMENSIONS = ("var", "turvar", "vervar", "turtahun")


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
    latest_by_airport = frame.groupby("bandara")["ds"].max()
    if set(latest_by_airport.index) != set(airports.values()):
        raise BpsApiError("Respons BPS tidak memuat nilai untuk kelima bandara.")
    # A month released for only some airports is held back so that every
    # airport shares the same last month; gaps before it are still rejected.
    latest = latest_by_airport.min()
    partial_months = sorted(frame.loc[frame["ds"] > latest, "ds"].dt.strftime("%Y-%m").unique())
    frame = frame.loc[frame["ds"] <= latest].reset_index(drop=True)
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
        "partial_months": partial_months,
    }


def year_requests(first_year: int, last_year: int) -> list[str]:
    """BPS year IDs (year − 1900), at most three years per request."""
    specs = []
    for start in range(first_year, last_year + 1, MAX_YEARS_PER_REQUEST):
        end = min(start + MAX_YEARS_PER_REQUEST - 1, last_year)
        specs.append(str(start - 1900) if start == end else f"{start - 1900}:{end - 1900}")
    return specs


def merge_bps_payloads(payloads: list[object]) -> dict:
    """Join per-year-range responses that must share the same dimensions."""
    if not payloads:
        raise BpsApiError("BPS tidak mengembalikan data yang tersedia.")
    first = payloads[0]
    contents: dict = {}
    years: dict[str, object] = {}
    for payload in payloads:
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            raise BpsApiError("BPS tidak mengembalikan data yang tersedia.")
        if any(payload.get(name) != first.get(name) for name in SHARED_DIMENSIONS):
            raise BpsApiError("Metadata respons BPS berbeda antarpermintaan tahun.")
        content = payload.get("datacontent") or {}
        tahun = payload.get("tahun") or []
        if not isinstance(content, dict) or not isinstance(tahun, list):
            raise BpsApiError("Nilai bulanan pada respons BPS tidak valid.")
        for key, value in content.items():
            if key in contents and contents[key] != value:
                raise BpsApiError("Respons BPS memuat nilai berbeda untuk bulan yang sama.")
            contents[key] = value
        for item in tahun:
            years.setdefault(json.dumps(item, sort_keys=True), item)
    return {**first, "tahun": list(years.values()), "datacontent": contents,
            "last_update": max(str(payload.get("last_update", "")) for payload in payloads)}


def _request_payload(public_url: str, api_key: str) -> object:
    request = Request(f"{public_url}/key/{api_key}", headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise BpsApiError("Respons BPS terlalu besar.")
            return json.loads(raw)
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


def fetch_bps_cargo(api_key: str, *, current_year: int | None = None) -> dict:
    """Request each year range; never include the secret-bearing URL in errors."""
    if not api_key or not api_key.isalnum():
        raise BpsApiError("BPS_API_KEY belum dikonfigurasi dengan benar.")
    year = current_year or datetime.now(timezone.utc).year
    if year < START_YEAR or year > 2100:
        raise BpsApiError("Tahun permintaan BPS tidak valid.")
    specs = year_requests(START_YEAR, year)
    payloads = [_request_payload(f"{BASE_URL}/th/{spec}", api_key) for spec in specs]
    result = parse_bps_response(
        merge_bps_payloads(payloads),
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_url=BASE_URL,
    )
    result["year_requests"] = specs
    return result
