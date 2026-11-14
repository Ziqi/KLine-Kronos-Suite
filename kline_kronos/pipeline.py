"""Deterministic intraday OHLCV cleaning, session-aligned 1m->5m resampling, QA auditing & Kronos scaling."""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import hashlib
import json
import math
import pathlib
from typing import Iterable, Sequence


@dataclasses.dataclass(frozen=True)
class BarRecord:
    timestamp: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


_COLUMN_ALIASES = {
    "dt": "timestamp",
    "date": "timestamp",
    "datetime": "timestamp",
    "timestamps": "timestamp",
    "time": "timestamp",
    "open": "open",
    "openprice": "open",
    "high": "high",
    "highprice": "high",
    "low": "low",
    "lowprice": "low",
    "close": "close",
    "closeprice": "close",
    "price": "close",
    "volume": "volume",
    "vol": "volume",
    "amount": "amount",
    "amt": "amount",
    "turnover": "amount",
}


def parse_timestamp(raw: str | dt.datetime) -> dt.datetime:
    if isinstance(raw, dt.datetime):
        return raw.replace(tzinfo=None)
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return dt.datetime.fromisoformat(s).replace(tzinfo=None)


def load_ohlcv_csv(path: str | pathlib.Path) -> list[BarRecord]:
    fp = pathlib.Path(path)
    records: list[BarRecord] = []
    with fp.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        col_map: dict[str, str] = {}
        for raw_col in reader.fieldnames:
            norm = _COLUMN_ALIASES.get(raw_col.strip().lower())
            if norm and norm not in col_map.values():
                col_map[norm] = raw_col
        required = ("timestamp", "open", "high", "low", "close")
        if not all(k in col_map for k in required):
            raise ValueError(f"Missing required OHLCV columns in {fp.name}: found {reader.fieldnames}")

        for row in reader:
            try:
                ts = parse_timestamp(row[col_map["timestamp"]])
                o = float(row[col_map["open"]])
                h = float(row[col_map["high"]])
                lo = float(row[col_map["low"]])
                c = float(row[col_map["close"]])
                vol = float(row[col_map["volume"]]) if "volume" in col_map and row[col_map["volume"]] != "" else 0.0
                amt = float(row[col_map["amount"]]) if "amount" in col_map and row[col_map["amount"]] != "" else 0.0
            except (TypeError, ValueError):
                continue
            if any(math.isnan(v) or math.isinf(v) for v in (o, h, lo, c, vol, amt)):
                continue
            records.append(BarRecord(ts, o, h, lo, c, vol, amt))
    return records


