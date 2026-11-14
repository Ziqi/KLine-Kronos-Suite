# Stage 01 · High-Frequency 1-Minute OHLCV Acquisition & Continuity Cleaner (`01_extract/`)

## Overview

Acquires raw 1-minute intraday equity bars, deduplicates timestamps, removes non-trading call-auction noise (`13:00:00` and `15:01:00–15:31:00`), synthesizes missing `15:00:00` session-close bars when absent, and persists clean CSV series to `01_extract/gui_downloads/`.

## Components

- **`miana_1m_clean_save.py`** — Headless multi-threaded CLI downloader & incremental updater (`MIANA_TOKEN` via environment variable, bounded `<= 8` day request windows).
- **`resample_1m_to_5m.py`** — Batch `ProcessPoolExecutor` converter from 1-minute CSVs to right-closed (`closed='right', label='right'`) 5-minute Kronos CSVs.
- **`gui_fetch_kline.py`** — `ttkbootstrap` desktop workstation with symbol fuzzy search, incremental progress tracking, and one-click file reveal.

## Headless CLI Usage

```bash
# Clean a local 1-minute CSV with zero external dependencies:
python3 -m kline_kronos clean ../examples/sample_1m_ohlcv.csv --output /tmp/cleaned_1m.csv

# Batch API download (requires your own MIANA_TOKEN):
export MIANA_TOKEN="your_api_token"
python3 01_extract/miana_1m_clean_save.py --symbol sh600519 --start "2026-01-01 09:30:00" --out-dir 01_extract/gui_downloads
```
