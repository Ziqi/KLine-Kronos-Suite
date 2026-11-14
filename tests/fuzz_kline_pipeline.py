#!/usr/bin/env python3
"""
KLine Kronos Suite Dual-Mode Fuzzing Harness (tests/fuzz_kline_pipeline.py)

Supports:
  1. Native Google Atheris coverage-guided fuzzing (`--atheris` when `atheris` is installed).
  2. Zero-dependency deterministic & randomized property-based mutation campaign
     (`python3 ./tests/fuzz_kline_pipeline.py --iterations 2000`) executed on every CI push/PR.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import pathlib
import random
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from kline_kronos.pipeline import (  # noqa: E402
    BarRecord,
    audit_5m_records,
    clean_1m_records,
    inverse_scale_trajectory,
    load_ohlcv_csv,
    next_cn_trading_bar_5m,
    parse_timestamp,
    prepare_inference_window,
    resample_1m_to_5m_records,
)


def fuzz_one_bytes(data: bytes) -> None:
    """Exercise CSV loader, timestamp parser, cleaner, resampler, and QA gate on arbitrary bytes."""
    text = data.decode("utf-8", errors="replace")

    for line in text.splitlines()[:6]:
        try:
            _ = parse_timestamp(line)
        except (ValueError, TypeError, OverflowError):
            pass

    with tempfile.TemporaryDirectory() as td:
        csv_path = pathlib.Path(td) / "fuzzed.csv"
        csv_path.write_bytes(data)
        try:
            recs = load_ohlcv_csv(csv_path)
        except (ValueError, csv.Error if "csv" in globals() else Exception):
            return

    cleaned = clean_1m_records(recs)
    for r in cleaned:
        t = r.timestamp.time()
        if t == dt.time(13, 0, 0):
            raise AssertionError("clean_1m_records leaked 13:00:00 boundary bar")
        if dt.time(15, 1, 0) <= t <= dt.time(15, 31, 0):
            raise AssertionError("clean_1m_records leaked 15:01-15:31 post-close bar")

    res5 = resample_1m_to_5m_records(cleaned)
    prev: dt.datetime | None = None
    for b in res5:
        if prev is not None and b.timestamp <= prev:
            raise AssertionError("resample_1m_to_5m_records produced non-monotonic timestamps")
        if b.timestamp.minute % 5 != 0 or b.timestamp.second != 0:
            raise AssertionError(f"Unaligned 5m bucket timestamp: {b.timestamp}")
        prev = b.timestamp

    _ok, _msg = audit_5m_records(res5, min_rows=2)


def fuzz_structured_market_invariants(rng: random.Random) -> None:
    """Property-based fuzzing over synthetic intraday bars, Z-score scaling, and session calendar."""
    base_day = dt.date(2026, rng.randint(1, 12), rng.randint(1, 28))
    n_bars = rng.randint(12, 48)
    price = rng.uniform(5.0, 500.0)
    raw_bars: list[BarRecord] = []

    cur_ts = dt.datetime.combine(base_day, dt.time(9, 30))
    for _ in range(n_bars):
        cur_ts += dt.timedelta(minutes=rng.randint(0, 7), seconds=rng.choice([0, 0, 15, 45]))
        delta = rng.uniform(-0.05, 0.05) * price
        o = max(0.01, price)
        c = max(0.01, price + delta)
        hi = max(o, c) + rng.uniform(0.0, 0.02 * price)
        lo = max(0.01, min(o, c) - rng.uniform(0.0, 0.02 * price))
        vol = rng.uniform(0.0, 1e6)
        amt = vol * ((o + c) * 0.5)
        raw_bars.append(BarRecord(cur_ts, o, hi, lo, c, vol, amt))
        price = c

    cleaned = clean_1m_records(raw_bars)
    if not any(b.timestamp.time() == dt.time(15, 0, 0) for b in cleaned):
        raise AssertionError("clean_1m_records failed to guarantee 15:00:00 daily close bar")

    res5 = resample_1m_to_5m_records(cleaned)
    ok, reason = audit_5m_records(res5, min_rows=1)
    if not ok:
        raise AssertionError(f"Valid positive synthetic bars failed audit_5m_records: {reason}")

    if len(res5) >= 8:
        lb = min(len(res5), rng.randint(5, 16))
        normed, means, stds = prepare_inference_window(res5, lookback=lb, clip_bound=5.0)
        for row in normed:
            for val in row:
                if math.isnan(val) or math.isinf(val) or val < -5.000001 or val > 5.000001:
                    raise AssertionError(f"Normalized Z-score escaped [-5, 5] clip bound: {val}")
        _ = inverse_scale_trajectory(normed, means, stds)

    stepped = next_cn_trading_bar_5m(cur_ts)
    if stepped.weekday() >= 5:
        raise AssertionError(f"next_cn_trading_bar_5m landed on weekend: {stepped}")
    hm = (stepped.hour, stepped.minute)
    if not (((9, 35) <= hm <= (11, 30)) or ((13, 5) <= hm <= (15, 0))):
        raise AssertionError(f"next_cn_trading_bar_5m landed outside trading hours: {stepped}")


def run_atheris() -> None:
    import atheris  # OpenSSF Scorecard recognized Python coverage-guided fuzzer

    atheris.Setup(sys.argv, fuzz_one_bytes)
    atheris.Fuzz()


def run_stdlib_campaign(iterations: int, seed: int) -> int:
    rng = random.Random(seed)
    seed_csv = (REPO_ROOT / "examples" / "sample_1m_ohlcv.csv").read_bytes()

    for i in range(iterations):
        if i % 2 == 0:
            fuzz_structured_market_invariants(rng)
        else:
            buf = bytearray(seed_csv)
            if buf:
                for _ in range(rng.randint(1, 12)):
                    idx = rng.randrange(len(buf))
                    buf[idx] = rng.randrange(256)
            fuzz_one_bytes(bytes(buf))

    edge_corpus = [
        b"",
        b"dt,open,high,low,close,volume,amount\n",
        b"dt,open,high,low,close\n2026-01-05 13:00:00,10,10,10,10\n2026-01-05 15:05:00,10,10,10,10\n",
        b"dt,open,high,low,close\n2026-01-05 09:31:00,NaN,Inf,-Inf,0\n",
        b"\xff\xfe\x00invalid-utf8\n1,2,3\n",
    ]
    for sample in edge_corpus:
        fuzz_one_bytes(sample)

    print(
        f"[PASS] [FUZZ-HARNESS] Completed {iterations} fuzz iterations + {len(edge_corpus)} edge cases (0 crashes, all OHLCV/Z-score/Calendar invariants held)."
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="KLine Kronos Suite Dual-Mode Fuzzing Harness")
    ap.add_argument("--atheris", action="store_true", help="Run native Google Atheris libFuzzer loop")
    ap.add_argument("--iterations", type=int, default=2000, help="Number of stdlib fuzz iterations")
    ap.add_argument("--seed", type=int, default=20261114, help="Deterministic PRNG seed")
    args, _unknown = ap.parse_known_args()

    if args.atheris:
        run_atheris()
        return 0
    return run_stdlib_campaign(args.iterations, args.seed)


if __name__ == "__main__":
    raise SystemExit(main())