def write_ohlcv_csv(
    records: Sequence[BarRecord],
    path: str | pathlib.Path,
    ts_col: str = "timestamps",
) -> int:
    fp = pathlib.Path(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    with fp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([ts_col, "open", "high", "low", "close", "volume", "amount"])
        for r in records:
            writer.writerow(
                [
                    r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{r.open:.4f}".rstrip("0").rstrip(".") if "." in f"{r.open:.4f}" else f"{r.open}",
                    f"{r.high:.4f}".rstrip("0").rstrip(".") if "." in f"{r.high:.4f}" else f"{r.high}",
                    f"{r.low:.4f}".rstrip("0").rstrip(".") if "." in f"{r.low:.4f}" else f"{r.low}",
                    f"{r.close:.4f}".rstrip("0").rstrip(".") if "." in f"{r.close:.4f}" else f"{r.close}",
                    f"{r.volume:.2f}".rstrip("0").rstrip("."),
                    f"{r.amount:.2f}".rstrip("0").rstrip("."),
                ]
            )
    return len(records)


MARKET_SESSIONS: dict[str, tuple[tuple[tuple[int, int], tuple[int, int]], ...]] = {
    "cn": (((9, 35), (11, 30)), ((13, 5), (15, 0))),
    "hk": (((9, 35), (12, 0)), ((13, 5), (16, 0))),
    "us": (((9, 35), (16, 0)),),
    "crypto": (((0, 0), (23, 55)),),
}


def clean_1m_records(records: Iterable[BarRecord], market: str = "cn") -> list[BarRecord]:
    """Deduplicate, sort, filter session boundary noise, and synthesize missing session close bar."""
    if market not in MARKET_SESSIONS:
        raise ValueError(f"Unsupported market: {market}")
    by_ts: dict[dt.datetime, BarRecord] = {}
    for r in records:
        t = r.timestamp.time()
        if market == "cn":
            if t == dt.time(13, 0, 0) or dt.time(15, 1, 0) <= t <= dt.time(15, 31, 0):
                continue
        elif market == "hk":
            if t == dt.time(13, 0, 0) or dt.time(16, 1, 0) <= t <= dt.time(16, 15, 0):
                continue
        elif market == "us":
            if t < dt.time(9, 30, 0) or t > dt.time(16, 0, 0):
                continue
        by_ts[r.timestamp] = r

    if not by_ts:
        return []

    sorted_recs = [by_ts[k] for k in sorted(by_ts)]
    if market == "crypto":
        return sorted_recs

    close_time = {"cn": dt.time(15, 0, 0), "hk": dt.time(16, 0, 0), "us": dt.time(16, 0, 0)}[market]
    by_day: dict[dt.date, list[BarRecord]] = {}
    for r in sorted_recs:
        by_day.setdefault(r.timestamp.date(), []).append(r)

    for day, day_bars in by_day.items():
        if not any(b.timestamp.time() == close_time for b in day_bars):
            last = day_bars[-1]
            close_ts = dt.datetime.combine(day, close_time)
            by_ts[close_ts] = BarRecord(
                timestamp=close_ts,
                open=last.close,
                high=last.close,
                low=last.close,
                close=last.close,
                volume=0.0,
                amount=0.0,
            )

    return [by_ts[k] for k in sorted(by_ts)]


def _bucket_5m_right_label(ts: dt.datetime) -> dt.datetime:
    """Match pandas `resample('5min', closed='right', label='right')` semantics deterministically."""
    floored = ts.replace(second=0, microsecond=0)
    if ts.second > 0 or ts.microsecond > 0:
        floored += dt.timedelta(minutes=1)
    rem = floored.minute % 5
    if rem == 0 and ts.second == 0 and ts.microsecond == 0:
        return floored
    add_min = (5 - rem) % 5
    return floored + dt.timedelta(minutes=add_min)


def resample_1m_to_5m_records(
    records: Iterable[BarRecord],
    start_dt: dt.datetime | None = None,
    end_dt: dt.datetime | None = None,
) -> list[BarRecord]:
    filtered = sorted(
        (
            r
            for r in records
            if (start_dt is None or r.timestamp >= start_dt)
            and (end_dt is None or r.timestamp <= end_dt)
        ),
        key=lambda x: x.timestamp,
    )
    if not filtered:
        return []

    buckets: dict[dt.datetime, list[BarRecord]] = {}
    for r in filtered:
        label = _bucket_5m_right_label(r.timestamp)
        buckets.setdefault(label, []).append(r)

    out: list[BarRecord] = []
    for label in sorted(buckets):
        grp = buckets[label]
        out.append(
            BarRecord(
                timestamp=label,
                open=grp[0].open,
                high=max(x.high for x in grp),
                low=min(x.low for x in grp),
                close=grp[-1].close,
                volume=sum(x.volume for x in grp),
                amount=sum(x.amount for x in grp),
            )
        )
    return out


def resample_csv_to_5m(
    input_file: str | pathlib.Path,
    output_dir: str | pathlib.Path,
    start_dt: dt.datetime | None = None,
    end_dt: dt.datetime | None = None,
    rename_1m_tag: bool = False,
) -> tuple[bool, pathlib.Path, int]:
    in_path = pathlib.Path(input_file)
    recs_1m = load_ohlcv_csv(in_path)
    recs_5m = resample_1m_to_5m_records(recs_1m, start_dt=start_dt, end_dt=end_dt)
    out_name = in_path.name.replace("_1m_", "_5m_") if rename_1m_tag else in_path.name
    out_path = pathlib.Path(output_dir) / out_name
    if not recs_5m:
        return False, out_path, 0
    count = write_ohlcv_csv(recs_5m, out_path, ts_col="timestamps")
    return True, out_path, count


def audit_5m_records(records: Sequence[BarRecord], min_rows: int = 10) -> tuple[bool, str]:
    if len(records) < min_rows:
        return False, f"TOO_SHORT ({len(records)} < {min_rows})"
    prev_ts: dt.datetime | None = None
    for r in records:
        if r.high < r.low or r.open <= 0 or r.close <= 0 or r.volume < 0 or r.amount < 0:
            return False, f"INVALID_BAR_BOUNDS at {r.timestamp.isoformat()}"
        if prev_ts is not None and r.timestamp <= prev_ts:
            return False, f"NON_MONOTONIC_TIMESTAMP at {r.timestamp.isoformat()}"
        prev_ts = r.timestamp
    return True, "OK"


def audit_csv_file(path: str | pathlib.Path, min_rows: int = 10) -> tuple[bool, str]:
    try:
        recs = load_ohlcv_csv(path)
    except Exception as exc:
        return False, f"CORRUPT_OR_MISSING_COLUMNS ({exc})"
    return audit_5m_records(recs, min_rows=min_rows)


def pack_kronos_dataset_meta(
    csv_files: Sequence[str | pathlib.Path],
    output_manifest_json: str | pathlib.Path,
    min_rows: int = 10,
) -> dict[str, object]:
    """Validate multiple 5m CSV files and emit a deterministic JSON + SHA-256 dataset manifest."""
    symbols: dict[str, dict[str, object]] = {}
    for fp_raw in sorted(pathlib.Path(p) for p in csv_files):
        recs = load_ohlcv_csv(fp_raw)
        ok, status = audit_5m_records(recs, min_rows=min_rows)
        if not ok:
            continue
        sym = fp_raw.stem.split("_")[0]
        digest = hashlib.sha256(fp_raw.read_bytes()).hexdigest()
        symbols[sym] = {
            "source_file": fp_raw.name,
            "rows": len(recs),
            "start": recs[0].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "end": recs[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "sha256": digest,
        }

    manifest = {
        "schema_version": "1.0.0",
        "symbol_count": len(symbols),
        "symbols": symbols,
    }
    out_p = pathlib.Path(output_manifest_json)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out_p.write_text(payload, encoding="utf-8")
    out_p.with_suffix(out_p.suffix + ".sha256").write_text(
        f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}  {out_p.name}\n",
        encoding="utf-8",
    )
    return manifest


def prepare_inference_window(
    records: Sequence[BarRecord],
    lookback: int = 90,
    clip_bound: float = 5.0,
) -> tuple[list[list[float]], list[float], list[float]]:
    if len(records) < lookback:
        raise ValueError(f"Insufficient history: {len(records)} < lookback={lookback}")
    window = records[-lookback:]
    matrix = [[r.open, r.high, r.low, r.close, r.volume, r.amount] for r in window]
    n = float(len(matrix))
    means = [sum(row[j] for row in matrix) / n for j in range(6)]
    stds = [math.sqrt(sum((row[j] - means[j]) ** 2 for row in matrix) / n) for j in range(6)]
    normed: list[list[float]] = []
    for row in matrix:
        norm_row = []
        for j in range(6):
            z = (row[j] - means[j]) / (stds[j] + 1e-5)
            z = max(-clip_bound, min(clip_bound, z))
            norm_row.append(z)
        normed.append(norm_row)
    return normed, means, stds


def inverse_scale_trajectory(
    norm_rows: Sequence[Sequence[float]],
    means: Sequence[float],
    stds: Sequence[float],
) -> list[list[float]]:
    return [[round(row[j] * stds[j] + means[j], 3) for j in range(6)] for row in norm_rows]


def next_market_trading_bar_5m(current_time: dt.datetime, market: str = "cn") -> dt.datetime:
    """Advance one right-closed 5-minute session bar across CN, HK, US, or 24/7 Crypto calendars."""
    if market not in MARKET_SESSIONS:
        raise ValueError(f"Unsupported market: {market}")
    next_t = current_time.replace(second=0, microsecond=0) + dt.timedelta(minutes=5)
    if market == "crypto":
        return next_t

    sessions = MARKET_SESSIONS[market]
    first_open = sessions[0][0]
    last_close = sessions[-1][1]
    while True:
        if next_t.weekday() >= 5:
            days_ahead = 7 - next_t.weekday()
            next_t = (next_t + dt.timedelta(days=days_ahead)).replace(
                hour=first_open[0], minute=first_open[1], second=0
            )
            continue
        hm = (next_t.hour, next_t.minute)
        if any(seg_start <= hm <= seg_end for seg_start, seg_end in sessions):
            return next_t
        if len(sessions) == 2 and sessions[0][1] < hm <= (sessions[1][0][0], 0):
            next_t = next_t.replace(hour=sessions[1][0][0], minute=sessions[1][0][1], second=0)
        elif hm > last_close:
            next_t = (next_t + dt.timedelta(days=1)).replace(
                hour=first_open[0], minute=first_open[1], second=0
            )
        else:
            next_t = next_t.replace(hour=first_open[0], minute=first_open[1], second=0)


def next_cn_trading_bar_5m(current_time: dt.datetime) -> dt.datetime:
    """Advance one 5-minute A-share session bar (09:35..11:30, 13:05..15:00, Mon-Fri)."""
    return next_market_trading_bar_5m(current_time, market="cn")


def audit_lookahead_and_hygiene(
    records: Sequence[BarRecord], market: str = "cn", max_jump_pct: float = 0.25
) -> dict[str, object]:
    """Detect look-ahead timestamp misalignment, off-session leakage bars, and extreme flash spikes."""
    if market not in MARKET_SESSIONS:
        raise ValueError(f"Unsupported market: {market}")
    issues: list[str] = []
    sessions = MARKET_SESSIONS[market]
    prev: BarRecord | None = None
    for r in records:
        if r.timestamp.minute % 5 != 0 or r.timestamp.second != 0:
            issues.append(f"MISALIGNED_5M_LABEL:{r.timestamp.isoformat()}")
        if market != "crypto":
            hm = (r.timestamp.hour, r.timestamp.minute)
            if r.timestamp.weekday() >= 5 or not any(s <= hm <= e for s, e in sessions):
                issues.append(f"OFF_SESSION_LEAKAGE_BAR:{r.timestamp.isoformat()}")
        if prev is not None:
            if r.timestamp <= prev.timestamp:
                issues.append(f"NON_MONOTONIC_LEAK:{r.timestamp.isoformat()}")
            if prev.close > 0 and abs(r.close - prev.close) / prev.close > max_jump_pct:
                issues.append(f"EXTREME_RETURN_SPIKE:{r.timestamp.isoformat()}")
        prev = r
    return {
        "passed": len(issues) == 0,
        "market": market,
        "rows_checked": len(records),
        "issue_count": len(issues),
        "issues": issues[:20],
    }


def export_foundation_windows_jsonl(
    records: Sequence[BarRecord],
    output_path: str | pathlib.Path,
    lookback: int = 16,
    horizon: int = 4,
    symbol: str = "SYNTH",
) -> int:
    """Export sliding OHLCV context/target windows as universal JSONL (Chronos / TimesFM / HF compatible)."""
    total = lookback + horizon
    out_fp = pathlib.Path(output_path)
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_fp.open("w", encoding="utf-8") as f:
        for idx in range(0, max(0, len(records) - total + 1)):
            ctx = records[idx : idx + lookback]
            fut = records[idx + lookback : idx + total]
            item = {
                "item_id": symbol,
                "start": ctx[0].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "context_end": ctx[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "context_close": [round(b.close, 4) for b in ctx],
                "target_close": [round(b.close, 4) for b in fut],
            }
            f.write(json.dumps(item) + "\n")
            written += 1
    return written
