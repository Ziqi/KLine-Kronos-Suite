# Engineering Roadmap (`KLine-Kronos-Suite`)

## Shipped (`v1.1.x` — Current Stable)
- **Zero-Dependency Deterministic Core & CLI (`kline_kronos/`)**: Pure Python 3.10+ standard-library CLI (`demo`, `clean`, `resample`, `audit`, `manifest`) with `>91%` core statement coverage (`kline_kronos`), 2,000-iteration randomized/Atheris fuzzing, and `uvx` / Homebrew (`Ziqi/tap`) zero-clone distribution.
- **Five-Stage Desktop Workstation (`01_extract/` – `05_predictor_gui/`)**: Modular `ttkbootstrap` GUI suite for 1-minute quote acquisition, right-closed `1m -> 5m` aggregation (`'5min'` syntax compatible with `pandas 2.x/3.x`; workstation pins `>=3.1.1`), sliding-window dataset QA, two-stage Kronos Tokenizer/Predictor supervision, and China A-share (`09:30–11:30, 13:00–15:00`) trading-calendar-aligned inference rollouts.
- **Supply-Chain Assurance & Reproducible Builds**: OpenSSF Best Practices Silver (`#16679`), OpenSSF OSPS Baseline Level 3, bit-for-bit reproducible PAX release archives (`scripts/repro_archive.py --verify`), `SLSA Build Level 3` provenance, `SPDX-2.3` SBOM, offline `Ed25519` release signatures (`keys/release-signing-pub.pem`), `FSFE REUSE 3.3` license compliance, and `CodeQL` SAST.

## Planned (`v1.2` — Zero-Copy Columnar Storage & Safe Tensors)
- Optional **Apache Parquet / Arrow** (`pyarrow`) output backend alongside CSV and JSON+SHA-256 manifests to eliminate `pickle` serialization in high-scale multi-symbol training pipelines.
- Safe-tensor (`safetensors`) checkpoint verification preflight in Stage `04_trainer_gui` and Stage `05_predictor_gui`.

## Planned (`v1.3` — Pluggable Global Exchange Session Calendars)
- Configurable session-calendar profiles extending `next_cn_trading_bar_5m` to support **HKEX** (`09:30–12:00`, `13:00–16:00`), **US Equities** (`09:30–16:00 ET`), and **24/7 Digital Asset** (`UTC`) continuous bars under unified right-closed interval semantics.

## Planned (`v2.0` — Hardware-Accelerated Local Inference & Walk-Forward Evaluation)
- Pluggable Apple Silicon (`MPS` / `CoreML`) and `ONNX Runtime` inference adapters for Stage `05_predictor_gui`.
- Deterministic walk-forward out-of-sample evaluation harness reporting directional hit-rate, pinball loss across empirical quantiles, and calibration drift.
