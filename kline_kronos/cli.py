"""Command-line entrypoint for headless KLine Kronos Suite operations."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
import tempfile

from . import __version__
from .pipeline import (
    MARKET_SESSIONS,
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


MCP_TOOLS = [
    {
        "name": "audit_ohlcv_leakage",
        "description": "Audit a 5-minute OHLCV CSV file for look-ahead timestamp misalignment, off-session leakage bars, and flash spikes across US, Crypto, HK, or CN calendars.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "csv_path": {"type": "string"},
                "market": {"type": "string", "enum": ["us", "crypto", "hk", "cn"], "default": "us"},
            },
            "required": ["csv_path"],
        },
    },
    {
        "name": "step_trading_calendar",
        "description": "Advance one right-closed 5-minute bar respecting US, Crypto (24/7), HKEX, or CN session & lunch/weekend boundaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timestamp": {"type": "string"},
                "market": {"type": "string", "enum": ["us", "crypto", "hk", "cn"], "default": "us"},
            },
            "required": ["timestamp"],
        },
    },
]


def serve_kline_mcp_stdio(in_stream, out_stream) -> int:
    while True:
        line = in_stream.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        req = json.loads(stripped.decode("utf-8"))
        req_id = req.get("id")
        method = req.get("method", "")
        if req_id is None or method.startswith("notifications/"):
            continue
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "kline-kronos-suite", "version": __version__},
                },
            }
        elif method == "tools/list":
            resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
        elif method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name")
            t_args = params.get("arguments") or {}
            if name == "audit_ohlcv_leakage":
                recs = load_ohlcv_csv(t_args["csv_path"])
                rep = audit_lookahead_and_hygiene(recs, market=t_args.get("market", "us"))
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(rep, indent=2)}], "isError": not rep["passed"]},
                }
            elif name == "step_trading_calendar":
                nxt = next_market_trading_bar_5m(parse_timestamp(t_args["timestamp"]), market=t_args.get("market", "us"))
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": nxt.strftime("%Y-%m-%d %H:%M:%S")}], "isError": False},
                }
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        out_stream.write(json.dumps(resp).encode("utf-8") + b"\n")
        out_stream.flush()
    return 0


def _run_zero_setup_demo() -> int:
    """Run an in-memory + auto-cleaned tempdir end-to-end showcase with zero external files."""
    raw = [
        BarRecord(parse_timestamp(f"2026-01-05 09:{31 + i:02d}:00"), 10.0 + 0.02 * i, 10.1 + 0.02 * i, 9.95 + 0.02 * i, 10.05 + 0.02 * i, 1200 + 50 * i, 12060 + 510 * i)
        for i in range(15)
    ] + [
        # Microstructure noise #1: 11:29..11:30 pre-lunch + 13:00:00 zero-volume boundary tick
        BarRecord(parse_timestamp("2026-01-05 11:29:00"), 10.35, 10.42, 10.31, 10.40, 1800, 18720),
        BarRecord(parse_timestamp("2026-01-05 11:30:00"), 10.40, 10.45, 10.38, 10.43, 2100, 21903),
        BarRecord(parse_timestamp("2026-01-05 13:00:00"), 10.43, 10.43, 10.43, 10.43, 0, 0),
        # Microstructure noise #2: missing 15:00 close + 15:05 post-close stray tick
        BarRecord(parse_timestamp("2026-01-05 14:59:00"), 10.50, 10.58, 10.48, 10.55, 3200, 33760),
        BarRecord(parse_timestamp("2026-01-05 15:05:00"), 10.55, 10.55, 10.55, 10.55, 0, 0),
    ]
    cleaned = clean_1m_records(raw)
    bars_5m = resample_1m_to_5m_records(cleaned)
    ok, verdict = audit_5m_records(bars_5m, min_rows=4)
    normed, means, stds = prepare_inference_window(bars_5m, lookback=4)
    restored = inverse_scale_trajectory(normed, means, stds)
    lunch_next = next_cn_trading_bar_5m(dt.datetime(2026, 1, 5, 11, 30))

    with tempfile.TemporaryDirectory() as td:
        tdir = pathlib.Path(td)
        csv_5m = tdir / "sh000001_5m_demo.csv"
        write_ohlcv_csv(bars_5m, csv_5m, ts_col="timestamps")
        manifest_path = tdir / "dataset_manifest.json"
        pack_kronos_dataset_meta([csv_5m], manifest_path, min_rows=4)
        manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    report = {
        "status": "ok" if ok else "fail",
        "version": __version__,
        "mode": "zero-setup-stdlib-demo",
        "raw_1m_rows": len(raw),
        "cleaned_1m_rows": len(cleaned),
        "synthesized_1500_close": cleaned[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "right_closed_5m_bars": len(bars_5m),
        "first_5m_label": bars_5m[0].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "lunch_break_step": f"2026-01-05 11:30:00 -> {lunch_next.strftime('%Y-%m-%d %H:%M:%S')}",
        "zscore_roundtrip_close": round(restored[-1][3], 4),
        "audit_verdict": verdict,
        "manifest_sha256": manifest_sha256,
    }
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kline-kronos",
        description="Deterministic 1m->5m OHLCV cleaning, resampling, QA auditing & dataset manifest CLI",
    )
    parser.add_argument("--version", action="version", version=f"kline-kronos {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "demo",
        help="Run a zero-file, zero-dependency synthetic 1m->5m clean, resample, QA & calendar showcase",
    )

    p_clean = sub.add_parser("clean", help="Clean 1-minute OHLCV CSV across CN, US, HK, or Crypto sessions")
    p_clean.add_argument("input_csv", type=pathlib.Path)
    p_clean.add_argument("--output", type=pathlib.Path, required=True)
    p_clean.add_argument("--market", choices=tuple(MARKET_SESSIONS), default="cn")

    p_res = sub.add_parser("resample", help="Resample 1-minute OHLCV CSV into right-closed 5-minute format")
    p_res.add_argument("input_csv", type=pathlib.Path)
    p_res.add_argument("--out-dir", type=pathlib.Path, required=True)

    p_aud = sub.add_parser("audit", help="Verify 5-minute OHLCV CSV schema, bounds, and timestamp monotonicity")
    p_aud.add_argument("input_csv", type=pathlib.Path)
    p_aud.add_argument("--min-rows", type=int, default=5)

    p_leak = sub.add_parser("leakage-audit", help="Audit 5-minute CSV for look-ahead bias, off-session bars, and spikes")
    p_leak.add_argument("input_csv", type=pathlib.Path)
    p_leak.add_argument("--market", choices=tuple(MARKET_SESSIONS), default="us")

    p_exp = sub.add_parser("export-windows", help="Export universal JSONL sliding windows (Chronos / TimesFM / HF)")
    p_exp.add_argument("input_csv", type=pathlib.Path)
    p_exp.add_argument("--output", type=pathlib.Path, required=True)
    p_exp.add_argument("--lookback", type=int, default=16)
    p_exp.add_argument("--horizon", type=int, default=4)

    p_pack = sub.add_parser("manifest", help="Build SHA-256 dataset manifest from 5-minute CSV directory")
    p_pack.add_argument("input_dir", type=pathlib.Path)
    p_pack.add_argument("--output", type=pathlib.Path, required=True)
    p_pack.add_argument("--min-rows", type=int, default=5)

    sub.add_parser("mcp", help="Run zero-dependency MCP JSON-RPC 2.0 server over stdio")

    args = parser.parse_args(argv)

    if args.cmd == "demo":
        return _run_zero_setup_demo()

    if args.cmd == "clean":
        raw = load_ohlcv_csv(args.input_csv)
        cleaned = clean_1m_records(raw, market=args.market)
        n = write_ohlcv_csv(cleaned, args.output, ts_col="dt")
        print(json.dumps({"status": "ok", "market": args.market, "input_rows": len(raw), "cleaned_rows": n, "output": str(args.output)}))
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

    if args.cmd == "leakage-audit":
        recs = load_ohlcv_csv(args.input_csv)
        rep = audit_lookahead_and_hygiene(recs, market=args.market)
        print(json.dumps(rep))
        return 0 if rep["passed"] else 1

    if args.cmd == "export-windows":
        recs = load_ohlcv_csv(args.input_csv)
        cnt = export_foundation_windows_jsonl(recs, args.output, lookback=args.lookback, horizon=args.horizon, symbol=args.input_csv.stem)
        print(json.dumps({"status": "ok", "windows": cnt, "output": str(args.output)}))
        return 0

    if args.cmd == "manifest":
        csvs = sorted(args.input_dir.glob("*.csv"))
        manifest = pack_kronos_dataset_meta(csvs, args.output, min_rows=args.min_rows)
        print(json.dumps({"status": "ok", "symbol_count": manifest["symbol_count"], "manifest": str(args.output)}))
        return 0

    if args.cmd == "mcp":
        return serve_kline_mcp_stdio(sys.stdin.buffer, sys.stdout.buffer)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
