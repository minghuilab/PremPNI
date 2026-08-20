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
            "验证蛋白质序列和单点突变，分别计算野生型和突变型的"
            "ESM-2(3B)特征，并提取两个2560维突变位点向量。"
        )
    )
    parser.add_argument("--sample-id", required=True, help="样本唯一ID")
    parser.add_argument("--sequence", required=True, help="野生型蛋白质序列")
    parser.add_argument("--mutation", required=True, help="突变，例如 A10V")
    parser.add_argument(
        "--model-location",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/esm2/esm2_t36_3B_UR50D.pt",
        help="fair-esm模型名或本地模型文件路径",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="默认cpu；若指定cuda且FP32显存不足，会自动回退到cpu",
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
        parser.exit(2, f"错误：{error}\n")

    print(f"Sample_ID：{result.sample_id}")
    print(f"突变：{result.mutation.label}")
    print(f"原始/实际计算长度：{result.sequence_length}/{result.embedded_length}")
    print(f"实际设备与精度：{result.device} / float32")
    print(f"野生型完整特征：{result.wild_type_embedding_path}")
    print(f"突变型完整特征：{result.mutant_embedding_path}")
    print(f"位点特征字典：{result.site_feature_path}")
    print(f"wt_site维度：{tuple(result.wt_site.shape)}")
    print(f"muta_site维度：{tuple(result.muta_site.shape)}")
    for warning in result.warnings:
        print(f"警告：{warning}")


if __name__ == "__main__":
    main()
