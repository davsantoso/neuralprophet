"""Nested, historical one-step backtest; all fitting uses earlier observations."""

from __future__ import annotations

import gc
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
from pathlib import Path
from typing import Callable

import pandas as pd

from .data import COLUMNS
from .enrichment import data_sha256, research_frame
from .modeling import EPOCHS, LAG_CANDIDATES, LEARNING_RATE, SEED, _fit, _forecast_next, _metrics, _predict_range


TARGET_DATES = pd.date_range("2023-01-01", "2026-06-01", freq="MS")
PROTOCOL = {"start": "2023-01", "end": "2026-06", "months": 42,
            "inner_validation_months": 12, "minimum_inner_train_months": 60,
            "lag_candidates": list(LAG_CANDIDATES), "selection_metric": "MAE",
            "seed": SEED, "epochs": EPOCHS, "learning_rate": LEARNING_RATE,
            "ar_layers": [], "n_changepoints": 10, "n_forecasts": 1,
            "yearly_seasonality": True, "weekly_seasonality": False, "daily_seasonality": False}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def validate_row(row: dict, data: pd.DataFrame, target: str, month: pd.Timestamp) -> None:
    origin = month - pd.DateOffset(months=1)
    validation_start = origin - pd.DateOffset(months=11)
    if (row["ds"] != month.strftime("%Y-%m") or row["origin"] != origin.strftime("%Y-%m")
            or row["inner_validation_start"] != validation_start.strftime("%Y-%m")
            or row["inner_train_end"] != (validation_start - pd.DateOffset(months=1)).strftime("%Y-%m")
            or row["inner_validation_end"] != row["origin"]):
        raise ValueError("Batas waktu checkpoint walk-forward tidak benar.")
    candidates = row["validation_candidates"]
    if [r["n_lags"] for r in candidates] != list(LAG_CANDIDATES):
        raise ValueError("Kandidat checkpoint tidak lengkap.")
    chosen = min(candidates, key=lambda r: (r["metrics"]["MAE"], r["n_lags"]))
    train_count = len(data.loc[data["ds"] < validation_start])
    if (row["inner_train_start"] != "2017-01" or row["inner_train_months"] != train_count
            or row["inner_validation_months"] != 12 or row["refit_months"] != train_count + 12):
        raise ValueError("Jumlah bulan checkpoint tidak cocok dengan batas waktunya.")
    if any(not math.isfinite(value) or value < 0 for item in candidates for value in item["metrics"].values()):
        raise ValueError("Metrik validasi checkpoint tidak valid.")
    if row["selected_n_lags"] != chosen["n_lags"]:
        raise ValueError("Pilihan lag checkpoint bukan MAE validasi minimum.")
    indexed = data.set_index("ds")
    if row["actual"] != float(indexed.loc[month, target]) or row["last_month"] != float(indexed.loc[origin, target]):
        raise ValueError("Aktual atau baseline checkpoint tidak cocok dengan snapshot.")
    if not all(math.isfinite(row[name]) for name in ("actual", "neuralprophet", "last_month")):
        raise ValueError("Prediksi walk-forward harus berhingga.")


def _evaluate_origin(data: pd.DataFrame, target: str, month: pd.Timestamp) -> dict:
    origin = month - pd.DateOffset(months=1)
    validation_start = origin - pd.DateOffset(months=11)
    available = data.loc[data["ds"] <= origin].copy()
    inner_train = available.loc[available["ds"] < validation_start].copy()
    if len(inner_train) < 60:
        raise ValueError("Train dalam harus memiliki minimal 60 bulan.")
    candidates = []
    for lag in LAG_CANDIDATES:
        model = _fit(inner_train, target, lag, minimal=True)
        try:
            validation = _predict_range(model, available, target, validation_start)
            if len(validation) != 12:
                raise ValueError("Validasi dalam harus tepat 12 bulan.")
            candidates.append({"n_lags": lag, "metrics": _metrics(validation)})
        finally:
            del model
            gc.collect()
    chosen = min(candidates, key=lambda r: (r["metrics"]["MAE"], r["n_lags"]))
    model = _fit(available, target, chosen["n_lags"], minimal=True)
    try:
        forecast = _forecast_next(model, available, target)
    finally:
        del model
        gc.collect()
    if forecast["ds"] != month.strftime("%Y-%m"):
        raise ValueError("Bulan prediksi walk-forward salah.")
    return {"ds": forecast["ds"], "origin": origin.strftime("%Y-%m"),
            "inner_train_start": "2017-01", "inner_train_end": inner_train["ds"].max().strftime("%Y-%m"),
            "inner_train_months": len(inner_train), "inner_validation_start": validation_start.strftime("%Y-%m"),
            "inner_validation_end": origin.strftime("%Y-%m"), "inner_validation_months": 12,
            "refit_months": len(available), "selected_n_lags": chosen["n_lags"],
            "validation_candidates": candidates, "neuralprophet": forecast["prediksi"],
            "actual": float(data.loc[data["ds"] == month, target].iloc[0]),
            "last_month": float(available[target].iloc[-1])}


