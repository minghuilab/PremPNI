#!/usr/bin/env python3
"""Batch PremPNI runner for the validated S1345 (DNA) and S604 (RNA) schemas.

Feature stages run in separate child processes so large GPU models are released
between stages.  The timing JSON reports total batch wall time and a clearly
labelled average per sample, rather than pretending that batch throughput is an
individual-sample latency.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description="Run a validated PremPNI batch pipeline.")
    parser.add_argument("--complex-type", required=True, choices=("dna", "rna"))
    parser.add_argument("--dataset", required=True, help="Tab-separated S1345 (DNA) or S604 (RNA) dataset.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--stage", default="all", choices=("all", "features", "predict"))
    parser.add_argument("--protein-features", default=None)
    parser.add_argument("--na-features", default=None)
    parser.add_argument("--protein-device", default="cuda:0")
    parser.add_argument("--na-device", default="cuda:1")
    parser.add_argument("--mlp-device", default="auto")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def run(command):
    print("Running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def option(command, flag, value):
    if value is not None:
        command.extend((flag, str(value)))


def main():
    args = parse_args()
    dataset = Path(args.dataset)
    if not dataset.is_file():
        raise SystemExit("ERROR: Dataset not found: {}".format(dataset))
    frame = pd.read_csv(dataset, sep="\t")
    if "sample_ID" not in frame or frame["sample_ID"].isna().any():
        raise SystemExit("ERROR: dataset needs a non-empty sample_ID column.")
    if "na_seq" not in frame:
        raise SystemExit("ERROR: dataset needs a na_seq column.")
    output = Path(args.output_root); features = output / "features"; prediction = output / "prediction"
    output.mkdir(parents=True, exist_ok=True)
    elapsed = {}; total_start = time.perf_counter()
    python = sys.executable

    try:
        if args.complex_type == "dna":
            if args.stage in ("all", "features"):
                start = time.perf_counter()
                cmd = [python, "run_esm_dbp_s1345.py", "--dataset", str(dataset), "--output", str(features / "ESMDBP_SiteAll.pt"), "--partial", str(features / "ESMDBP_SiteAll.partial.pt"), "--device", args.protein_device]
                if args.resume: cmd.append("--resume")
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["protein_embedding"] = time.perf_counter() - start
                start = time.perf_counter()
                cmd = [python, "run_hyenadna_s1345.py", "--dataset", str(dataset), "--output", str(features / "HyenaDNA_SiteMean.pt"), "--sequence-cache", str(features / "HyenaDNA_sequence_cache.pt"), "--device", args.na_device]
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["nucleic_acid_embedding"] = time.perf_counter() - start
            protein = Path(args.protein_features) if args.protein_features else features / "ESMDBP_SiteAll.pt"
            nucleic = Path(args.na_features) if args.na_features else features / "HyenaDNA_SiteMean.pt"
            if args.stage in ("all", "predict"):
                start = time.perf_counter()
                cmd = [python, "run_dna_mlp_s1345.py", "--dataset", str(dataset), "--protein-features", str(protein), "--dna-features", str(nucleic), "--output-root", str(prediction), "--device", args.mlp_device, "--batch-size", str(args.batch_size)]
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["mlp_prediction"] = time.perf_counter() - start
        else:
            if args.stage in ("all", "features"):
                start = time.perf_counter()
                cmd = [python, "run_esm2_3b_s604.py", "--dataset", str(dataset), "--output", str(features / "ESM2_3B_SiteAll.pt"), "--partial", str(features / "ESM2_3B_SiteAll.partial.pt"), "--device", args.protein_device]
                if args.resume: cmd.append("--resume")
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["protein_embedding"] = time.perf_counter() - start
                start = time.perf_counter()
                cmd = [python, "run_rinalmo_s604.py", "--dataset", str(dataset), "--output", str(features / "RiNALMo_SiteMean.pt"), "--sequence-cache", str(features / "RiNALMo_sequence_cache.pt"), "--device", args.na_device]
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["nucleic_acid_embedding"] = time.perf_counter() - start
            protein = Path(args.protein_features) if args.protein_features else features / "ESM2_3B_SiteAll.pt"
            nucleic = Path(args.na_features) if args.na_features else features / "RiNALMo_SiteMean.pt"
            if args.stage in ("all", "predict"):
                start = time.perf_counter()
                cmd = [python, "run_rna_mlp_s604.py", "--dataset", str(dataset), "--protein-features", str(protein), "--rna-features", str(nucleic), "--output-root", str(prediction), "--device", args.mlp_device, "--batch-size", str(args.batch_size)]
                if args.overwrite: cmd.append("--overwrite")
                run(cmd); elapsed["mlp_prediction"] = time.perf_counter() - start
    except subprocess.CalledProcessError as error:
        raise SystemExit("ERROR: stage failed with exit code {}.".format(error.returncode))

    total = time.perf_counter() - total_start
    chains = frame["na_seq"].astype(str).map(lambda value: len(value.split("|")))
    lengths = frame["na_seq"].astype(str).map(lambda value: sum(len(part.strip()) for part in value.split("|")))
    payload = {
        "complex_type": args.complex_type,
        "dataset": str(dataset),
        "sample_count": int(len(frame)),
        "input_lengths": {"mean_nucleic_acid_total_length": float(lengths.mean()), "max_nucleic_acid_total_length": int(lengths.max()), "mean_chain_count": float(chains.mean())},
        "timing_seconds": {**elapsed, "total": total, "mean_wall_seconds_per_sample": total / len(frame), "definition": "Batch wall time divided by number of samples; it is throughput, not independent single-sample latency."},
    }
    timing_path = output / "batch_timing.json"
    timing_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Batch timing: {}".format(timing_path))
    print("Samples: {}; total seconds: {:.3f}; mean wall seconds/sample: {:.3f}".format(len(frame), total, total / len(frame)))


if __name__ == "__main__":
    main()
