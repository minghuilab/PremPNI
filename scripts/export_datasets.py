#!/usr/bin/env python3
"""Copy the approved workbooks unchanged and export their four dataset sheets.

Requires openpyxl for read-only extraction (not an inference dependency).
Run from the repository: python scripts/export_datasets.py
To import the approved originals, pass --source-dir /path/to/final/files.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASHES = {
    "S1336.xlsx": "3c4c27837ee0237c69bff06791ce1a6999cdf474f8f9bde4427a25f960ffee21",
    "S599.xlsx": "b149704f174c3a5f186fbb7ccc9c29cd5e57c0e2732e6119ec628f450e08137a",
    "S1664.xlsx": "fdcb22e4297c9cf44a1d9e371d0034bed16c2e8d4f6e08b6cf82cf3f01e9cb97",
    "S1150.xlsx": "24dd58d555ef98b34033163784b8950961a65dc60bffe4ab31cfc1214d6bd327",
    "Supplementary_Data_S1_10.10.xlsx": "dfd8cac8ecfe87467c231189c899590ca086104495464c9c606613820b7ddabb",
    "Supplementary_Data_S2_10.10.xlsx": "3c69cc1dfb3e7df005f8f315f02e7f2f245da1b92f601684680c3b7ef1081403",
    "Supplementary_Data_S3_10.10.xlsx": "83a3a0e073d2eb310fc2fc4d3e02195a5114b3aa37063d53e0b67e730ed31a03",
}
DATASETS = {"S1336": (1336, 29), "S599": (599, 22), "S1664": (1664, 4), "S1150": (1150, 4)}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "datasets")
    parser.add_argument("--output", type=Path, default=ROOT / "datasets")
    args = parser.parse_args()
    require(args.source_dir.resolve() != args.output.resolve() or args.output.resolve() == (ROOT / "datasets").resolve(),
            "Use a separate output directory to preserve the original source directory")
    report = {"version": "2026-10-13", "workbooks": {}, "datasets": {}}
    prepared = {}
    for filename, expected_hash in SOURCE_HASHES.items():
        content = (args.source_dir / filename).read_bytes()
        require(digest(content) == expected_hash, filename + ": unexpected source workbook version")
        prepared[filename] = content
        book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheets = {}
        try:
            for sheet in book:
                rows = list(sheet.values)
                if sheet.title == "README":
                    sheets[sheet.title] = {"description": rows[0][0]}
                    continue
                header = list(rows[0])
                sheets[sheet.title] = {"rows": len(rows) - 1, "columns": header}
                name = Path(filename).stem
                if name not in DATASETS or sheet.title != name:
                    continue
                count, columns = DATASETS[name]
                require(len(rows) == count + 1 and len(header) == columns, name + ": unexpected table dimensions")
                require(not any(cell.data_type == "f" for row in sheet for cell in row), name + ": formulas require an explicit export policy")
                if name == "S1150":
                    require("Record ID" not in header and "Mutant protein sequence" not in header,
                            "S1150: removed columns must not be restored")
                output = io.StringIO(newline="")
                csv.writer(output, delimiter="\t", lineterminator="\n").writerows(rows)
                tsv_name = name + ".tsv"
                prepared[tsv_name] = output.getvalue().encode("utf-8")
                report["datasets"][name] = {
                    "source_file": filename, "source_sheet": name, "rows": count,
                    "columns": header, "tsv_file": tsv_name, "tsv_sha256": digest(prepared[tsv_name]),
                }
        finally:
            book.close()
        report["workbooks"][filename] = {"sha256": expected_hash, "bytes": len(content), "sheets": sheets}
    require(set(report["datasets"]) == set(DATASETS), "Missing dataset worksheet")
    # Finish validation of every source before writing any output.
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, content in prepared.items():
        destination = args.output / filename
        if not destination.exists() or destination.read_bytes() != content:
            destination.write_bytes(content)
    (args.output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified 7 original workbooks and exported 4 dataset sheets without reordering or changing fields.")


if __name__ == "__main__":
    main()
