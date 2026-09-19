#!/usr/bin/env python3
"""Run the repository's experiment reviewer; emit its unmodified JSON evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
from app.domains import experiments


def main() -> int:
    parser = argparse.ArgumentParser(description="Review one preregistered synthetic growth experiment.")
    parser.add_argument("--db", type=Path, required=True, help="SQLite dataset path")
    parser.add_argument("--scenario", choices=[item["value"] for item in experiments.SCENARIOS], default="healthy_gain")
    parser.add_argument("--init", action="store_true", help="Initialize only the experiment domain's synthetic tables")
    parser.add_argument("--output", type=Path, help="Save the same review JSON to this file")
    args = parser.parse_args()
    if args.init:
        experiments.build_database(args.db)
    if not args.db.is_file():
        parser.error("Database does not exist; provide an existing dataset or initialize it with --init.")
    result = experiments.analyze({"domain": "experiments", "task": "report", "filters": {"scenario": args.scenario}}, args.db)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
