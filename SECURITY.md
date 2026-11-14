# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| `1.0.x` (`main`) | Yes |
| `< 1.0.0` | No |

## Reporting a Vulnerability

Please **do not** report security vulnerabilities in public GitHub issues.

Use **[GitHub Private Vulnerability Reporting](https://github.com/Ziqi/KLine-Kronos-Suite/security/advisories/new)** to submit a confidential advisory directly to the maintainer:

- **Acknowledgement SLA:** Within **48 hours**
- **Triage & Fix Target:** Within **14 days** for confirmed high-severity issues

## Serialization & Model Checkpoint Safety Notice

- Stage `03_slicer` can export local `.pkl` dictionary bundles for downstream PyTorch / Kronos training, and Stage `05_predictor_gui` loads local model checkpoints under `KRONOS_HOME`.
- **Never load `.pkl` or untrusted PyTorch checkpoint files downloaded from unverified third parties**, as Python `pickle` deserialization can execute arbitrary code. For untrusted exchange or audit workflows, use the deterministic JSON + SHA-256 manifest mode (`kline-kronos manifest`).
- Zero API tokens or credentials are stored in source files; pass market data API tokens strictly via environment variables (`MIANA_TOKEN`).
