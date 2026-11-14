# Security Policy

## 1. Supported Versions

| Version | Supported |
| :--- | :--- |
| `1.1.x` (`main`) | Yes |
| `1.0.x` | Critical security fixes only |
| `< 1.0.0` | No |

## 2. Reporting a Vulnerability & Researcher Credit

Please **do not** report security vulnerabilities in public GitHub issues.

Use **[GitHub Private Vulnerability Reporting](https://github.com/Ziqi/KLine-Kronos-Suite/security/advisories/new)** to submit a confidential advisory directly to the maintainer:

- **Acknowledgement SLA:** Within **48 hours**
- **Triage & Fix Target:** Within **14 days** for confirmed high-severity issues (`<= 60 days` maximum for all severities)
- **Researcher Recognition:** Reporters are credited in the corresponding GitHub Security Advisory and release notes unless anonymity is requested.

## 3. Vulnerability Response Process

1. **Intake & Reproduction:** Validate the advisory privately in an isolated branch and add a deterministic regression test in `tests/test_pipeline_core.py` or `tests/fuzz_kline_pipeline.py`.
2. **Patch & Audit:** Verify `CodeQL` SAST, `>=85%` coverage gate, 2,000-iteration fuzzing, `repro_archive.py --verify`, and OSV dependency advisories pass with zero warnings.
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
| **Dataset & Release Supply Chain** | Silent dataset tampering, vulnerable transitive packages, or unsigned release tarballs | SHA-256 dataset manifests (`.json.sha256`), 0-CVE dependency floors, 40-char SHA-pinned GitHub Actions (`permissions: {}`), `Ed25519` signatures, bit-for-bit reproducible PAX tarballs, and Sigstore `SLSA Build Level 3` provenance | `.github/workflows/attestations.yml` + `.github/workflows/scorecard.yml` + `scripts/repro_archive.py --verify` |

## 6. OpenSSF OSPS Baseline (Level 3) Alignment & Reproducible Builds

`KLine-Kronos-Suite` (`v1.1.0+`) conforms to the **OpenSSF Open Source Project Security (OSPS) Baseline Level 3** controls alongside **EU Cyber Resilience Act (CRA)** open-source steward readiness:

| OSPS Domain | Level 3 Control Requirement | Repository Implementation & Evidence |
| :--- | :--- | :--- |
| **Access Control & Governance (`OSPS-AC` / `OSPS-GV`)** | Protected default branch, immutable git history, signed commits/releases, machine-readable security metadata | Protected `main` branch with required CI status checks, linear history, `GOVERNANCE.md`, and `.github/SECURITY-INSIGHTS.yml` (Schema `2.0.0`) |
| **Build & Release Integrity (`OSPS-BR`)** | Pinned CI dependencies, non-falsifiable SLSA L3 build provenance, cryptographic release signatures, bit-for-bit reproducible archives | 40-char SHA-pinned GitHub Actions (`permissions: {}`), Sigstore OIDC `actions/attest-build-provenance` (`SLSA Build Level 3`), offline `Ed25519` `.sig` (`keys/release-signing-pub.pem`), and `python3 ./scripts/repro_archive.py --verify` (`mtime=0, uid/gid=0`) |
| **Documentation & Licensing (`OSPS-DO` / `OSPS-LE`)** | Machine-readable SPDX licensing on 100% of files, accurate SBOM per release | `FSFE REUSE 3.3` (`REUSE.toml`) verified in CI + deterministic `SPDX-2.3` JSON SBOM (`scripts/generate_spdx_sbom.py` + `actions/attest-sbom`) |
| **Quality & Vulnerability Management (`OSPS-QA` / `OSPS-VM`)** | Automated SAST, fuzzing, >=85% coverage gate, coordinated private vulnerability disclosure (`<=48h` ack) | GitHub `CodeQL`, `tests/test_pipeline_core.py --min-coverage 85` (`>91%` actual), `tests/fuzz_kline_pipeline.py --iterations 2000`, Dependabot, and GitHub Private Vulnerability Reporting |
