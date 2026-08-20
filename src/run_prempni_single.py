#!/usr/bin/env python3
"""End-to-end single-sample PremPNI prediction for Protein-DNA or Protein-RNA.

The JSON and CSV result include input lengths and wall-clock timings for each
stage.  Timings include loading the model weights, so they are suitable for
reporting the cost of one independent command-line prediction.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import time
from pathlib import Path

import torch


APP_ROOT = Path(os.environ.get("PREMPNI_HOME", Path(__file__).resolve().parent))
MODEL_ROOT = Path(os.environ.get("PREMPNI_MODEL_ROOT", APP_ROOT / "models"))
OUTPUT_ROOT = Path(os.environ.get("PREMPNI_OUTPUT_ROOT", "/output"))
DNA_OUTPUT_ROOT = str(OUTPUT_ROOT / "protein_dna")
RNA_OUTPUT_ROOT = str(OUTPUT_ROOT / "protein_rna")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run one complete PremPNI Protein-DNA or Protein-RNA prediction."
    )
    parser.add_argument("--complex-type", required=True, choices=("dna", "rna"))
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--protein-sequence", required=True)
    parser.add_argument(
        "--mutation", required=True,
        help="One-based amino-acid substitution, for example A10V.",
    )
    parser.add_argument(
        "--chain", action="append", required=True,
        help="Repeat for each 5'-to-3' nucleic-acid chain, e.g. DNA_1=ACGT or RNA_1=ACGU.",
    )
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--protein-device", default=os.environ.get("PREMPNI_PROTEIN_DEVICE", "cuda:0"))
    parser.add_argument("--na-device", default=os.environ.get("PREMPNI_NA_DEVICE", "cuda:0"))
    parser.add_argument("--mlp-device", default=os.environ.get("PREMPNI_MLP_DEVICE", "auto"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--esmdbp-model-dir", default=str(MODEL_ROOT / "esm_dbp"))
    parser.add_argument("--hyenadna-checkpoint-root", default=str(MODEL_ROOT / "hyenadna"))
    parser.add_argument("--dna-mlp-model-root", default=str(MODEL_ROOT / "mlp" / "protein_dna"))
    parser.add_argument(
        "--esm2-model-location",
        default=str(MODEL_ROOT / "esm2" / "esm2_t36_3B_UR50D.pt"),
    )
    parser.add_argument(
        "--rinalmo-checkpoint",
        default=str(MODEL_ROOT / "rinalmo" / "rinalmo_giga_pretrained.pt"),
    )
    parser.add_argument("--rna-mlp-model-root", default=str(MODEL_ROOT / "mlp" / "protein_rna"))
    return parser.parse_args()


def sync_cuda():
    if torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            try:
                torch.cuda.synchronize(index)
            except RuntimeError:
                pass


def release(model):
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def write_result(job_dir, payload, overwrite):
    prediction_dir = Path(job_dir) / "prediction"
    json_path = prediction_dir / "prempni_prediction.json"
    csv_path = prediction_dir / "prempni_prediction.csv"
    if (json_path.exists() or csv_path.exists()) and not overwrite:
        raise FileExistsError("Prediction output already exists. Use --overwrite: {}".format(prediction_dir))
    prediction_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    timing = payload["timing_seconds"]
    row = {
        "sample_id": payload["sample_id"],
        "complex_type": payload["complex_type"],
        "protein_length": payload["input_lengths"]["protein_length"],
        "nucleic_acid_chain_count": payload["input_lengths"]["nucleic_acid_chain_count"],
        "nucleic_acid_total_length": payload["input_lengths"]["nucleic_acid_total_length"],
        "mean_ddg": payload["mean_ddg"],
        "classification": payload["classification"],
        "protein_embedding_seconds": timing["protein_embedding"],
        "nucleic_acid_embedding_seconds": timing["nucleic_acid_embedding"],
        "mlp_prediction_seconds": timing["mlp_prediction"],
        "total_seconds": timing["total"],
    }
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return json_path, csv_path


def run_dna(args):
    from protein_dna.esm_dbp import ESMDBPEmbedder, validate_inputs
    from protein_dna.mlp_predictor import ProteinDNAMLPEnsemble
    from protein_dna.pipeline import HyenaDNAPipeline
    from protein_dna.processing import parse_chain_argument, validate_chains, validate_identifier

    sample_id = validate_identifier(args.sample_id, "Sample_ID")
    _, protein_sequence, mutation = validate_inputs(sample_id, args.protein_sequence, args.mutation)
    chains = validate_chains([parse_chain_argument(value) for value in args.chain])
    output_root = Path(args.output_root or DNA_OUTPUT_ROOT)
    embedding_dir = output_root / sample_id / "embeddings"
    total_start = time.perf_counter()

    sync_cuda(); start = time.perf_counter()
    protein_embedder = ESMDBPEmbedder(args.esmdbp_model_dir, args.protein_device)
    protein_result = protein_embedder.run_wild_and_mutant(
        sample_id, sample_id, protein_sequence, mutation.label, embedding_dir, args.overwrite
    )
    sync_cuda(); protein_seconds = time.perf_counter() - start
    wt_site, muta_site = protein_result.wt_site, protein_result.muta_site
    release(protein_embedder)

    sync_cuda(); start = time.perf_counter()
    na_pipeline = HyenaDNAPipeline(args.hyenadna_checkpoint_root, args.na_device)
    na_result = na_pipeline.run(sample_id, chains, output_root, overwrite=args.overwrite)
    sync_cuda(); na_seconds = time.perf_counter() - start
    dna_mean = torch.load(na_result.mean_embedding_path, map_location="cpu")[sample_id]
    release(na_pipeline)

    sync_cuda(); start = time.perf_counter()
    ensemble = ProteinDNAMLPEnsemble(args.dna_mlp_model_root, args.mlp_device)
    prediction = ensemble.predict(sample_id, wt_site, muta_site, dna_mean)
    sync_cuda(); mlp_seconds = time.perf_counter() - start
    release(ensemble)
    return output_root / sample_id, prediction, protein_seconds, na_seconds, mlp_seconds, protein_sequence, chains, total_start


def run_rna(args):
    from protein_rna.esm2_3b import ESM2ThreeBEmbedder, validate_inputs
    from protein_rna.mlp_predictor import ProteinRNAMLPEnsemble
    from protein_rna.rinalmo_pipeline import RiNALMoPipeline
    from protein_rna.rinalmo_processing import parse_chain_argument, validate_chains, validate_identifier

    sample_id = validate_identifier(args.sample_id, "Sample_ID")
    _, protein_sequence, mutation = validate_inputs(sample_id, args.protein_sequence, args.mutation)
    chains = validate_chains([parse_chain_argument(value) for value in args.chain])
    output_root = Path(args.output_root or RNA_OUTPUT_ROOT)
    embedding_dir = output_root / sample_id / "embeddings"
    total_start = time.perf_counter()

    sync_cuda(); start = time.perf_counter()
    protein_embedder = ESM2ThreeBEmbedder(args.esm2_model_location, args.protein_device)
    protein_result = protein_embedder.run_wild_and_mutant(
        sample_id, protein_sequence, mutation.label, embedding_dir, args.overwrite
    )
    sync_cuda(); protein_seconds = time.perf_counter() - start
    wt_site, muta_site = protein_result.wt_site, protein_result.muta_site
    release(protein_embedder)

    sync_cuda(); start = time.perf_counter()
    na_pipeline = RiNALMoPipeline(args.rinalmo_checkpoint, args.na_device)
    na_result = na_pipeline.run(sample_id, chains, output_root, overwrite=args.overwrite)
    sync_cuda(); na_seconds = time.perf_counter() - start
    rna_mean = torch.load(na_result.mean_embedding_path, map_location="cpu")[sample_id]
    release(na_pipeline)

    sync_cuda(); start = time.perf_counter()
    ensemble = ProteinRNAMLPEnsemble(args.rna_mlp_model_root, args.mlp_device)
    prediction = ensemble.predict(sample_id, wt_site, muta_site, rna_mean)
    sync_cuda(); mlp_seconds = time.perf_counter() - start
    release(ensemble)
    return output_root / sample_id, prediction, protein_seconds, na_seconds, mlp_seconds, protein_sequence, chains, total_start


def main():
    args = parse_args()
    try:
        if args.complex_type == "dna":
            values = run_dna(args)
            nucleic_acid_name = "DNA"
        else:
            values = run_rna(args)
            nucleic_acid_name = "RNA"
        job_dir, prediction, protein_seconds, na_seconds, mlp_seconds, protein_sequence, chains, total_start = values
        total_seconds = time.perf_counter() - total_start
        payload = {
            "sample_id": prediction.sample_id,
            "complex_type": args.complex_type,
            "input_lengths": {
                "protein_length": len(protein_sequence),
                "nucleic_acid_type": nucleic_acid_name,
                "nucleic_acid_chain_count": len(chains),
                "nucleic_acid_chain_lengths": {chain.chain_id: len(chain.sequence) for chain in chains},
                "nucleic_acid_total_length": sum(len(chain.sequence) for chain in chains),
            },
            "mean_ddg": prediction.mean_ddg,
            "classification": prediction.classification,
            "classification_rule": "mean_ddg >= 0: destabilizing mutation; mean_ddg < 0: stabilizing mutation",
            "timing_seconds": {
                "protein_embedding": protein_seconds,
                "nucleic_acid_embedding": na_seconds,
                "mlp_prediction": mlp_seconds,
                "total": total_seconds,
                "definition": "Wall-clock time for this independent command; each stage includes model loading, inference, and feature-output writing.",
            },
        }
        json_path, csv_path = write_result(job_dir, payload, args.overwrite)
    except (ValueError, TypeError, KeyError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        raise SystemExit("ERROR: {}".format(error))

    print("Sample_ID: {}".format(payload["sample_id"]))
    print("Protein length: {}; nucleic-acid total length: {}".format(
        payload["input_lengths"]["protein_length"],
        payload["input_lengths"]["nucleic_acid_total_length"]
    ))
    print("Ensemble mean ddG: {:.6f}".format(payload["mean_ddg"]))
    print("Timing (s): protein={:.3f}, nucleic-acid={:.3f}, MLP={:.3f}, total={:.3f}".format(
        payload["timing_seconds"]["protein_embedding"], payload["timing_seconds"]["nucleic_acid_embedding"],
        payload["timing_seconds"]["mlp_prediction"], payload["timing_seconds"]["total"]
    ))
    print("JSON: {}".format(json_path)); print("CSV: {}".format(csv_path))


if __name__ == "__main__":
    main()
