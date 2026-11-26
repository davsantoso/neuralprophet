"""Analisis post hoc dari artefak yang sudah dibekukan: koreksi Holm dan rata-rata lima seed.

Tidak ada model yang dilatih di sini, dan hasilnya tidak dipakai untuk memilih ulang
konfigurasi resmi. Semua masukan dibaca dari artifacts/significance.json dan
artifacts/diagnostics.json.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .modeling import _metrics
from .significance import BASELINES, LOSSES, PROTOCOLS, diebold_mariano

TARGETS = ("bongkar", "muat")
BEST_BASELINE = {"bongkar": "same_month_last_year", "muat": "last_month"}


def holm_adjust(p_values: list[float]) -> list[float]:
    """Nilai p terkoreksi Holm (step-down), urutan keluaran sama dengan masukan."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def build_holm(significance: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for target in TARGETS:
        for protocol in PROTOCOLS:
            for baseline in BASELINES:
                for loss in LOSSES:
                    item = significance["series"][target][protocol]["comparisons"][baseline][loss]
                    rows.append({"deret": target, "protokol": protocol, "pembanding": baseline, "loss": loss,
                                 "p_value": item["p_value"]})
    for row, adjusted in zip(rows, holm_adjust([row["p_value"] for row in rows]), strict=True):
        row["p_holm"] = adjusted
        row["signifikan_setelah_holm"] = adjusted < 0.05
    return rows


def build_seed_ensemble(diagnostics: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for target in TARGETS:
        series = diagnostics["series"][target]
        runs = series["seed_runs"]
        months = [row["ds"] for row in runs[0]["predictions"]]
        for run in runs:
            if [row["ds"] for row in run["predictions"]] != months:
                raise ValueError("Bulan prediksi antarseed tidak sama.")
        ensemble = [sum(run["predictions"][i]["prediksi"] for run in runs) / len(runs) for i in range(len(months))]
        monthly = series["monthly"]
        if [row["ds"] for row in monthly] != months:
            raise ValueError("Bulan diagnostik dan prediksi seed tidak sama.")
        actual = [float(row["actual"]) for row in monthly]
        baseline = BEST_BASELINE[target]
        metrics = _metrics(pd.DataFrame({"aktual": actual, "prediksi": ensemble}))
        result[target] = {
            "seeds": [run["seed"] for run in runs],
            "metrics": metrics,
            "pembanding_terbaik": baseline,
            "dm_absolut_vs_pembanding_terbaik": diebold_mariano(actual, ensemble, [float(row[baseline]) for row in monthly],
                                                               loss="absolute"),
            "prediksi": [{"ds": ds, "aktual": a, "prediksi_rata_rata": p} for ds, a, p in zip(months, actual, ensemble, strict=True)],
        }
    return result
