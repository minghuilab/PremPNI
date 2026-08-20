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
            "计算一条或多条5′→3′ DNA链的HyenaDNA特征；生成逐链、固定长度"
            "和平均池化特征。"
        )
    )
    parser.add_argument("--sample-id", required=True, help="样本唯一ID")
    parser.add_argument(
        "--chain",
        action="append",
        required=True,
        help="DNA链，格式为 DNA_1=AGCT；多条链重复使用该参数",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "compatible", "experimental"],
        default="auto",
        help="auto：1/2链兼容，3链以上实验模式",
    )
    parser.add_argument(
        "--checkpoint-root",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/hyenadna",
    )
    parser.add_argument("--device", default="cuda:0", help="例如1、cuda:1或cpu")
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
        parser.exit(2, f"错误：{error}\n")

    print(f"Sample_ID：{result.sample_id}")
    print(f"处理模式：{result.mode}")
    print(f"逐链特征：{result.chain_embeddings_path}")
    print(f"固定长度特征：{result.fixed_embedding_path}")
    print(f"固定长度mask：{result.fixed_mask_path}")
    print(f"平均池化特征：{result.mean_embedding_path}")
    print(f"训练兼容特征：{result.combined_embedding_path}")
    print(f"元数据：{result.metadata_path}")
    for warning in result.warnings:
        print(f"警告：{warning}")


if __name__ == "__main__":
    main()
