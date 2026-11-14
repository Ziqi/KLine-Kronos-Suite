# Project Governance

## Governance Model

**KLine Kronos Suite** (`v1.1.0`) follows a lightweight **Benevolent Dictator For Life (BDFL)** / Lead Maintainer model optimized for deterministic engineering quality and supply-chain security:

- **Lead Maintainer:** `@Ziqi`
- **Pull Request & CI Gate:** All changes targeting `main` must pass the automated CI suite (`>=85%` statement coverage, AST security invariants, FSFE REUSE licensing check) and CodeQL SAST analysis.
- **License Continuity:** All contributions are licensed under the MIT License (`LICENSE`) with Developer Certificate of Origin (`git commit -s`) sign-off.
