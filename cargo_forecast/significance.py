"""Diebold-Mariano tests on forecasts that were already produced and frozen.

Supplementary only: no model is fitted here, and no result is used to reselect
the official configuration.
"""

from __future__ import annotations

import math
from statistics import mean
from typing import Any

import pandas as pd

from .data import COLUMNS
from .enrichment import data_sha256, research_frame
from .modeling import _metrics


BASELINES = ("last_month", "same_month_last_year")
LOSSES = ("absolute", "squared")
ALPHA = 0.05


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Lentz continued fraction for the incomplete beta function."""
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    fraction = d
    for m in range(1, 300):
        for numerator in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
                          -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):
            d = 1.0 + numerator * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + numerator / c
            c = c if abs(c) > tiny else tiny
            fraction *= c * d
        if abs(c * d - 1.0) < 1e-15:
            return fraction
    raise ArithmeticError("Fungsi beta tak lengkap tidak konvergen.")


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1.0 - math.exp(log_front) * _beta_continued_fraction(b, a, 1.0 - x) / b


def t_two_sided_p(t: float, df: int) -> float:
    """Two-sided p-value of Student's t; scipy is not part of the environment."""
    if df < 1 or not math.isfinite(t):
        raise ValueError("Statistik t atau derajat bebas tidak valid.")
    return _regularized_beta(df / 2.0, 0.5, df / (df + t * t))


def diebold_mariano(actual: list[float], forecast_a: list[float], forecast_b: list[float], *, loss: str) -> dict[str, float | int]:
    """One-step DM test with the Harvey-Leybourne-Newbold small-sample correction.

    d_t = L(e_a) - L(e_b); a negative mean means forecast A has the smaller loss.
    For h = 1 the long-run variance is the variance of d_t (no autocovariance terms).
    """
    if loss not in LOSSES:
        raise ValueError(f"Loss tidak dikenal: {loss}")
    if not actual or not len(actual) == len(forecast_a) == len(forecast_b):
        raise ValueError("Panjang aktual dan kedua prediksi harus sama.")
    power = 1 if loss == "absolute" else 2
    differences = [abs(a - y) ** power - abs(b - y) ** power
                   for y, a, b in zip(actual, forecast_a, forecast_b, strict=True)]
    n = len(differences)
    centre = mean(differences)
    variance = sum((value - centre) ** 2 for value in differences) / n
    if n < 3 or variance <= 0:
        raise ValueError("Selisih loss terlalu sedikit atau tidak bervariasi.")
    dm = centre / math.sqrt(variance / n)
    hln = dm * math.sqrt((n - 1) / n)
    return {"n": n, "mean_loss_difference": centre, "dm": dm, "dm_hln": hln,
            "df": n - 1, "p_value": t_two_sided_p(hln, n - 1)}


def _compare(rows: list[dict[str, Any]], baselines: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    actual = [float(row["actual"]) for row in rows]
    model = [float(row["neuralprophet"]) for row in rows]
    return {baseline: {loss: diebold_mariano(actual, model, [float(row[baseline]) for row in rows], loss=loss)
                       for loss in LOSSES}
            for baseline in baselines}


def build_significance(frame: pd.DataFrame, diagnostics: dict, walk_forward: dict, *, report_sha256: str) -> dict[str, Any]:
    data = research_frame(frame)
    source = {"data_sha256": data_sha256(data), "report_sha256": report_sha256}
    if (diagnostics["source"]["data_sha256"], diagnostics["source"]["report_sha256"]) != (source["data_sha256"], report_sha256):
        raise ValueError("Diagnostik tidak cocok dengan snapshot atau laporan resmi.")
    if walk_forward["source"] != source:
        raise ValueError("Backtest tidak cocok dengan snapshot atau laporan resmi.")
    indexed = data.set_index("ds")
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "uji_signifikansi_tambahan_bukan_pengganti_uji_resmi",
        "source": source,
        "method": {"name": "Diebold-Mariano dengan koreksi sampel kecil Harvey-Leybourne-Newbold",
                   "horizon_months": 1, "losses": list(LOSSES), "alpha": ALPHA,
                   "difference": "loss NeuralProphet dikurangi loss pembanding; negatif berarti galat NeuralProphet lebih kecil",
                   "reference_distribution": "t dengan derajat bebas n-1, dua sisi"},
        "series": {},
    }
    for target in COLUMNS:
        test_rows = diagnostics["series"][target]["monthly"]
        if len(test_rows) != 18:
            raise ValueError("Uji resmi harus memiliki 18 bulan.")
        walk_rows = []
        for row in walk_forward["series"][target]["monthly"]:
            month = pd.Timestamp(f"{row['ds']}-01")
            walk_rows.append({**row, "same_month_last_year": float(indexed.loc[month - pd.DateOffset(months=12), target])})
        if len(walk_rows) != 42:
            raise ValueError("Backtest harus memiliki 42 bulan.")
        actual = [row["actual"] for row in walk_rows]
        walk_metrics = {method: _metrics(pd.DataFrame({"aktual": actual, "prediksi": [row[method] for row in walk_rows]}))
                        for method in ("neuralprophet", *BASELINES)}
        result["series"][target] = {
            "test_18": {"start": test_rows[0]["ds"], "end": test_rows[-1]["ds"], "comparisons": _compare(test_rows, BASELINES)},
            "walk_forward_42": {"start": walk_rows[0]["ds"], "end": walk_rows[-1]["ds"], "metrics": walk_metrics,
                                "same_month_last_year": [{"ds": row["ds"], "prediksi": row["same_month_last_year"]} for row in walk_rows],
                                "comparisons": _compare(walk_rows, BASELINES)},
        }
    return result
