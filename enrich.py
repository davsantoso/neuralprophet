"""Export MASE, residual ACF and evaluated-model components offline."""

import gc
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
import warnings

from cargo_forecast.data import load_bps_data
from cargo_forecast.enrichment import data_sha256, extract_components, supplementary_metrics
from cargo_forecast.modeling import VALIDATION_END, _fit
from cargo_forecast.walkforward import atomic_json


def main():
    if sys.version_info >= (3, 13):
        raise SystemExit("Gunakan Python 3.12.")
    warnings.filterwarnings("ignore", category=FutureWarning)
    import torch
    torch.set_num_threads(1)
    report_path = Path("artifacts/report.json")
    original = report_path.read_bytes()
    report = json.loads(original)
    diagnostics = json.loads(Path("artifacts/diagnostics.json").read_text(encoding="utf-8"))
    data = load_bps_data()
    if diagnostics["source"]["report_sha256"] != hashlib.sha256(original).hexdigest():
        raise ValueError("Diagnostik dan laporan resmi tidak cocok.")
    result = {"schema_version": 1, "kind": "interpretasi_tambahan_model_uji_resmi",
              "source": {"report_sha256": hashlib.sha256(original).hexdigest(), "data_sha256": data_sha256(data)},
              "configuration": {"ar_layers": [], "ar_type": "linear", "n_changepoints": 10,
                                "epochs": 100, "learning_rate": 0.01, "seed": 42,
                                "growth": "linear", "yearly_seasonality": True, "n_forecasts": 1},
              "environment": {"python": sys.version.split()[0], "neuralprophet": version("neuralprophet")},
              "series": supplementary_metrics(data, diagnostics)}
    for target in ("bongkar", "muat"):
        model = _fit(data.loc[data["ds"] <= VALIDATION_END], target, report["series"][target]["selected_n_lags"], minimal=True)
        try:
            result["series"][target]["components"] = extract_components(model, data, target, report["series"][target])
        finally:
            del model
            gc.collect()
        print(f"{target}: MASE dan komponen terverifikasi", flush=True)
    if report_path.read_bytes() != original:
        raise ValueError("Laporan resmi berubah selama analisis.")
    atomic_json(Path("artifacts/enrichment.json"), result)
    print("Tersimpan: artifacts/enrichment.json", flush=True)


if __name__ == "__main__":
    main()
