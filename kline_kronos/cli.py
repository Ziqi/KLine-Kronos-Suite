"""Command-line entrypoint for headless KLine Kronos Suite operations."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from . import __version__
from .pipeline import (
    audit_csv_file,
    clean_1m_records,
    load_ohlcv_csv,
    pack_kronos_dataset_meta,
    resample_csv_to_5m,
    write_ohlcv_csv,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kline-kronos",
        description="Deterministic 1m->5m OHLCV cleaning, resampling, QA auditing & dataset manifest CLI",
    )
    parser.add_argument("--version", action="version", version=f"kline-kronos {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_clean = sub.add_parser("clean", help="Clean 1-minute OHLCV CSV and synthesize missing 15:00 session bar")
    p_clean.add_argument("input_csv", type=pathlib.Path)
    p_clean.add_argument("--output", type=pathlib.Path, required=True)

    p_res = sub.add_parser("resample", help="Resample 1-minute OHLCV CSV into Kronos 5-minute format")
    p_res.add_argument("input_csv", type=pathlib.Path)
    p_res.add_argument("--out-dir", type=pathlib.Path, required=True)

    p_aud = sub.add_parser("audit", help="Verify 5-minute OHLCV CSV schema, bounds, and timestamp monotonicity")
    p_aud.add_argument("input_csv", type=pathlib.Path)
    p_aud.add_argument("--min-rows", type=int, default=5)

    p_pack = sub.add_parser("manifest", help="Build SHA-256 dataset manifest from 5-minute CSV directory")
    p_pack.add_argument("input_dir", type=pathlib.Path)
    p_pack.add_argument("--output", type=pathlib.Path, required=True)
    p_pack.add_argument("--min-rows", type=int, default=5)

    args = parser.parse_args(argv)

    if args.cmd == "clean":
        raw = load_ohlcv_csv(args.input_csv)
        cleaned = clean_1m_records(raw)
        n = write_ohlcv_csv(cleaned, args.output, ts_col="dt")
        print(json.dumps({"status": "ok", "input_rows": len(raw), "cleaned_rows": n, "output": str(args.output)}))
        return 0

    if args.cmd == "resample":
        ok, out_path, count = resample_csv_to_5m(args.input_csv, args.out_dir, rename_1m_tag=True)
        if not ok:
            print(json.dumps({"status": "empty", "output": str(out_path)}), file=sys.stderr)
            return 1
        print(json.dumps({"status": "ok", "rows_5m": count, "output": str(out_path)}))
        return 0

    if args.cmd == "audit":
        ok, verdict = audit_csv_file(args.input_csv, min_rows=args.min_rows)
        print(json.dumps({"status": "ok" if ok else "fail", "verdict": verdict, "file": args.input_csv.name}))
        return 0 if ok else 1

    if args.cmd == "manifest":
        csvs = sorted(args.input_dir.glob("*.csv"))
        manifest = pack_kronos_dataset_meta(csvs, args.output, min_rows=args.min_rows)
        print(json.dumps({"status": "ok", "symbol_count": manifest["symbol_count"], "manifest": str(args.output)}))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
