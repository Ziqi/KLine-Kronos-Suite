# Stage 03 · Dataset QA Inspector & Kronos Dictionary Packer (`03_slicer/`)

## Overview

Audits 5-minute OHLCVA CSV series in `02_resample/gui_out_5m/` for missing columns, NaNs, price-bound violations (`high < low`), and non-monotonic timestamps before packing verified symbols into either:
- **Deterministic SHA-256 JSON Manifests** (`python3 -m kline_kronos manifest ...`) for reproducible auditability, or
- **Kronos Training Dictionary `.pkl` Bundles** (`03_slicer/gui_out_slices/`) via `gui_slicer.py`.

## Usage

```bash
# Headless QA audit & SHA-256 manifest generation:
python3 -m kline_kronos audit ./02_resample/gui_out_5m/sample_5m_ohlcv.csv --min-rows 2
python3 -m kline_kronos manifest ./02_resample/gui_out_5m --output ./03_slicer/dataset_manifest.json

# Desktop QA & .pkl packer workstation:
python3 ./03_slicer/gui_slicer.py
```
