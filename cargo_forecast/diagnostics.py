"""Diagnostik tambahan pada 18 bulan uji penelitian yang sudah dibekukan."""

from __future__ import annotations

import hashlib
import math
from statistics import mean, stdev
from typing import Any

import pandas as pd

from .data import COLUMNS, THESIS_CUTOFF, validate_monthly
from .modeling import SEED, SENSITIVITY_SEEDS, VALIDATION_END


BASELINE_LABELS = {
    "last_month": "Nilai aktual bulan sebelumnya",
    "same_month_last_year": "Nilai aktual bulan yang sama tahun sebelumnya",
}


def _metrics(actual: list[float], predicted: list[float]) -> dict[str, float]:
    if not actual or len(actual) != len(predicted) or any(value <= 0 for value in actual):
        raise ValueError("Pasangan aktual dan prediksi tidak valid.")
    errors = [forecast - observed for observed, forecast in zip(actual, predicted, strict=True)]
    if not all(math.isfinite(value) for value in [*actual, *predicted, *errors]):
        raise ValueError("Pasangan aktual dan prediksi harus berhingga.")
    return {
        "MAE": mean(abs(error) for error in errors),
        "RMSE": math.sqrt(mean(error * error for error in errors)),
        "MAPE": 100 * mean(abs(error) / observed for error, observed in zip(errors, actual, strict=True)),
    }


def _seed_summary(runs: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    summaries = {}
    for metric in ("MAE", "RMSE", "MAPE"):
        values = [float(run["metrics"][metric]) for run in runs]
        summaries[metric] = {
            "mean": mean(values),
            "sample_std": stdev(values),
            "min": min(values),
            "max": max(values),
        }
    return summaries


def build_diagnostics(
    frame: pd.DataFrame,
    report: dict[str, Any],
    seed_runs: dict[str, list[dict[str, Any]]],
    *,
    report_sha256: str,
) -> dict[str, Any]:
    """Join fixed test forecasts to historical-only benchmarks and seed runs."""
    data = validate_monthly(frame)
    if len(data) != 114 or data["ds"].max() != THESIS_CUTOFF:
        raise ValueError("Diagnostik harus memakai 114 bulan data penelitian.")
    if report.get("n_observations") != 114 or report.get("cutoff") != "2026-06":
        raise ValueError("Laporan resmi tidak cocok dengan data penelitian.")
    if set(seed_runs) != set(COLUMNS):
        raise ValueError("Uji seed perlu kedua deret.")
    indexed = data.set_index("ds")
    test_dates = list(pd.date_range(VALIDATION_END + pd.offsets.MonthBegin(1), THESIS_CUTOFF, freq="MS"))
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "analisis_tambahan_bukan_pengganti_laporan_resmi",
        "source": {
            "report_sha256": report_sha256,
            "data_sha256": hashlib.sha256(
                data.assign(ds=data["ds"].dt.strftime("%Y-%m"))
                .to_csv(index=False, lineterminator="\n")
                .encode("utf-8")
            ).hexdigest(),
            "category": "Soekarno Hatta-Jakarta",
            "unit": "ton per bulan",
        },
        "evaluation": {
            "test_start": "2025-01",
            "test_end": "2026-06",
            "test_months": 18,
            "horizon_months": 1,
            "baselines": BASELINE_LABELS,
            "baseline_rule": "Setiap prediksi memakai hanya nilai aktual yang telah tersedia sebelum bulan target.",
        },
        "sensitivity": {
            "seeds": list(SENSITIVITY_SEEDS),
            "fit_end": "2024-12",
            "selected_lags_fixed": True,
            "selection_note": "Lookback berasal dari validasi resmi seed 42 dan tidak dipilih ulang memakai data uji.",
            "test_note": "Lima pelatihan ulang per deret memakai split dan konfigurasi tetap; hasil uji tidak dipakai memilih seed terbaik.",
        },
        "series": {},
    }
    for target in COLUMNS:
        official = report["series"][target]
        predictions = official["test_predictions"]
        if len(predictions) != len(test_dates):
            raise ValueError(f"Prediksi uji resmi {target} tidak berjumlah 18.")
        monthly = []
        for date, row in zip(test_dates, predictions, strict=True):
            month = date.strftime("%Y-%m")
            observed = float(indexed.loc[date, target])
            if row["ds"] != month or not math.isclose(float(row["aktual"]), observed, abs_tol=1e-9):
                raise ValueError(f"Aktual uji resmi {target} tidak cocok pada {month}.")
            forecast = float(row["prediksi"])
            previous_month = float(indexed.loc[date - pd.DateOffset(months=1), target])
            previous_year = float(indexed.loc[date - pd.DateOffset(months=12), target])
            error = forecast - observed
            monthly.append({
                "ds": month,
                "actual": observed,
                "neuralprophet": forecast,
                "last_month": previous_month,
                "same_month_last_year": previous_year,
                "error": error,
                "absolute_error": abs(error),
                "ape_percent": 100 * abs(error) / observed,
            })
        actual = [row["actual"] for row in monthly]
        metrics = {
            method: _metrics(actual, [row[method] for row in monthly])
            for method in ("neuralprophet", *BASELINE_LABELS)
        }
        for name, value in official["test_metrics"].items():
            if not math.isclose(metrics["neuralprophet"][name], value, rel_tol=1e-10):
                raise ValueError(f"Metrik resmi {target} berubah pada {name}.")
        errors = [row["error"] for row in monthly]
        runs = seed_runs[target]
        if [run["seed"] for run in runs] != list(SENSITIVITY_SEEDS):
            raise ValueError(f"Urutan atau jumlah seed {target} tidak sesuai.")
        clean_runs = []
        for run in runs:
            seed_predictions = run["predictions"]
            if len(seed_predictions) != 18 or [row["ds"] for row in seed_predictions] != [row["ds"] for row in monthly]:
                raise ValueError(f"Prediksi seed {run['seed']} untuk {target} tidak lengkap.")
            if any(not math.isclose(float(row["aktual"]), expected, abs_tol=1e-9) for row, expected in zip(seed_predictions, actual, strict=True)):
                raise ValueError(f"Aktual seed {run['seed']} untuk {target} tidak cocok.")
            recomputed = _metrics(actual, [float(row["prediksi"]) for row in seed_predictions])
            if any(not math.isclose(recomputed[name], run["metrics"][name], rel_tol=1e-10) for name in recomputed):
                raise ValueError(f"Metrik seed {run['seed']} untuk {target} tidak cocok.")
            clean_runs.append(run)
        official_seed = next(run for run in clean_runs if run["seed"] == SEED)
        max_official_gap = max(
            abs(float(run_row["prediksi"]) - float(official_row["prediksi"]))
            for run_row, official_row in zip(official_seed["predictions"], predictions, strict=True)
        )
        if max_official_gap > 1e-5:
            raise ValueError(f"Seed 42 tidak mereproduksi prediksi resmi {target}; periksa versi lingkungan.")
        result["series"][target] = {
            "selected_n_lags": official["selected_n_lags"],
            "monthly": monthly,
            "metrics": metrics,
            "bias": {
                "mean_error": mean(errors),
                "overprediction_months": sum(error > 0 for error in errors),
                "underprediction_months": sum(error < 0 for error in errors),
                "exact_months": sum(error == 0 for error in errors),
            },
            "largest_errors": sorted(monthly, key=lambda row: row["absolute_error"], reverse=True)[:3],
            "seed_runs": clean_runs,
            "seed_summary": _seed_summary(clean_runs),
            "seed_42_max_forecast_difference_from_official": max_official_gap,
        }
    return result
