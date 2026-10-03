"""Supplementary metrics and interpretation of the frozen evaluated models."""

from __future__ import annotations

import hashlib
import math
from statistics import mean
from typing import Any

import pandas as pd

from .data import COLUMNS, THESIS_CUTOFF, to_neuralprophet, validate_monthly
from .modeling import VALIDATION_END


def data_sha256(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.assign(ds=frame["ds"].dt.strftime("%Y-%m"))
                          .to_csv(index=False, lineterminator="\n").encode("utf-8")).hexdigest()


def research_frame(frame: pd.DataFrame) -> pd.DataFrame:
    data = validate_monthly(frame)
    if len(data) != 114 or data["ds"].max() != THESIS_CUTOFF:
        raise ValueError("Analisis tambahan harus memakai 114 bulan sampai Juni 2026.")
    return data


def residual_acf(errors: list[float], max_lag: int = 3) -> list[dict[str, float | int]]:
    """Sample ACF, centred by the mean; descriptive, with no whiteness claim."""
    if len(errors) <= max_lag or not all(math.isfinite(v) for v in errors):
        raise ValueError("Residual tidak lengkap atau tidak berhingga.")
    centre = mean(errors)
    values = [value - centre for value in errors]
    denominator = sum(value * value for value in values)
    return [{"lag": lag, "acf": (sum(values[i] * values[i - lag] for i in range(lag, len(values)))
                                      / denominator if denominator else 0.0)}
            for lag in range(1, max_lag + 1)]


def supplementary_metrics(frame: pd.DataFrame, diagnostics: dict) -> dict[str, Any]:
    data = research_frame(frame)
    if diagnostics["source"]["data_sha256"] != data_sha256(data):
        raise ValueError("Diagnostik tidak cocok dengan snapshot penelitian.")
    train = data.loc[data["ds"] <= VALIDATION_END]
    result = {}
    for target in COLUMNS:
        detail = diagnostics["series"][target]
        if len(detail["monthly"]) != 18:
            raise ValueError("Residual resmi harus berjumlah 18.")
        scale = float(train[target].diff().abs().dropna().mean())
        if scale <= 0 or not math.isfinite(scale):
            raise ValueError("Skala MASE harus positif dan berhingga.")
        result[target] = {
            "mase": {"scale_ton": scale, "scale_start": "2017-01", "scale_end": "2024-12",
                     "training_observations": 96, "training_differences": 95,
                     "methods": {name: float(metrics["MAE"]) / scale
                                 for name, metrics in detail["metrics"].items()}},
            "residual": {"definition": "prediksi dikurangi aktual", "n": 18,
                         "acf": residual_acf([row["error"] for row in detail["monthly"]])},
        }
    return result


def extract_components(model: Any, frame: pd.DataFrame, target: str, official: dict) -> dict:
    """Export components only after verifying the evaluated model's forecasts."""
    forecast = model.predict(to_neuralprophet(frame, target))
    test = forecast.loc[forecast["ds"] > VALIDATION_END]
    if len(test) != 18 or list(test["ds"].dt.strftime("%Y-%m")) != [r["ds"] for r in official["test_predictions"]]:
        raise ValueError("Komponen tidak memiliki 18 tanggal uji yang benar.")
    difference = max(abs(float(value) - row["prediksi"])
                     for value, row in zip(test["yhat1"], official["test_predictions"], strict=True))
    if difference > 1e-5:
        raise ValueError(f"Model interpretasi tidak mereproduksi laporan resmi: {difference} ton.")
    valid = forecast.dropna(subset=["yhat1", "ar1", "trend", "season_yearly"])
    reconstruction = float((valid["trend"] + valid["season_yearly"] + valid["ar1"] - valid["yhat1"]).abs().max())
    if reconstruction > 0.01:
        raise ValueError("Jumlah komponen tidak cocok dengan prediksi dalam toleransi 0,01 ton.")
    # AR needs previous observations, but trend and yearly components do not.
    # Fill their initial n_lags rows through the component-specific public APIs.
    trend_values = model.predict_trend(to_neuralprophet(frame, target)).set_index("ds")["trend"]
    seasonal_values = model.predict_seasonal_components(to_neuralprophet(frame, target)).set_index("ds")["yearly"]
    forecast["trend"] = forecast["trend"].fillna(forecast["ds"].map(trend_values))
    forecast["season_yearly"] = forecast["season_yearly"].fillna(forecast["ds"].map(seasonal_values))
    timeline = []
    for row in forecast.itertuples(index=False):
        timeline.append({"ds": row.ds.strftime("%Y-%m"), "trend": None if pd.isna(row.trend) else float(row.trend),
                         "yearly": None if pd.isna(row.season_yearly) else float(row.season_yearly),
                         "ar": None if pd.isna(row.ar1) else float(row.ar1)})
    training_season = forecast.loc[forecast["ds"] <= VALIDATION_END, ["ds", "season_yearly"]].copy()
    training_season["month"] = training_season["ds"].dt.month
    seasonal = [{"month": int(month), "contribution_ton": float(value)}
                for month, value in training_season.groupby("month")["season_yearly"].mean().items()]
    weights = model.model.ar_weights.detach().cpu().numpy()[0].tolist()
    ar = sorted([{"lag": len(weights) - index, "weight": float(value)}
                 for index, value in enumerate(weights)], key=lambda row: row["lag"])
    params = model.config_normalization.get_data_params("__df__")
    ds_scale = params["ds"].scale
    # A nominal month is 365.25 / 12 days; this is not a calendar-specific slope.
    slope_scale = float(params["y"].scale) * (365.25 / 12) / (ds_scale.total_seconds() / 86400)
    deltas = model.model.trend.get_trend_deltas.detach().cpu().numpy()[0, 0]
    changepoints = [{"date": (params["ds"].shift + pd.Timedelta(seconds=float(cp) * ds_scale.total_seconds())).strftime("%Y-%m-%d"),
                     "slope_change_ton_per_nominal_month": float(delta) * slope_scale}
                    for cp, delta in zip(model.model.config_trend.changepoints[1:], deltas[1:], strict=True)]
    return {"fit_start": "2017-01", "fit_end": "2024-12", "timeline": timeline,
            "yearly_monthly_mean": seasonal,
            "yearly_peak_month": max(seasonal, key=lambda r: r["contribution_ton"])["month"],
            "yearly_low_month": min(seasonal, key=lambda r: r["contribution_ton"])["month"],
            "ar_weights": ar, "largest_absolute_ar_lag": max(ar, key=lambda r: abs(r["weight"]))["lag"],
            "potential_changepoints": changepoints, "nominal_month_days": 365.25 / 12,
            "max_forecast_difference_ton": difference, "max_component_reconstruction_difference_ton": reconstruction}
