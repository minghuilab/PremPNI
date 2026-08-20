#!/usr/bin/env python3
"""Compute independent-chain RiNALMo features for one website sample."""

import argparse
import os

from protein_rna.rinalmo_model import DEFAULT_CHECKPOINT
from protein_rna.rinalmo_pipeline import (
    RiNALMoPipeline,
    ensure_outputs_available,
    result_paths,
)
from protein_rna.rinalmo_processing import (
    choose_mode,
    parse_chain_argument,
    validate_chains,
    validate_identifier,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Embed each 5-to-3 RNA chain independently with RiNALMo, remove "
            "each chain's CLS/EOS tokens, concatenate real nucleotides, and "
            "mean-pool across the full concatenation."
        )
    )
    parser.add_argument("--sample-id", required=True, help="Unique Sample_ID")
    parser.add_argument(
        "--chain",
        action="append",
        required=True,
        help="RNA_1=ACGU; repeat --chain for multiple RNA chains",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "training_compatible", "independent_chains"],
        default="auto",
        help="All choices resolve to independent_chains for compatibility.",
    )
    parser.add_argument("--device", default="cuda:1", help="cpu, cuda:0, cuda:1")
    parser.add_argument(
        "--checkpoint",
        default=str(DEFAULT_CHECKPOINT),
        help="Path to the RiNALMo giga-v1 checkpoint",
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
        sample_id = validate_identifier(args.sample_id, "Sample_ID")
        chains = validate_chains(
            [parse_chain_argument(value) for value in args.chain]
        )
        choose_mode(args.mode, len(chains))
        paths = result_paths(args.output_root, sample_id)
        ensure_outputs_available(paths, args.overwrite)

        pipeline = RiNALMoPipeline(args.checkpoint, args.device)
        result = pipeline.run(
            sample_id=sample_id,
            chains=chains,
            output_root=args.output_root,
            mode=args.mode,
            overwrite=args.overwrite,
        )
    except (ValueError, TypeError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, "ERROR: {}\n".format(error))

    print("Sample_ID: {}".format(result.sample_id))
    print("Processing mode: {}".format(result.mode))
    print("Per-chain embeddings: {}".format(result.chain_embeddings_path))
    print("Concatenated embedding: {}".format(result.joint_embedding_path))
    print("Site embedding: {}".format(result.fixed_embedding_path))
    print("Site mask: {}".format(result.fixed_mask_path))
    print("Full-length mean embedding: {}".format(result.mean_embedding_path))
    print("MLP-compatible features: {}".format(result.combined_embedding_path))
    print("Metadata: {}".format(result.metadata_path))
    for warning in result.warnings:
        print("WARNING: {}".format(warning))


if __name__ == "__main__":
    main()
