# Security Policy

## 1. Supported Versions

| Version | Supported |
| :--- | :--- |
| `1.0.x` (`main`) | Yes |
| `< 1.0.0` | No |

## 2. Reporting a Vulnerability & Researcher Credit

Please **do not** report security vulnerabilities in public GitHub issues.

Use **[GitHub Private Vulnerability Reporting](https://github.com/Ziqi/KLine-Kronos-Suite/security/advisories/new)** to submit a confidential advisory directly to the maintainer:

- **Acknowledgement SLA:** Within **48 hours**
- **Triage & Fix Target:** Within **14 days** for confirmed high-severity issues (`<= 60 days` maximum for all severities)
- **Researcher Recognition:** Reporters are credited in the corresponding GitHub Security Advisory and release notes unless anonymity is requested.

## 3. Vulnerability Response Process

1. **Intake & Reproduction:** Validate the advisory privately in an isolated branch and add a deterministic regression test in `tests/test_pipeline_core.py` or `tests/fuzz_kline_pipeline.py`.
2. **Patch & Audit:** Verify `CodeQL` SAST, `>=85%` coverage gate, 2,000-iteration fuzzing, and OSV dependency advisories pass with zero warnings.
3. **Signed Release & Advisory:** Publish a signed patch release (`Ed25519` `.sig` + `SLSA Build Level 3` + `SPDX-2.3` SBOM) and disclose the advisory.

## 4. Serialization, Subprocess & Credential Hardening

- **Zero Shell Injection:** All cross-platform process launches and file-manager helpers strictly pass argument vectors (`subprocess.run([...], check=False)`) with `shell=False`; `tests/test_pipeline_core.py` enforces an AST gate blocking `os.system(` and bare `except:` across the entire repository.
- **Untrusted Checkpoint Warning:** Stage `03_slicer` can export local `.pkl` dictionary bundles for downstream PyTorch / Kronos training, and Stage `05_predictor_gui` loads local model checkpoints under `KRONOS_HOME`. **Never load `.pkl` or untrusted PyTorch checkpoint files from unverified third parties**; use the deterministic JSON + SHA-256 manifest workflow (`kline-kronos manifest`) for auditable data exchange.
- **Zero Embedded Secrets:** Market data API tokens are read exclusively from runtime environment variables (`MIANA_TOKEN`) over TLS 1.2+ (`https://`).

## 5. Architecture Threat Model & Security Assurance Case

| Trust Boundary | Threat Scenario | Fail-Closed Control | Automated Verification |
| :--- | :--- | :--- | :--- |
| **External Market CSV / Quote Feed $\rightarrow$ `kline_kronos`** | Malformed timestamps, `NaN`/`Inf` floats, negative volume, or inverted `high < low` bars corrupting downstream tensors | Strict column allowlisting, `math.isnan`/`isinf` filtering, monotonic timestamp check, and positive price bounds in `audit_5m_records` | `tests/test_pipeline_core.py` + 2,000-iteration `tests/fuzz_kline_pipeline.py` |
| **Desktop GUI $\rightarrow$ OS Process Execution** | Command injection via crafted filenames or workspace paths | Complete elimination of shell invocation (`os.system` banned); argv-only `subprocess.run` in `kline_kronos/desktop_utils.py` | Repo-wide AST gate in `test_static_security_invariants_across_all_repo_scripts` + GitHub `CodeQL` SAST |
| **Dataset & Release Supply Chain** | Silent dataset tampering, vulnerable transitive packages, or unsigned release tarballs | SHA-256 dataset manifests (`.json.sha256`), 0-CVE dependency floors, 40-char SHA-pinned GitHub Actions (`permissions: {}`), `Ed25519` signatures, and Sigstore `SLSA Build Level 3` provenance | `.github/workflows/attestations.yml` + `.github/workflows/scorecard.yml` + Dependabot |
