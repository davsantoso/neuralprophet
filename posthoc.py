"""Membentuk artifacts/posthoc.json dari artefak yang sudah ada; tanpa pelatihan."""

import hashlib
import json
from pathlib import Path

from cargo_forecast.posthoc import build_holm, build_seed_ensemble
from cargo_forecast.walkforward import atomic_json

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sig_path, diag_path = ROOT / "artifacts/significance.json", ROOT / "artifacts/diagnostics.json"
    significance = json.loads(sig_path.read_text(encoding="utf-8"))
    diagnostics = json.loads(diag_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "kind": "analisis_post_hoc_bukan_pengganti_hasil_resmi",
        "source": {"significance_sha256": sha(sig_path), "diagnostics_sha256": sha(diag_path)},
        "holm": {"jumlah_uji": 16, "alpha": 0.05, "uji": build_holm(significance)},
        "rata_rata_lima_seed": build_seed_ensemble(diagnostics),
        "catatan": "Dihitung setelah evaluasi dari prediksi dan nilai p yang tersimpan. Seed 42 tetap hasil utama.",
    }
    atomic_json(ROOT / "artifacts/posthoc.json", result)
    for row in result["holm"]["uji"]:
        print(f"{row['deret']:8} {row['protokol']:16} {row['pembanding']:21} {row['loss']:9} p={row['p_value']:.4f} holm={row['p_holm']:.4f}")
    for target, item in result["rata_rata_lima_seed"].items():
        print(target, round(item["metrics"]["MAE"], 2), "p =", round(item["dm_absolut_vs_pembanding_terbaik"]["p_value"], 3))


if __name__ == "__main__":
    main()
