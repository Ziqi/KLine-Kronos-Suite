#!/usr/bin/env python3
"""Deterministic SPDX-2.3 JSON SBOM generator for KLine-Kronos-Suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha1_git_or_bytes(data: bytes) -> str:
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def generate_sbom(version: str, output_path: pathlib.Path) -> None:
    skip_dirs = {".git", "__pycache__", "dist", "artifacts", ".venv", "venv"}
    files_list = []
    idx = 0
    for fp in sorted(REPO_ROOT.rglob("*")):
        if any(part in skip_dirs for part in fp.parts) or not fp.is_file() or fp.is_symlink():
            continue
        if fp.resolve() == output_path.resolve():
            continue
        idx += 1
        raw = fp.read_bytes()
        rel = fp.relative_to(REPO_ROOT).as_posix()
        files_list.append(
            {
                "SPDXID": f"SPDXRef-File-{idx}",
                "fileName": f"./{rel}",
                "checksums": [
                    {"algorithm": "SHA256", "checksumValue": sha256_bytes(raw)},
                    {"algorithm": "SHA1", "checksumValue": sha1_git_or_bytes(raw)},
                ],
                "licenseConcluded": "MIT",
                "copyrightText": "2026 Ziqi and KLine-Kronos-Suite Contributors",
            }
        )

    doc = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"kline-kronos-suite-{version}",
        "documentNamespace": f"https://github.com/Ziqi/KLine-Kronos-Suite/spdx/{version}",
        "creationInfo": {
            "created": "2026-11-14T00:00:00Z",
            "creators": ["Person: Ziqi", "Tool: kline-kronos-sbom-1.0"],
            "licenseListVersion": "3.25",
        },
        "packages": [
            {
                "SPDXID": "SPDXRef-Package-kline-kronos-suite",
                "name": "kline-kronos-suite",
                "versionInfo": version,
                "downloadLocation": "https://github.com/Ziqi/KLine-Kronos-Suite",
                "filesAnalyzed": True,
                "licenseConcluded": "MIT",
                "licenseDeclared": "MIT",
                "copyrightText": "2026 Ziqi and KLine-Kronos-Suite Contributors",
                "hasFiles": [f["SPDXID"] for f in files_list],
            }
        ],
        "files": files_list,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-Package-kline-kronos-suite",
            }
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] [SPDX-SBOM] Generated {output_path} ({len(files_list)} files indexed, SPDX-2.3).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1.1.0")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    generate_sbom(args.version, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
