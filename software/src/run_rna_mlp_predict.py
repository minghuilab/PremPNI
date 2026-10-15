#!/usr/bin/env python3
"""Predict one Protein-RNA mutation with the three final F-F RNA-MLPs."""

import argparse
import csv
import json
import os
from pathlib import Path

from protein_rna.mlp_predictor import ProteinRNAMLPEnsemble, load_sample_features
from protein_rna.rinalmo_processing import validate_identifier


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run Seed21/trial3, Seed22/trial9 and Seed32/trial11, then report "
            "their ddG predictions and arithmetic ensemble mean."
        )
    )
    parser.add_argument("--sample-id", required=True)
    parser.add_argument(
        "--feature-root",
        default=os.environ.get("PREMPNI_OUTPUT_ROOT", "/output") + "/protein_rna",
    )
    parser.add_argument(
        "--model-root",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/mlp/protein_rna",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main():
    parser = build_parser(); args = parser.parse_args()
    try:
        sample_id = validate_identifier(args.sample_id, "Sample_ID")
        job_dir = Path(args.feature_root) / sample_id
        embedding_dir = job_dir / "embeddings"
        protein_path = embedding_dir / "esm2_3b_site.pt"
        rna_path = embedding_dir / "rinalmo_features.pt"
        if not rna_path.exists():
            rna_path = embedding_dir / "rinalmo_mean.pt"
        prediction_dir = job_dir / "prediction"
        json_path = prediction_dir / "mlp_ensemble_prediction.json"
        csv_path = prediction_dir / "mlp_ensemble_prediction.csv"
        existing = [path for path in (json_path, csv_path) if path.exists()]
        if existing and not args.overwrite:
            raise FileExistsError(
                "Prediction output exists: {}. Use --overwrite.".format(
                    ", ".join(map(str, existing))
                )
            )
        wt_site, muta_site, rna_mean = load_sample_features(
            sample_id, protein_path, rna_path
        )
        result = ProteinRNAMLPEnsemble(args.model_root, args.device).predict(
            sample_id, wt_site, muta_site, rna_mean
        )
        prediction_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "sample_id": result.sample_id,
            "model_predictions": result.model_predictions,
            "mean_ddg": result.mean_ddg,
            "classification": result.classification,
            "classification_rule": {
                "destabilizing mutation": "predicted ddG >= 0",
                "stabilizing mutation": "predicted ddG < 0",
            },
        }
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        row = {"sample_id": result.sample_id, **result.model_predictions,
               "mean_ddg": result.mean_ddg, "classification": result.classification}
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader(); writer.writerow(row)
    except (ValueError, TypeError, KeyError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, "ERROR: {}\n".format(error))
    print("Sample_ID: {}".format(result.sample_id))
    for model_name, value in result.model_predictions.items():
        print("{} ddG: {:.6f}".format(model_name, value))
    print("Ensemble mean ddG: {:.6f}".format(result.mean_ddg))
    print("Classification: {}".format(result.classification))
    print("JSON: {}".format(json_path)); print("CSV: {}".format(csv_path))


if __name__ == "__main__":
    main()
