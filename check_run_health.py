# check_run_health.py

"""
Standalone script: reports retry/failure health for an Inspect eval log —
n_attempts and error_message aren't written into any of the output CSVs
(derive_csvs() only carries through the final scored metrics), so this is
the only way to see how many samples needed a retry or failed outright
after an unattended run.

Usage:
    python3 check_run_health.py [path/to/log.eval]

If no path is given, uses the most recently modified .eval log directly
under inspect_pipeline.LOG_DIR (same convention as derive_csvs_only.py).
"""

import sys

from inspect_ai.log import read_eval_log

import inspect_pipeline as ip
from derive_csvs_only import find_latest_log


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else find_latest_log(ip.LOG_DIR)

    print(f"Reading log: {log_path}")
    log = read_eval_log(log_path)
    samples = log.samples
    total = len(samples)
    print(f"Total samples: {total}\n")

    retried = [s for s in samples if (s.metadata.get("n_attempts") or 1) > 1]
    failed = [s for s in samples if s.metadata.get("error_message")]

    print(f"Needed a retry (n_attempts > 1): {len(retried)} / {total}")
    print(f"Failed outright (error_message set): {len(failed)} / {total}")

    if retried:
        print("\n--- Samples that needed a retry ---")
        for s in retried:
            m = s.metadata
            print(
                f"  {m['condition']} | {m['strategy']} | {m['retrieval_type']} | "
                f"epoch {m['epoch']} | {m['model']['label']} | n_attempts={m.get('n_attempts')}"
            )

    if failed:
        print("\n--- Samples that failed outright ---")
        for s in failed:
            m = s.metadata
            print(
                f"  {m['condition']} | {m['strategy']} | {m['retrieval_type']} | "
                f"epoch {m['epoch']} | {m['model']['label']}"
            )
            print(f"    error: {m['error_message']}")

    if not retried and not failed:
        print("\nAll samples succeeded cleanly on the first attempt.")


if __name__ == "__main__":
    main()
