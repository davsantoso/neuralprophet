"""Buat atau verifikasi sidik jari data, laporan, dan lingkungan penelitian."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import pandas as pd

from cargo_forecast.data import load_bps_data


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPORT_PATH = ROOT / "artifacts" / "report.json"
MANIFEST_PATH = ROOT / "artifacts" / "provenance.json"
BPS_URL = "https://www.bps.go.id/id/statistics-table/2/MjM1MSMy/bongkar-muat-barang-angkutan-udara-dalam-negeri-di-5-bandara-utama.html"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def build_manifest() -> dict:
    files = sorted(DATA_DIR.glob("*.csv"))
    if len(files) != 10:
        raise ValueError("Jejak penelitian memerlukan tepat 10 CSV tahunan BPS (2017–2026).")
    frame = load_bps_data(DATA_DIR)
    if len(frame) != 114 or frame["ds"].max() != pd.Timestamp("2026-06-01"):
        raise ValueError("Dataset penelitian harus berakhir pada Juni 2026 dengan 114 bulan.")
    july = load_bps_data(DATA_DIR, through=pd.Timestamp("2026-07-01"))
    if len(july) != 115:
        raise ValueError("Snapshot CSV 2026 seharusnya memuat Juli sebagai bulan ke-115.")
    report_bytes = REPORT_PATH.read_bytes()
    report = json.loads(report_bytes)
    if report["n_observations"] != 114 or report["cutoff"] != "2026-06":
        raise ValueError("Cakupan laporan tidak sesuai dataset penelitian.")
    indexed = frame.set_index("ds")
    for target in ("bongkar", "muat"):
        rows = report["series"][target]["test_predictions"]
        if len(rows) != 18:
            raise ValueError(f"Laporan uji {target} harus memiliki 18 bulan.")
        for row in rows:
            if float(indexed.loc[pd.Timestamp(row["ds"] + "-01"), target]) != row["aktual"]:
                raise ValueError(f"Aktual uji {target} tidak cocok dengan snapshot BPS.")
    canonical = frame.assign(ds=frame["ds"].dt.strftime("%Y-%m")).to_csv(index=False, lineterminator="\n")
    packages = {name: version(name) for name in ("neuralprophet", "numpy", "pandas", "torch", "pytorch-lightning", "streamlit")}
    return {
        "schema_version": 1,
        "source": {"publisher": "Badan Pusat Statistik", "url": BPS_URL, "category": "Soekarno Hatta-Jakarta", "unit": "ton per bulan", "retrieval_date": None, "retrieval_date_note": "Tanggal pengunduhan awal tidak tercatat; tidak direkonstruksi dari metadata berkas."},
        "raw_files": [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path.read_bytes())} for path in files],
        "research_dataset": {"first_month": "2017-01", "last_month": "2026-06", "observations_per_series": 114, "columns": ["ds", "bongkar", "muat"], "canonical_csv_sha256": digest(canonical.encode("utf-8")), "excluded_available_month": "2026-07"},
        "experiment": {"train": report["split"]["train"], "validation": report["split"]["validation"], "test": report["split"]["test"], "horizon_months": report["horizon_months"], "lag_candidates": report["lag_candidates"], "selected_lags": {target: report["series"][target]["selected_n_lags"] for target in ("bongkar", "muat")}, "seed": report["seed"], "epochs": report["epochs"], "learning_rate": report["learning_rate"], "selection_metric": report["selection_metric"]},
        "report": {"path": REPORT_PATH.relative_to(ROOT).as_posix(), "sha256": digest(report_bytes)},
        "environment": {"python": platform.python_version(), "packages": packages},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Perbarui manifest setelah eksperimen resmi diulang.")
    args = parser.parse_args()
    actual = build_manifest()
    if args.write:
        MANIFEST_PATH.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Manifest ditulis: {MANIFEST_PATH}")
    else:
        expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if actual != expected:
            raise SystemExit("Manifest tidak cocok. Periksa perubahan data, laporan, atau lingkungan; jangan perbarui tanpa meninjau perubahan.")
        print("Jejak penelitian cocok: 10 CSV, 114 bulan, laporan model, dan versi lingkungan.")


if __name__ == "__main__":
    main()
