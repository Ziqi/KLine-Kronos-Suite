# Stage 02 · Session-Aligned 1m-to-5m OHLCV Aggregator (`02_resample/`)

## Overview

Aggregates cleaned 1-minute intraday bars from `01_extract/gui_downloads/` into standardized 5-minute OHLCVA bars (`timestamps, open, high, low, close, volume, amount`) under `02_resample/gui_out_5m/` using right-closed, right-labeled intervals (`09:31..09:35 -> 09:35`).

## Usage

```bash
# Fast zero-dependency CLI resampling:
python3 -m kline_kronos resample ./examples/sample_1m_ohlcv.csv --out-dir ./02_resample/gui_out_5m

# Launch desktop resampling workstation:
python3 ./02_resample/gui_resample_5m.py
```
