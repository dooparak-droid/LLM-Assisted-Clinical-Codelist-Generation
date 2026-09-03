# derive_csvs_only.py

"""
Standalone script: regenerates the six output CSVs from an existing Inspect
eval log, without re-running any experiments (no model API calls). Useful
after correcting the categorised gold standard CSVs
(data/categorised_gold_standards/), or any other post-hoc fix to
derive_csvs() itself — just re-derive outputs from a log already on disk.

Usage:
    python3 derive_csvs_only.py [path/to/log.eval]

If no path is given, uses the most recently modified .eval log directly
under inspect_pipeline.LOG_DIR (not recursing into subdirectories, so
one-off comparison logs under inspect_logs/manual_comparison/ are ignored).
"""

import glob
import os
import sys

from inspect_ai.log import read_eval_log

import inspect_pipeline as ip


def find_latest_log(log_dir):
    candidates = glob.glob(os.path.join(log_dir, "*.eval"))
    if not candidates:
        raise SystemExit(f"No .eval logs found directly under {log_dir}")
    return max(candidates, key=os.path.getmtime)


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else find_latest_log(ip.LOG_DIR)

    print(f"Reading log: {log_path}")
    log = read_eval_log(log_path)
    print(f"Loaded {len(log.samples)} samples")

    ip.derive_csvs(log, ip.OUTPUT_DIR)


if __name__ == "__main__":
    main()
