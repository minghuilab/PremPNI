#!/usr/bin/env python3
"""Verify that the Docker build contains exactly the expected model assets."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    checked = 0
    for line_number, raw_line in enumerate(
        args.manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            expected, relative_name = line.split(None, 1)
        except ValueError:
            errors.append(f"Malformed manifest line {line_number}: {raw_line}")
            continue
        path = args.root / relative_name.strip().lstrip("*")
        if not path.is_file():
            errors.append(f"Missing model asset: {relative_name}")
            continue
        actual = sha256(path)
        if actual != expected:
            errors.append(
                f"Checksum mismatch for {relative_name}: {actual} != {expected}"
            )
        checked += 1

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Verified {checked} PremPNI model assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
