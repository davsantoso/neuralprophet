"""Baca dan validasi tabel bulanan BPS untuk dua deret kargo."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pandas as pd


AIRPORT = "Soekarno Hatta-Jakarta"
THESIS_CUTOFF = pd.Timestamp("2026-06-01")
START = pd.Timestamp("2017-01-01")
COLUMNS = ("bongkar", "muat")


def validate_monthly(frame: pd.DataFrame, *, expected_start: pd.Timestamp = START) -> pd.DataFrame:
    """Return a sorted copy with exactly one positive observation per month."""
    required = {"ds", *COLUMNS}
    if not required.issubset(frame.columns):
        raise ValueError(f"Kolom wajib: {', '.join(sorted(required))}.")
    clean = frame.loc[:, ["ds", *COLUMNS]].copy()
    clean["ds"] = pd.to_datetime(clean["ds"], errors="raise")
    if clean["ds"].isna().any() or (clean["ds"].dt.day != 1).any():
        raise ValueError("Tanggal harus hari pertama setiap bulan (YYYY-MM-01).")
    for name in COLUMNS:
        clean[name] = pd.to_numeric(clean[name], errors="raise")
        if clean[name].isna().any() or (clean[name] <= 0).any():
            raise ValueError(f"Nilai {name} harus angka positif tanpa kekosongan.")
    clean = clean.sort_values("ds").reset_index(drop=True)
    if clean.empty or clean.loc[0, "ds"] != expected_start:
        raise ValueError(f"Deret harus dimulai pada {expected_start:%Y-%m}.")
    expected = pd.date_range(expected_start, periods=len(clean), freq="MS")
    if not clean["ds"].equals(pd.Series(expected, name="ds")):
        raise ValueError("Tanggal bulanan harus berurutan tanpa duplikasi atau bulan hilang.")
    return clean


def load_bps_data(directory: str | Path = "data", *, through: pd.Timestamp | None = THESIS_CUTOFF) -> pd.DataFrame:
    """Extract the Soekarno Hatta row from each annual BPS CSV."""
    records: list[dict[str, object]] = []
    files = sorted(Path(directory).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"Tidak ada berkas CSV BPS di {directory}.")
    for path in files:
        year_match = re.search(r"(20\d{2})\.csv$", path.name)
        if year_match is None:
            continue
        year = int(year_match.group(1))
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        matches = [row for row in rows if row and row[0].strip() == AIRPORT]
        if len(matches) != 1 or len(matches[0]) < 26:
            raise ValueError(f"Baris {AIRPORT} tidak valid di {path.name}.")
        row = matches[0]
        for month in range(1, 13):
            ds = pd.Timestamp(year, month, 1)
            if through is not None and ds > through:
                continue
            raw_bongkar, raw_muat = row[month].strip(), row[month + 13].strip()
            if raw_bongkar == "-" or raw_muat == "-":
                raise ValueError(f"Data belum tersedia untuk {ds:%Y-%m} di {path.name}.")
            records.append({"ds": ds, "bongkar": raw_bongkar, "muat": raw_muat})
    return validate_monthly(pd.DataFrame(records))


def parse_additional_csv(content: bytes, base: pd.DataFrame) -> pd.DataFrame:
    """Accept new monthly rows in ds,bongkar,muat format and append to base."""
    if len(content) > 1_000_000:
        raise ValueError("CSV tambahan maksimal 1 MB.")
    try:
        extra = pd.read_csv(io.BytesIO(content), dtype={"ds": str})
    except (UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError("Berkas tambahan harus berupa CSV UTF-8.") from exc
    if not {"ds", *COLUMNS}.issubset(extra.columns) or extra.empty:
        raise ValueError("CSV tambahan perlu kolom ds,bongkar,muat dan minimal satu baris.")
    if len(extra) > 24:
        raise ValueError("CSV tambahan maksimal 24 bulan per eksperimen.")
    extra = extra.loc[:, ["ds", *COLUMNS]].copy()
    if not extra["ds"].str.fullmatch(r"\d{4}-\d{2}").all():
        raise ValueError("Kolom ds harus menggunakan format YYYY-MM.")
    extra["ds"] = pd.to_datetime(extra["ds"] + "-01", errors="raise")
    expected_start = base["ds"].max() + pd.offsets.MonthBegin(1)
    if extra["ds"].min() != expected_start:
        raise ValueError(f"Data tambahan harus dimulai dari {expected_start:%Y-%m}.")
    return validate_monthly(pd.concat([base, extra], ignore_index=True))


def to_neuralprophet(frame: pd.DataFrame, target: str) -> pd.DataFrame:
    if target not in COLUMNS:
        raise ValueError(f"Target tidak dikenal: {target}")
    return frame.loc[:, ["ds", target]].rename(columns={target: "y"}).copy()


def descriptive_stats(frame: pd.DataFrame) -> pd.DataFrame:
    """Statistics useful for describing the two observed series."""
    data = validate_monthly(frame)
    rows = []
    for name in COLUMNS:
        values = data[name].astype(float)
        rows.append({
            "Deret": name.capitalize(),
            "Minimum (ton)": float(values.min()),
            "Maksimum (ton)": float(values.max()),
            "Rata-rata (ton)": float(values.mean()),
            "Rata-rata perubahan absolut bulanan (ton)": float(values.diff().abs().dropna().mean()),
            "Rata-rata perubahan absolut bulanan (%)": float(values.pct_change().abs().dropna().mean() * 100),
        })
    return pd.DataFrame(rows)