def _worker_init():
    import os
    import sys
    import warnings
    warnings.filterwarnings("ignore")
    Path(".tmp").mkdir(exist_ok=True)
    sys.stderr = open(Path(".tmp") / f"walk_forward_worker_{os.getpid()}.log", "a", encoding="utf-8")
    import torch
    torch.set_num_threads(1)


def walk_forward(frame: pd.DataFrame, *, report_sha256: str, checkpoint: Path | None = None,
                 progress: Callable[[str], None] | None = None, workers: int = 1) -> dict:
    data = research_frame(frame)
    source = {"data_sha256": data_sha256(data), "report_sha256": report_sha256}
    state = {"source": source, "protocol": PROTOCOL, "rows": {}}
    if checkpoint is not None and checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        if state["source"] != source or state["protocol"] != PROTOCOL:
            raise ValueError("Checkpoint berbeda data, laporan, atau protokol. Gunakan berkas checkpoint baru.")
    output = {"schema_version": 1, "kind": "backtest_tambahan_bukan_pengganti_uji_resmi",
              "source": source, "protocol": PROTOCOL, "series": {}}
    jobs = [(target, month) for target in COLUMNS for month in TARGET_DATES]
    for target, month in jobs:
        key = f"{target}:{month:%Y-%m}"
        if key in state["rows"]:
            validate_row(state["rows"][key], data, target, month)
    missing = [(target, month) for target, month in jobs if f"{target}:{month:%Y-%m}" not in state["rows"]]
    def save(target, month, row):
        validate_row(row, data, target, month)
        state["rows"][f"{target}:{month:%Y-%m}"] = row
        if checkpoint is not None:
            atomic_json(checkpoint, state)
        if progress:
            progress(f"{target} {month:%Y-%m}: {len(state['rows'])}/84 selesai; lag {row['selected_n_lags']}")
    if workers == 1 or (not missing and workers in (2, 3, 4)):
        for target, month in missing:
            save(target, month, _evaluate_origin(data, target, month))
    elif workers in (2, 3, 4):
        with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as pool:
            futures = {pool.submit(_evaluate_origin, data, target, month): (target, month) for target, month in missing}
            for future in as_completed(futures):
                target, month = futures[future]
                save(target, month, future.result())
    else:
        raise ValueError("Jumlah worker lokal harus antara 1 dan 4.")
    for target in COLUMNS:
        rows = []
        for month in TARGET_DATES:
            row = state["rows"][f"{target}:{month:%Y-%m}"]
            validate_row(row, data, target, month)
            rows.append(row)
        metrics = {}
        for label, subset in (("all_42", rows), ("2023_2024", rows[:24]), ("2025_2026", rows[24:])):
            metrics[label] = {method: _metrics(pd.DataFrame({"aktual": [r["actual"] for r in subset],
                                                           "prediksi": [r[method] for r in subset]}))
                              for method in ("neuralprophet", "last_month")}
        output["series"][target] = {"monthly": rows, "metrics": metrics,
                                     "lag_counts": {str(lag): sum(r["selected_n_lags"] == lag for r in rows)
                                                    for lag in LAG_CANDIDATES}}
    return output
