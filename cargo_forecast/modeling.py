"""Eksperimen kronologis satu langkah ke depan untuk dua deret independen."""

from __future__ import annotations

import math
import os
import gc
import logging
from pathlib import Path
import time
from typing import Any

import pandas as pd

from .data import COLUMNS, THESIS_CUTOFF, to_neuralprophet, validate_monthly


TRAIN_END = pd.Timestamp("2023-12-01")
VALIDATION_END = pd.Timestamp("2024-12-01")
LAG_CANDIDATES = (3, 6, 12)
SEED = 42
EPOCHS = 100
LEARNING_RATE = 0.01


def _fit(frame: pd.DataFrame, target: str, n_lags: int):
    matplotlib_cache = Path(__file__).resolve().parents[1] / ".mpl-cache"
    matplotlib_cache.mkdir(exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    from neuralprophet import NeuralProphet, set_log_level, set_random_seed

    set_log_level("ERROR")
    set_random_seed(SEED)
    model = NeuralProphet(
        n_lags=n_lags,
        n_forecasts=1,
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        n_changepoints=10,
        epochs=EPOCHS,
        learning_rate=LEARNING_RATE,
    )
    model.fit(to_neuralprophet(frame, target), freq="MS", progress=None)
    return model


def _predict_range(model: Any, frame: pd.DataFrame, target: str, start: pd.Timestamp) -> pd.DataFrame:
    """yhat1 at month t uses actual values only through month t-1."""
    forecast = model.predict(to_neuralprophet(frame, target))
    selected = forecast.loc[forecast["ds"] >= start, ["ds", "y", "yhat1"]].copy()
    if selected.empty or selected[["y", "yhat1"]].isna().any().any():
        raise ValueError(f"Prediksi {target} tidak lengkap sejak {start:%Y-%m}.")
    selected = selected.rename(columns={"y": "aktual", "yhat1": "prediksi"})
    return selected.reset_index(drop=True)


def _metrics(predictions: pd.DataFrame) -> dict[str, float]:
    actual = predictions["aktual"].astype(float)
    error = predictions["prediksi"].astype(float) - actual
    return {
        "MAE": float(error.abs().mean()),
        "RMSE": float(math.sqrt((error**2).mean())),
        "MAPE": float((error.abs() / actual).mean() * 100),
    }


def _records(predictions: pd.DataFrame) -> list[dict[str, float | str]]:
    return [
        {"ds": row.ds.strftime("%Y-%m"), "aktual": float(row.aktual), "prediksi": float(row.prediksi)}
        for row in predictions.itertuples(index=False)
    ]


def _forecast_next(model: Any, frame: pd.DataFrame, target: str) -> dict[str, float | str]:
    future = model.make_future_dataframe(to_neuralprophet(frame, target), periods=1)
    forecast = model.predict(future).iloc[-1]
    value = float(forecast["yhat1"])
    if not math.isfinite(value):
        raise ValueError(f"Prediksi masa depan {target} tidak valid.")
    return {"ds": forecast["ds"].strftime("%Y-%m"), "prediksi": value}


def run_thesis_experiment(frame: pd.DataFrame) -> dict[str, Any]:
    """Select lags on 2024, evaluate once on Jan 2025–Jun 2026."""
    data = validate_monthly(frame)
    if len(data) != 114 or data["ds"].max() != THESIS_CUTOFF:
        raise ValueError("Eksperimen skripsi harus memakai 114 bulan sampai Juni 2026.")
    train = data.loc[data["ds"] <= TRAIN_END].copy()
    through_validation = data.loc[data["ds"] <= VALIDATION_END].copy()
    if (len(train), len(through_validation) - len(train), len(data) - len(through_validation)) != (84, 12, 18):
        raise ValueError("Pembagian kronologis tidak sesuai 84/12/18 bulan.")

    result: dict[str, Any] = {
        "source": "BPS, Bongkar/Muat Barang Angkutan Udara Dalam Negeri di 5 Bandara Utama; Soekarno Hatta-Jakarta",
        "cutoff": "2026-06",
        "split": {"train": "2017-01..2023-12", "validation": "2024-01..2024-12", "test": "2025-01..2026-06"},
        "n_observations": 114,
        "horizon_months": 1,
        "lag_candidates": list(LAG_CANDIDATES),
        "seed": SEED,
        "epochs": EPOCHS,
        "learning_rate": LEARNING_RATE,
        "selection_metric": "MAE",
        "series": {},
    }

    for target in COLUMNS:
        candidates: list[dict[str, Any]] = []
        for n_lags in LAG_CANDIDATES:
            model = _fit(train, target, n_lags)
            validation = _predict_range(model, through_validation, target, train["ds"].max() + pd.offsets.MonthBegin(1))
            candidates.append({"n_lags": n_lags, "metrics": _metrics(validation)})
            del model
        chosen = min(candidates, key=lambda item: (item["metrics"]["MAE"], item["n_lags"]))

        test_model = _fit(through_validation, target, chosen["n_lags"])
        test = _predict_range(test_model, data, target, VALIDATION_END + pd.offsets.MonthBegin(1))
        del test_model

        final_model = _fit(data, target, chosen["n_lags"])
        next_month = _forecast_next(final_model, data, target)
        del final_model

        result["series"][target] = {
            "validation_candidates": candidates,
            "selected_n_lags": chosen["n_lags"],
            "test_metrics": _metrics(test),
            "test_predictions": _records(test),
            "next_month": next_month,
        }
    return result


def retrain_for_next_month(frame: pd.DataFrame, lags: dict[str, int]) -> dict[str, Any]:
    """Fit on all available rows for an exploratory next-month forecast."""
    data = validate_monthly(frame)
    if data["ds"].max() < THESIS_CUTOFF:
        raise ValueError("Data eksperimen tidak boleh berakhir sebelum Juni 2026.")
    forecasts = {}
    for target in COLUMNS:
        forecasts[target] = retrain_target_for_next_month(data, target, lags[target])["forecast"]
    return {"last_observation": data["ds"].max().strftime("%Y-%m"), "n_observations": len(data), "forecasts": forecasts}


def retrain_target_for_next_month(frame: pd.DataFrame, target: str, n_lags: int) -> dict[str, Any]:
    """Fit one independent series, keeping cloud CPU use bounded per request."""
    data = validate_monthly(frame)
    if data["ds"].max() < THESIS_CUTOFF:
        raise ValueError("Data eksperimen tidak boleh berakhir sebelum Juni 2026.")
    if target not in COLUMNS:
        raise ValueError(f"Target tidak dikenal: {target}")
    if n_lags <= 0:
        raise ValueError("Lookback harus positif.")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    import torch

    torch.set_num_threads(1)
    started = time.perf_counter()
    model = _fit(data, target, n_lags)
    try:
        forecast = _forecast_next(model, data, target)
    finally:
        del model
        gc.collect()
    duration = time.perf_counter() - started
    logging.getLogger(__name__).info("Pelatihan eksperimen %s: %.1f detik, %s bulan, %s epoch", target, duration, len(data), EPOCHS)
    return {"target": target, "last_observation": data["ds"].max().strftime("%Y-%m"), "n_observations": len(data), "forecast": forecast, "duration_seconds": duration}

