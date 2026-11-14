# Engineering Roadmap (`KLine-Kronos-Suite`)

## Shipped (`v1.0.x` — Current Stable)
- **Zero-Dependency Deterministic Core (`kline_kronos/`)**: Pure Python 3.10+ standard-library CLI (`clean`, `resample`, `audit`, `manifest`) with `>90%` statement coverage and 2,000-iteration randomized/Atheris fuzzing.
- **Five-Stage Desktop Workstation (`01_extract/` – `05_predictor_gui/`)**: Modular `ttkbootstrap` GUI suite for 1-minute quote acquisition, right-closed `1m -> 5m` aggregation (`pandas 2.x/3.x` `'5min'` compatible), sliding-window dataset QA, two-stage Kronos Tokenizer/Predictor supervision, and A-share trading-calendar-aligned inference rollouts.
- **Supply-Chain Assurance**: `SLSA Build Level 3` provenance, `SPDX-2.3` SBOM, offline `Ed25519` release signatures, `FSFE REUSE 3.3` license compliance, `CodeQL` SAST, and `OpenSSF Scorecard`.

## Planned (`v1.1` — Zero-Copy Columnar Storage & Safe Tensors)
- Optional **Apache Parquet / Arrow** (`pyarrow`) output backend alongside CSV and JSON+SHA-256 manifests to eliminate `pickle` serialization in high-scale multi-symbol training pipelines.
- Safe-tensor (`safetensors`) checkpoint verification preflight in Stage `04_trainer_gui` and Stage `05_predictor_gui`.

## Planned (`v1.2` — Pluggable Global Exchange Session Calendars)
- Configurable session-calendar profiles extending `next_cn_trading_bar_5m` to support **HKEX** (`09:30–12:00`, `13:00–16:00`), **US Equities** (`09:30–16:00 ET`), and **24/7 Digital Asset** (`UTC`) continuous bars under unified right-closed interval semantics.

## Planned (`v2.0` — Hardware-Accelerated Local Inference & Walk-Forward Evaluation)
- Pluggable Apple Silicon (`MPS` / `CoreML`) and `ONNX Runtime` inference adapters for Stage `05_predictor_gui`.
- Deterministic walk-forward out-of-sample evaluation harness reporting directional hit-rate, pinball loss across empirical quantiles, and calibration drift.
