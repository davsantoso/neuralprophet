"""Run the resumable 42-month nested backtest offline (336 model fits)."""

import hashlib
import argparse
from importlib.metadata import version
from pathlib import Path
import sys
import warnings

from cargo_forecast.data import load_bps_data
from cargo_forecast.walkforward import atomic_json, walk_forward


def main():
    if sys.version_info >= (3, 13):
        raise SystemExit("Gunakan Python 3.12.")
    warnings.filterwarnings("ignore", category=FutureWarning)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=4)
    args = parser.parse_args()
    import torch
    torch.set_num_threads(1)
    report = Path("artifacts/report.json")
    original = report.read_bytes()
    result = walk_forward(load_bps_data(), report_sha256=hashlib.sha256(original).hexdigest(),
                          checkpoint=Path(".tmp/walk_forward_checkpoint.json"),
                          progress=lambda message: print(message, flush=True), workers=args.workers)
    result["environment"] = {"python": sys.version.split()[0], "neuralprophet": version("neuralprophet")}
    if report.read_bytes() != original:
        raise ValueError("Laporan resmi berubah selama backtest.")
    atomic_json(Path("artifacts/walk_forward.json"), result)
    print("Tersimpan: artifacts/walk_forward.json", flush=True)


if __name__ == "__main__":
    main()
