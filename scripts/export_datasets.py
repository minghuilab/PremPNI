#!/usr/bin/env python3
"""Export the author-designated curated workbook without altering scientific values.

Requires openpyxl (data preparation only, not an inference dependency).
Run from the repository: python scripts/export_datasets.py
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "23efe7455ea7085d9d913f66cae6df04a292398dea1a53991b482ad4e7791248"
SCHEMAS = {
    "S1664": ["Mutation", "Protein_sequence", "Nucleic_acid_sequence", "DDG"],
    "S1150": ["Mutation", "Protein_sequence", "Nucleic_acid_sequence", "DDG"],
    "S1336": ["PDB_mutation", "DDG", "PremPDI2_prediction"],
    "S599": ["PDB_mutation", "DDG", "PremPRI2_prediction"],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "datasets/PremPNI_curated_datasets.xlsx")
    parser.add_argument("--output", type=Path, default=ROOT / "datasets")
    args = parser.parse_args()
    require(digest(args.source) == SOURCE_SHA256, "Unexpected source workbook version")
    book = openpyxl.load_workbook(args.source, read_only=True, data_only=False)
    require(set(book.sheetnames) == set(SCHEMAS), "Unexpected worksheet set")
    report = {"version": "2026-09-09", "source_file": "PremPNI_curated_datasets.xlsx", "source_sha256": SOURCE_SHA256, "datasets": {}}
    prepared = {}
    for name, schema in SCHEMAS.items():
        values = list(book[name].values)
        header, rows = list(values[0]), values[1:]
        require(header == schema, name + ": unexpected columns")
        require(len(rows) == int(name[1:]), name + ": unexpected record count")
        records = [dict(zip(header, row)) for row in rows]
        require(not any(isinstance(v, str) and v.startswith("=") for row in rows for v in row), name + ": unexpected formula")
        for record in records:
            for key in (k for k in header if k == "DDG" or k.endswith("_prediction")):
                require(isinstance(record[key], (int, float)) and math.isfinite(record[key]), name + ": missing/nonfinite " + key)
            if "Mutation" in record:
                mutation = re.fullmatch(r"([ACDEFGHIKLMNPQRSTVWY])([1-9][0-9]*)([ACDEFGHIKLMNPQRSTVWY])", record["Mutation"])
                require(mutation is not None, name + ": malformed mutation")
                wt, position, _ = mutation.groups()
                protein = record["Protein_sequence"]
                require(bool(protein) and set(protein) <= set("ACDEFGHIKLMNPQRSTVWY"), name + ": invalid protein")
                require(int(position) <= len(protein) and protein[int(position)-1] == wt, name + ": sequence position mismatch")
                chains = record["Nucleic_acid_sequence"].split("|")
                alphabet = set("ACGT" if name == "S1664" else "ACGU")
                require(all(c and set(c) <= alphabet for c in chains), name + ": invalid nucleic-acid sequence")
        if "PDB_mutation" in header:
            require(len({r["PDB_mutation"] for r in records}) == len(records), name + ": duplicate mutation identifier")
        report["datasets"][name] = {"rows": len(rows), "columns": header}
        prepared[name] = (header, rows)
    book.close()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, (header, rows) in prepared.items():
        path = args.output / (name + ".tsv")
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
        report["datasets"][name]["sha256"] = digest(path)
    (args.output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: value["rows"] for name, value in report["datasets"].items()}))


if __name__ == "__main__":
    main()
