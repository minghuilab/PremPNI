#!/usr/bin/env python3
"""Compute WT and mutant ESM-2(3B) features for one protein-RNA sample."""

import argparse
import os
from pathlib import Path

from protein_rna.esm2_3b import (
    ESM2ThreeBEmbedder,
    ensure_outputs_available,
    output_paths,
    validate_inputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the protein sequence and single-site mutation, compute wild-type and mutant "
            "ESM-2(3B) embeddings, and extract two 2560-dimensional mutation site vectors."
        )
    )
    parser.add_argument("--sample-id", required=True, help="Unique sample ID")
    parser.add_argument("--sequence", required=True, help="Wild-type protein sequence")
    parser.add_argument("--mutation", required=True, help="Mutation, for example A10V")
    parser.add_argument(
        "--model-location",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/esm2/esm2_t36_3B_UR50D.pt",
        help="fair-esm model name or local model file path",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Default: cpu; CUDA falls back to CPU if FP32 GPU memory is insufficient",
    )
    parser.add_argument(
        "--output-root",
        default=os.environ.get("PREMPNI_OUTPUT_ROOT", "/output") + "/protein_rna",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        sample_id, sequence, mutation = validate_inputs(
            args.sample_id, args.sequence, args.mutation
        )
        embedding_dir = Path(args.output_root) / sample_id / "embeddings"
        paths = output_paths(embedding_dir, sample_id, mutation)
        ensure_outputs_available(paths, args.overwrite)

        embedder = ESM2ThreeBEmbedder(
            model_location=args.model_location,
            device=args.device,
        )
        result = embedder.run_wild_and_mutant(
            sample_id=sample_id,
            wild_type_sequence=sequence,
            mutation_text=mutation.label,
            output_dir=embedding_dir,
            overwrite=args.overwrite,
        )
    except (
        ValueError,
        FileNotFoundError,
        FileExistsError,
        RuntimeError,
        KeyError,
    ) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Sample_ID: {result.sample_id}")
    print(f"Mutation: {result.mutation.label}")
    print(f"Original/embedded length: {result.sequence_length}/{result.embedded_length}")
    print(f"Actual device and precision: {result.device} / float32")
    print(f"Wild-type full embeddings: {result.wild_type_embedding_path}")
    print(f"Mutant full embeddings: {result.mutant_embedding_path}")
    print(f"Site feature dictionary: {result.site_feature_path}")
    print(f"wt_site shape: {tuple(result.wt_site.shape)}")
    print(f"muta_site shape: {tuple(result.muta_site.shape)}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
