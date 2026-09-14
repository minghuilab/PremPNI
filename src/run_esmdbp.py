#!/usr/bin/env python3
"""Compute wild-type and mutant ESM-DBP protein features for one sample."""

import argparse
import os
from pathlib import Path

from protein_dna.esm_dbp import (
    ESMDBPEmbedder,
    ensure_wild_mutant_outputs_available,
    validate_inputs,
    validate_protein_name,
    wild_mutant_output_paths,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute full ESM-DBP embeddings for wild-type and mutant proteins and extract "
            "two 1280-dimensional vectors at the mutation site."
        )
    )
    parser.add_argument("--sample-id", required=True, help="Unique sample ID")
    parser.add_argument("--sequence", required=True, help="Wild-type protein sequence")
    parser.add_argument("--mutation", required=True, help="Mutation, for example A10V")
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/esm_dbp",
    )
    parser.add_argument("--device", default="cpu", help="cpu, cuda or cuda:0")
    parser.add_argument(
        "--output-root",
        default=os.environ.get("PREMPNI_OUTPUT_ROOT", "/output") + "/protein_dna",
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        sample_id = validate_protein_name(args.sample_id)
        protein_name, sequence, mutation = validate_inputs(
            sample_id,
            args.sequence,
            args.mutation,
        )
        embedding_dir = Path(args.output_root) / sample_id / "embeddings"
        paths = wild_mutant_output_paths(
            embedding_dir,
            protein_name,
            mutation,
        )
        ensure_wild_mutant_outputs_available(paths, args.overwrite)

        embedder = ESMDBPEmbedder(args.model_dir, args.device)
        result = embedder.run_wild_and_mutant(
            sample_id=sample_id,
            protein_name=sample_id,
            wild_type_sequence=sequence,
            mutation_text=mutation.label,
            output_dir=embedding_dir,
            overwrite=args.overwrite,
        )
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Sample_ID: {result.sample_id}")
    print(f"Protein: {result.protein_name}")
    print(f"Mutation: {result.mutation.label}")
    print(f"Wild-type full embeddings: {result.wild_type_embedding_path}")
    print(f"Mutant full embeddings: {result.mutant_embedding_path}")
    print(f"Site feature dictionary: {result.site_feature_path}")
    print(f"wt_site shape: {tuple(result.wt_site.shape)}")
    print(f"muta_site shape: {tuple(result.muta_site.shape)}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
