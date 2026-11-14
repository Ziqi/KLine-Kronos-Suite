# Contributing to KLine Kronos Suite

Thank you for contributing to **KLine Kronos Suite**!

## Development & Verification Quickstart

The core data cleaning, resampling, auditing, and scaling engine (`kline_kronos/`) runs on **Python 3.10+ standard library** with zero mandatory runtime dependencies, enabling instant local testing:

```bash
git clone https://github.com/Ziqi/KLine-Kronos-Suite.git
cd KLine-Kronos-Suite

# Run unit, adversarial, static-security & >=85% statement coverage gate
python3 ./tests/test_pipeline_core.py --min-coverage 85

# Verify SPDX-2.3 SBOM generation
python3 ./scripts/generate_spdx_sbom.py --version dev --output /tmp/kline.spdx.json
```

For the optional `ttkbootstrap` desktop workstations and PyTorch / Kronos training supervisors:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Coding & Security Guardrails

1. **Zero `os.system` & Zero Bare `except:`** — Use `subprocess.run([...])` with explicit argument lists (`kline_kronos.desktop_utils`) and catch explicit exception types. Our test suite enforces this via AST inspection.
2. **Zero Real Account Data or Live Credentials** — Never commit live API tokens (`MIANA_TOKEN`) or large proprietary market CSV dumps; use synthetic test vectors such as `examples/sample_1m_ohlcv.csv`.
3. **Developer Certificate of Origin (DCO)** — Sign off commits with `git commit -s` (`Signed-off-by:`).
