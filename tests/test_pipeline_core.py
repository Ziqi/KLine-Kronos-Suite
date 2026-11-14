#!/usr/bin/env python3
"""Deterministic unit, adversarial & >=85% statement coverage gate for KLine-Kronos-Suite."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import pathlib
import sys
import tempfile
import trace
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import io
import kline_kronos  # noqa: E402
from kline_kronos.cli import main as cli_main, serve_kline_mcp_stdio  # noqa: E402
from kline_kronos.desktop_utils import bring_window_frontmost, reveal_in_file_manager  # noqa: E402
from kline_kronos.pipeline import (  # noqa: E402
    BarRecord,
    audit_5m_records,
    audit_csv_file,
    audit_lookahead_and_hygiene,
    clean_1m_records,
    export_foundation_windows_jsonl,
    inverse_scale_trajectory,
    load_ohlcv_csv,
    next_cn_trading_bar_5m,
    next_market_trading_bar_5m,
    pack_kronos_dataset_meta,
    parse_timestamp,
    prepare_inference_window,
    resample_1m_to_5m_records,
    resample_csv_to_5m,
    write_ohlcv_csv,
)


class KLineKronosPipelineTests(unittest.TestCase):
    def test_sample_csv_end_to_end_cli(self) -> None:
        self.assertEqual(cli_main(["demo"]), 0)
        sample_csv = REPO_ROOT / "examples" / "sample_1m_ohlcv.csv"
        self.assertTrue(sample_csv.is_file())
        with tempfile.TemporaryDirectory() as td:
            tdir = pathlib.Path(td)
            cleaned_csv = tdir / "sh000001_1m_clean.csv"
            self.assertEqual(cli_main(["clean", str(sample_csv), "--output", str(cleaned_csv)]), 0)
            self.assertTrue(cleaned_csv.is_file())

            out_5m_dir = tdir / "out_5m"
            self.assertEqual(cli_main(["resample", str(cleaned_csv), "--out-dir", str(out_5m_dir)]), 0)
            out_5m_csv = out_5m_dir / "sh000001_5m_clean.csv"
            self.assertTrue(out_5m_csv.is_file())

            self.assertEqual(cli_main(["audit", str(out_5m_csv), "--min-rows", "2"]), 0)

            manifest_path = tdir / "dataset_manifest.json"
            self.assertEqual(
                cli_main(["manifest", str(out_5m_dir), "--output", str(manifest_path), "--min-rows", "2"]),
                0,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["symbol_count"], 1)
            self.assertTrue(manifest_path.with_suffix(".json.sha256").is_file())

    def test_clean_1m_filters_noise_and_synthesizes_1500_close(self) -> None:
        self.assertEqual(clean_1m_records([]), [])
        raw = [
            BarRecord(parse_timestamp("2026-01-05 09:31:00"), 10.0, 10.2, 9.9, 10.1, 1000, 10100),
            BarRecord(parse_timestamp("2026-01-05 13:00:00"), 10.1, 10.1, 10.1, 10.1, 0, 0),
            BarRecord(parse_timestamp("2026-01-05 14:59:00"), 10.2, 10.5, 10.1, 10.4, 2000, 20800),
            BarRecord(parse_timestamp("2026-01-05 15:05:00"), 10.4, 10.4, 10.4, 10.4, 0, 0),
        ]
        cleaned = clean_1m_records(raw)
        self.assertEqual(len(cleaned), 3)
        self.assertEqual(cleaned[-1].timestamp, dt.datetime(2026, 1, 5, 15, 0, 0))
        self.assertEqual(cleaned[-1].close, 10.4)
        self.assertEqual(cleaned[-1].volume, 0.0)
        self.assertEqual(cleaned[-1].amount, 0.0)

    def test_resample_right_closed_and_window_bounds(self) -> None:
        self.assertEqual(resample_1m_to_5m_records([]), [])
        bars = [
            BarRecord(dt.datetime(2026, 1, 5, 9, 31), 10.0, 10.2, 9.9, 10.1, 100, 1000),
            BarRecord(dt.datetime(2026, 1, 5, 9, 32), 10.1, 10.4, 10.0, 10.3, 150, 1530),
            BarRecord(dt.datetime(2026, 1, 5, 9, 35), 10.3, 10.5, 10.2, 10.4, 200, 2080),
            BarRecord(dt.datetime(2026, 1, 5, 9, 36), 10.4, 10.6, 10.3, 10.5, 120, 1260),
        ]
        res = resample_1m_to_5m_records(bars)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].timestamp, dt.datetime(2026, 1, 5, 9, 35))
        self.assertAlmostEqual(res[0].open, 10.0)
        self.assertAlmostEqual(res[0].high, 10.5)
        self.assertAlmostEqual(res[0].low, 9.9)
        self.assertAlmostEqual(res[0].close, 10.4)
        self.assertAlmostEqual(res[0].volume, 450.0)
        self.assertEqual(res[1].timestamp, dt.datetime(2026, 1, 5, 9, 40))

    def test_audit_adversarial_cases(self) -> None:
        ok, msg = audit_5m_records([], min_rows=3)
        self.assertFalse(ok)
        self.assertIn("TOO_SHORT", msg)

        bad_bounds = [
            BarRecord(dt.datetime(2026, 1, 5, 9, 35), 10.0, 9.5, 10.2, 10.0, 100, 1000),
            BarRecord(dt.datetime(2026, 1, 5, 9, 40), 10.0, 10.2, 9.8, 10.0, 100, 1000),
        ]
        ok2, msg2 = audit_5m_records(bad_bounds, min_rows=2)
        self.assertFalse(ok2)
        self.assertIn("INVALID_BAR_BOUNDS", msg2)

        non_mono = [
            BarRecord(dt.datetime(2026, 1, 5, 9, 40), 10.0, 10.2, 9.8, 10.0, 100, 1000),
            BarRecord(dt.datetime(2026, 1, 5, 9, 35), 10.0, 10.2, 9.8, 10.0, 100, 1000),
        ]
        ok3, msg3 = audit_5m_records(non_mono, min_rows=2)
        self.assertFalse(ok3)
        self.assertIn("NON_MONOTONIC_TIMESTAMP", msg3)

        with tempfile.TemporaryDirectory() as td:
            bad_csv = pathlib.Path(td) / "bad.csv"
            bad_csv.write_text("foo,bar\n1,2\n", encoding="utf-8")
            ok4, msg4 = audit_csv_file(bad_csv, min_rows=1)
            self.assertFalse(ok4)
            self.assertIn("CORRUPT_OR_MISSING_COLUMNS", msg4)
            self.assertEqual(cli_main(["audit", str(bad_csv), "--min-rows", "1"]), 1)

            empty_csv = pathlib.Path(td) / "empty.csv"
            empty_csv.write_text("dt,open,high,low,close,volume,amount\n", encoding="utf-8")
            self.assertEqual(cli_main(["resample", str(empty_csv), "--out-dir", td]), 1)

    def test_scaling_and_trading_calendar_stepper(self) -> None:
        recs = [
            BarRecord(dt.datetime(2026, 1, 5, 9, 35) + dt.timedelta(minutes=5 * i), 10.0 + i * 0.1, 10.2 + i * 0.1, 9.9 + i * 0.1, 10.1 + i * 0.1, 100 + i, 1000 + i * 10)
            for i in range(12)
        ]
        normed, means, stds = prepare_inference_window(recs, lookback=10)
        self.assertEqual(len(normed), 10)
        restored = inverse_scale_trajectory(normed, means, stds)
        self.assertAlmostEqual(restored[-1][3], recs[-1].close, places=2)

        with self.assertRaises(ValueError):
            prepare_inference_window(recs, lookback=50)

        # Morning -> Lunch jump (11:30 -> 13:05)
        self.assertEqual(
            next_cn_trading_bar_5m(dt.datetime(2026, 1, 5, 11, 30)),
            dt.datetime(2026, 1, 5, 13, 5),
        )
        # Afternoon close -> Next morning (15:00 -> 09:35)
        self.assertEqual(
            next_cn_trading_bar_5m(dt.datetime(2026, 1, 5, 15, 0)),
            dt.datetime(2026, 1, 6, 9, 35),
        )
        # Friday 15:00 -> Monday 09:35 (2026-01-09 is Friday -> 2026-01-12 Monday)
        self.assertEqual(
            next_cn_trading_bar_5m(dt.datetime(2026, 1, 9, 15, 0)),
            dt.datetime(2026, 1, 12, 9, 35),
        )
        # Pre-open -> 09:35
        self.assertEqual(
            next_cn_trading_bar_5m(dt.datetime(2026, 1, 5, 9, 15)),
            dt.datetime(2026, 1, 5, 9, 35),
        )
        # US, HK, Crypto multi-market calendars & clean/leakage-audit/export-windows/MCP
        self.assertEqual(
            next_market_trading_bar_5m(dt.datetime(2026, 1, 5, 16, 0), market="us"),
            dt.datetime(2026, 1, 6, 9, 35),
        )
        self.assertEqual(
            next_market_trading_bar_5m(dt.datetime(2026, 1, 5, 12, 0), market="hk"),
            dt.datetime(2026, 1, 5, 13, 5),
        )
        self.assertEqual(
            next_market_trading_bar_5m(dt.datetime(2026, 1, 10, 23, 55), market="crypto"),
            dt.datetime(2026, 1, 11, 0, 0),
        )
        with self.assertRaises(ValueError):
            next_market_trading_bar_5m(dt.datetime(2026, 1, 5, 9, 35), market="invalid")
        with self.assertRaises(ValueError):
            clean_1m_records([], market="invalid")
        with self.assertRaises(ValueError):
            audit_lookahead_and_hygiene([], market="invalid")

        us_cleaned = clean_1m_records(
            [
                BarRecord(dt.datetime(2026, 1, 5, 9, 15), 100.0, 100.2, 99.9, 100.1, 10, 1000),
                BarRecord(dt.datetime(2026, 1, 5, 15, 59), 101.0, 101.5, 100.8, 101.2, 50, 5060),
            ],
            market="us",
        )
        self.assertEqual(us_cleaned[-1].timestamp, dt.datetime(2026, 1, 5, 16, 0))
        hk_cleaned = clean_1m_records(
            [
                BarRecord(dt.datetime(2026, 1, 5, 13, 0), 50.0, 50.0, 50.0, 50.0, 0, 0),
                BarRecord(dt.datetime(2026, 1, 5, 15, 59), 51.0, 51.2, 50.9, 51.1, 20, 1022),
            ],
            market="hk",
        )
        self.assertEqual(hk_cleaned[-1].timestamp, dt.datetime(2026, 1, 5, 16, 0))
        crypto_cleaned = clean_1m_records(
            [BarRecord(dt.datetime(2026, 1, 10, 23, 59), 90000.0, 90100.0, 89900.0, 90050.0, 5, 450250)],
            market="crypto",
        )
        self.assertEqual(len(crypto_cleaned), 1)

        leaky_bars = [
            BarRecord(dt.datetime(2026, 1, 5, 9, 32), 10.0, 10.2, 9.9, 10.0, 100, 1000),
            BarRecord(dt.datetime(2026, 1, 5, 12, 10), 15.0, 15.5, 14.9, 15.0, 100, 1500),
        ]
        leak_rep = audit_lookahead_and_hygiene(leaky_bars, market="cn")
        self.assertFalse(leak_rep["passed"])
        self.assertGreaterEqual(leak_rep["issue_count"], 2)

        with tempfile.TemporaryDirectory() as td:
            tdir = pathlib.Path(td)
            clean_us_csv = tdir / "spy_5m.csv"
            write_ohlcv_csv(recs, clean_us_csv)
            self.assertEqual(cli_main(["leakage-audit", str(clean_us_csv), "--market", "us"]), 0)
            win_jsonl = tdir / "windows.jsonl"
            self.assertEqual(
                cli_main(["export-windows", str(clean_us_csv), "--output", str(win_jsonl), "--lookback", "6", "--horizon", "2"]),
                0,
            )
            self.assertEqual(len(win_jsonl.read_text(encoding="utf-8").splitlines()), 5)

            mcp_in = io.BytesIO(
                b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'
                b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                b'{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n'
                + json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "audit_ohlcv_leakage", "arguments": {"csv_path": str(clean_us_csv), "market": "us"}},
                    }
                ).encode("utf-8")
                + b"\n"
                + b'{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"step_trading_calendar","arguments":{"timestamp":"2026-01-05 16:00:00","market":"us"}}}\n'
                + b'{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"bad_tool","arguments":{}}}\n'
                + b'{"jsonrpc":"2.0","id":6,"method":"bad/method"}\n'
            )
            mcp_out = io.BytesIO()
            self.assertEqual(serve_kline_mcp_stdio(mcp_in, mcp_out), 0)
            self.assertIn(b"kline-kronos-suite", mcp_out.getvalue())

    def test_static_security_invariants_across_all_repo_scripts(self) -> None:
        """Guarantee zero os.system(), zero bare except:, zero deprecated '5T', and valid AST across all scripts."""
        for py in sorted(REPO_ROOT.rglob("*.py")):
            if ".git" in py.parts or py.resolve() == pathlib.Path(__file__).resolve():
                continue
            src = py.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(py))
            self.assertNotIn("os.system(", src, f"Unsafe os.system found in {py}")
            self.assertNotIn("resample('5T'", src, f"Deprecated pandas 5T found in {py}")
            self.assertNotIn('resample("5T"', src, f"Deprecated pandas 5T found in {py}")
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    self.assertIsNotNone(node.type, f"Bare except: found in {py}:{node.lineno}")

    def test_desktop_utils_nonblocking_smoke(self) -> None:
        # Ensure parse_timestamp datetime passthrough & desktop helpers return bool without raising
        now = dt.datetime(2026, 1, 5, 9, 35)
        self.assertEqual(parse_timestamp(now), now)
        self.assertIsInstance(bring_window_frontmost(), bool)
        if sys.platform != "darwin":
            self.assertIsInstance(reveal_in_file_manager(REPO_ROOT, select_file=False), bool)


def executable_lines(py_file: pathlib.Path) -> set[int]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)
        ):
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) and isinstance(node.value.value, str):
                continue
            lines.add(node.lineno)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-coverage", type=float, default=85.0)
    args = ap.parse_args()

    tracer = trace.Trace(count=1, trace=0)

    def _run_suite() -> unittest.TestResult:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(KLineKronosPipelineTests)
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    result = tracer.runfunc(_run_suite)
    if not result.wasSuccessful():
        return 1

    counts = tracer.results().counts
    tracked = [
        REPO_ROOT / "kline_kronos" / "__init__.py",
        REPO_ROOT / "kline_kronos" / "pipeline.py",
        REPO_ROOT / "kline_kronos" / "cli.py",
    ]
    total_exec = 0
    total_hit = 0
    for fp in tracked:
        exec_set = executable_lines(fp)
        hit_set = {ln for ln in exec_set if counts.get((str(fp.resolve()), ln), 0) > 0 or counts.get((str(fp), ln), 0) > 0}
        total_exec += len(exec_set)
        total_hit += len(hit_set)
        pct_f = (100.0 * len(hit_set) / len(exec_set)) if exec_set else 100.0
        print(f"[COVERAGE] {fp.relative_to(REPO_ROOT)}: {len(hit_set)}/{len(exec_set)} ({pct_f:.2f}%)")

    pct = (100.0 * total_hit / total_exec) if total_exec else 100.0
    print(f"[INFO] Total kline_kronos statement coverage: {total_hit}/{total_exec} ({pct:.2f}%, gate >= {args.min_coverage:.1f}%)")
    if pct < args.min_coverage:
        print(f"[FAIL] Coverage {pct:.2f}% below threshold {args.min_coverage:.1f}%", file=sys.stderr)
        return 1
    print(f"[PASS] Coverage gate satisfied ({pct:.2f}% >= {args.min_coverage:.1f}%).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
