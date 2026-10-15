#!/usr/bin/env python3
"""Predict Protein-DNA mutation ΔΔG with the three final F-F MLPs."""

import argparse
import csv
import json
import os
from pathlib import Path

from protein_dna.mlp_predictor import (
    ProteinDNAMLPEnsemble,
    load_sample_features,
)
from protein_dna.processing import validate_identifier


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Load the three F-F MLPs (Seed46/trial8, Seed66/trial0 and Seed77/trial4), "
            "and report their DDG predictions, mean and stability classification."
        )
    )
    parser.add_argument("--sample-id", required=True, help="Unique sample ID")
    parser.add_argument(
        "--feature-root",
        default=os.environ.get("PREMPNI_OUTPUT_ROOT", "/output") + "/protein_dna",
    )
    parser.add_argument(
        "--model-root",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/mlp/protein_dna",
    )
    parser.add_argument("--device", default="cpu", help="cpu, cuda or cuda:0")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        sample_id = validate_identifier(args.sample_id, "Sample_ID")
        job_dir = Path(args.feature_root) / sample_id
        embedding_dir = job_dir / "embeddings"
        protein_path = embedding_dir / "esmdbp_site.pt"
        dna_path = embedding_dir / "hyenadna_features.pt"
        if not dna_path.exists():
            dna_path = embedding_dir / "hyenadna_mean.pt"

        prediction_dir = job_dir / "prediction"
        json_path = prediction_dir / "mlp_ensemble_prediction.json"
        csv_path = prediction_dir / "mlp_ensemble_prediction.csv"
        existing = [path for path in (json_path, csv_path) if path.exists()]
        if existing and not args.overwrite:
            raise FileExistsError(
                "Prediction files already exist: "
                + ", ".join(str(path) for path in existing)
                + ". Use --overwrite to replace existing files."
            )

        wt_site, muta_site, dna_mean = load_sample_features(
            sample_id,
            protein_path,
            dna_path,
        )
        ensemble = ProteinDNAMLPEnsemble(args.model_root, args.device)
        result = ensemble.predict(sample_id, wt_site, muta_site, dna_mean)

        prediction_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "sample_id": result.sample_id,
            "model_predictions": result.model_predictions,
            "mean_ddg": result.mean_ddg,
            "classification": result.classification,
            "classification_rule": {
                "destabilizing mutation": "predicted ΔΔG >= 0",
                "stabilizing mutation": "predicted ΔΔG < 0",
            },
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

        row = {
            "sample_id": result.sample_id,
            **result.model_predictions,
            "mean_ddg": result.mean_ddg,
            "classification": result.classification,
        }
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
    except (ValueError, KeyError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Sample_ID: {result.sample_id}")
    for model_name, value in result.model_predictions.items():
        print(f"{model_name} ΔΔG: {value:.6f}")
    print(f"Three-model mean DDG: {result.mean_ddg:.6f}")
    print(f"Classification: {result.classification}")
    print(f"JSON results: {json_path}")
    print(f"CSV results: {csv_path}")


if __name__ == "__main__":
    main()
