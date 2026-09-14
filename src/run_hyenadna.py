#!/usr/bin/env python3
"""Command-line entry point for the PremPNI HyenaDNA pipeline."""

import argparse
import os

from protein_dna.pipeline import HyenaDNAPipeline, ensure_outputs_available, result_paths
from protein_dna.processing import (
    choose_mode,
    parse_chain_argument,
    validate_chains,
    validate_identifier,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compute HyenaDNA embeddings for one or more 5′→3′ DNA chains; generate per-chain, fixed-length "
            "and mean-pooled embeddings."
        )
    )
    parser.add_argument("--sample-id", required=True, help="Unique sample ID")
    parser.add_argument(
        "--chain",
        action="append",
        required=True,
        help="DNA chain as DNA_1=AGCT; repeat this option for multiple chains",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "compatible", "experimental"],
        default="auto",
        help="auto: compatible with one or two chains; experimental mode for three or more chains",
    )
    parser.add_argument(
        "--checkpoint-root",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/hyenadna",
    )
    parser.add_argument("--device", default="cuda:0", help="For example 1, cuda:1 or cpu")
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
        sample_id = validate_identifier(args.sample_id, "Sample_ID")
        chains = validate_chains([parse_chain_argument(value) for value in args.chain])
        choose_mode(args.mode, len(chains))
        paths = result_paths(args.output_root, sample_id)
        ensure_outputs_available(paths, args.overwrite)

        pipeline = HyenaDNAPipeline(args.checkpoint_root, args.device)
        result = pipeline.run(
            sample_id=sample_id,
            chains=chains,
            output_root=args.output_root,
            mode=args.mode,
            overwrite=args.overwrite,
        )
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Sample_ID: {result.sample_id}")
    print(f"Processing mode: {result.mode}")
    print(f"Per-chain embeddings: {result.chain_embeddings_path}")
    print(f"Fixed-length embeddings: {result.fixed_embedding_path}")
    print(f"Fixed-length mask: {result.fixed_mask_path}")
    print(f"Mean-pooled embeddings: {result.mean_embedding_path}")
    print(f"Training-compatible embeddings: {result.combined_embedding_path}")
    print(f"Metadata: {result.metadata_path}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
