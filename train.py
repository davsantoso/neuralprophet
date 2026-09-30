"""Jalankan eksperimen skripsi dan simpan hasil yang dipakai aplikasi."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from cargo_forecast.data import load_bps_data
from cargo_forecast.modeling import run_thesis_experiment


def main() -> None:
    if sys.version_info >= (3, 13):
        raise SystemExit("NeuralProphet 0.9.0 memerlukan Python 3.9–3.12; jalankan dengan Python 3.12.")
    report = run_thesis_experiment(load_bps_data())
    output = Path("artifacts/report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Hasil tersimpan: {output}")
    for target, details in report["series"].items():
        print(target, "n_lags=", details["selected_n_lags"], details["test_metrics"], details["next_month"])


if __name__ == "__main__":
    main()

