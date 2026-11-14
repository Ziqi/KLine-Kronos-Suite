#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Ziqi and KLine-Kronos-Suite Contributors
# SPDX-License-Identifier: MIT
"""Bit-for-bit deterministic PAX source archive builder & verifier (Python 3.10+ stdlib only)."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import pathlib
import sys
import tarfile

DEFAULT_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "artifacts",
    "dist",
    "build",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "gui_out_5m",
    "data",
    "outputs",
    "kronos_runtime",
}
SKIP_FILES = {".DS_Store"}


def build_reproducible_tarball_bytes(
    repo_root: pathlib.Path,
    prefix: str = "kline-kronos-suite",
    exclude_paths: set[pathlib.Path] | None = None,
) -> tuple[bytes, int]:
    excluded = exclude_paths or set()
    entries: list[tuple[str, pathlib.Path]] = []
    for root, dirs, files in os.walk(repo_root, followlinks=False):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in SKIP_DIRS and not d.endswith(".egg-info") and not d.startswith("dist_")
        )
        rp = pathlib.Path(root)
        for name in sorted(files):
            if name in SKIP_FILES or name.endswith((".pyc", ".pyo")):
                continue
            fp = rp / name
            if fp.resolve() in excluded:
                continue
            rel = fp.relative_to(repo_root).as_posix()
            entries.append((rel, fp))
        for dname in list(dirs):
            dp = rp / dname
            if dp.is_symlink():
                rel = dp.relative_to(repo_root).as_posix()
                entries.append((rel, dp))
                dirs.remove(dname)

    entries.sort(key=lambda item: item[0])
    clean_prefix = prefix.strip("/") or "kline-kronos-suite"
    raw_buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw_buf, compresslevel=9, mtime=0) as gz:
        with tarfile.open(mode="w", fileobj=gz, format=tarfile.PAX_FORMAT) as tf:
            for rel, fp in entries:
                arcname = f"{clean_prefix}/{rel}"
                ti = tarfile.TarInfo(name=arcname)
                ti.mtime = 0
                ti.uid = 0
                ti.gid = 0
                ti.uname = ""
                ti.gname = ""
                ti.pax_headers = {}
                if fp.is_symlink():
                    ti.type = tarfile.SYMTYPE
                    ti.linkname = os.readlink(fp)
                    ti.mode = 0o777
                    tf.addfile(ti)
                elif fp.is_file():
                    data = fp.read_bytes()
                    ti.type = tarfile.REGTYPE
                    ti.size = len(data)
                    ti.mode = 0o755 if os.access(fp, os.X_OK) else 0o644
                    tf.addfile(ti, io.BytesIO(data))
    return raw_buf.getvalue(), len(entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build or verify a bit-for-bit reproducible source tarball for KLine-Kronos-Suite"
    )
    parser.add_argument("--repo-root", type=pathlib.Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--output", type=pathlib.Path, help="Write deterministic .tar.gz to this path")
    parser.add_argument("--prefix", default="kline-kronos-suite", help="Top-level directory prefix inside tarball")
    parser.add_argument("--verify", action="store_true", help="Verify bit-for-bit determinism across independent builds")
    parser.add_argument("--verify-file", type=pathlib.Path, help="Verify an existing .tar.gz against current source tree")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    excluded = {p.resolve() for p in (args.output, args.verify_file) if p is not None}
    bytes_a, file_count = build_reproducible_tarball_bytes(repo_root, args.prefix, excluded)
    sha_a = hashlib.sha256(bytes_a).hexdigest()

    if args.verify_file is not None:
        if not args.verify_file.is_file():
            print(f"[FAIL] [REPRODUCIBLE-BUILD] Archive not found: {args.verify_file}", file=sys.stderr)
            return 1
        actual_sha = hashlib.sha256(args.verify_file.read_bytes()).hexdigest()
        if actual_sha != sha_a:
            print(
                f"[FAIL] [REPRODUCIBLE-BUILD] Digest mismatch for {args.verify_file}: expected {sha_a}, got {actual_sha}",
                file=sys.stderr,
            )
            return 1
        print(
            f"[PASS] [REPRODUCIBLE-BUILD] {args.verify_file} matches source tree bit-for-bit (sha256={sha_a}, files={file_count})."
        )
        return 0

    bytes_b, _ = build_reproducible_tarball_bytes(repo_root, args.prefix, excluded)
    sha_b = hashlib.sha256(bytes_b).hexdigest()
    if bytes_a != bytes_b or sha_a != sha_b:
        print("[FAIL] [REPRODUCIBLE-BUILD] Non-deterministic archive output detected!", file=sys.stderr)
        return 1

    if args.output is not None:
        out_path = args.output.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(bytes_a)
        print(
            f"[PASS] [REPRODUCIBLE-BUILD] Wrote deterministic archive {out_path} (sha256={sha_a}, files={file_count}, mtime=0, uid/gid=0)."
        )
        return 0

    print(
        f"[PASS] [REPRODUCIBLE-BUILD] Bit-for-bit deterministic archive verified (sha256={sha_a}, files={file_count}, mtime=0, uid/gid=0)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
