#!/usr/bin/env python3
"""ESM-2 3B features for one protein-RNA mutation sample."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import esm
import torch


STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
EMBEDDING_DIM = 2560
REPRESENTATION_LAYER = 36
MUTATION_PATTERN = re.compile(r"^([A-Z])([1-9]\d*)([A-Z])$")
SAMPLE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class Mutation:
    reference: str
    position: int
    alternate: str

    @property
    def label(self) -> str:
        return f"{self.reference}{self.position}{self.alternate}"


@dataclass(frozen=True)
class ESM2Result:
    sample_id: str
    mutation: Mutation
    sequence_length: int
    embedded_length: int
    device: str
    wild_type_embedding_path: Path
    mutant_embedding_path: Path
    site_feature_path: Path
    metadata_path: Path
    wt_site: torch.Tensor
    muta_site: torch.Tensor
    warnings: tuple[str, ...]


def validate_sample_id(sample_id: str) -> str:
    sample_id = sample_id.strip()
    if not SAMPLE_ID_PATTERN.fullmatch(sample_id):
        raise ValueError(
            "Sample_ID 只能包含英文字母、数字、点、下划线和连字符，"
            "并且必须以字母或数字开头。"
        )
    return sample_id


def validate_sequence(sequence: str) -> str:
    """Remove whitespace, convert to upper case, and validate residues."""
    sequence = re.sub(r"\s+", "", sequence).upper()
    if not sequence:
        raise ValueError("蛋白质序列不能为空。")

    invalid = [
        (position, residue)
        for position, residue in enumerate(sequence, start=1)
        if residue not in STANDARD_AMINO_ACIDS
    ]
    if invalid:
        details = ", ".join(
            f"{residue}@{position}" for position, residue in invalid[:10]
        )
        if len(invalid) > 10:
            details += f", ...（共 {len(invalid)} 处）"
        raise ValueError(
            "蛋白质序列含有非标准氨基酸；只允许20种标准氨基酸。"
            f"异常位置：{details}"
        )
    return sequence


def validate_mutation(mutation_text: str, sequence: str) -> Mutation:
    mutation_text = mutation_text.strip().upper()
    match = MUTATION_PATTERN.fullmatch(mutation_text)
    if match is None:
        raise ValueError("突变格式错误，应使用类似 A10V 的格式。")

    reference, position_text, alternate = match.groups()
    if reference not in STANDARD_AMINO_ACIDS:
        raise ValueError(f"参考氨基酸 {reference!r} 不是标准氨基酸。")
    if alternate not in STANDARD_AMINO_ACIDS:
        raise ValueError(f"目标氨基酸 {alternate!r} 不是标准氨基酸。")
    if reference == alternate:
        raise ValueError("参考氨基酸和目标氨基酸相同，不构成突变。")

    position = int(position_text)
    if position > len(sequence):
        raise ValueError(
            f"突变位置 {position} 超出序列长度 {len(sequence)}。"
        )
    actual = sequence[position - 1]
    if actual != reference:
        raise ValueError(
            f"突变 {mutation_text} 与输入序列不一致：序列第 {position} 位是 "
            f"{actual}，不是 {reference}。"
        )
    return Mutation(reference, position, alternate)


def validate_inputs(
    sample_id: str,
    sequence: str,
    mutation_text: str,
) -> tuple[str, str, Mutation]:
    sample_id = validate_sample_id(sample_id)
    sequence = validate_sequence(sequence)
    mutation = validate_mutation(mutation_text, sequence)
    return sample_id, sequence, mutation


def build_mutant_sequence(sequence: str, mutation: Mutation) -> str:
    index = mutation.position - 1
    return sequence[:index] + mutation.alternate + sequence[index + 1 :]


def output_paths(
    output_dir: Union[str, Path],
    sample_id: str,
    mutation: Mutation,
) -> tuple[Path, Path, Path, Path]:
    output_dir = Path(output_dir)
    return (
        output_dir / f"{sample_id}_wt_esm2_3b.pt",
        output_dir / f"{sample_id}_{mutation.label}_mutant_esm2_3b.pt",
        output_dir / "esm2_3b_site.pt",
        output_dir.parent / "protein_metadata.json",
    )


def ensure_outputs_available(
    paths: tuple[Path, Path, Path, Path], overwrite: bool
) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "输出文件已存在："
            + ", ".join(str(path) for path in existing)
            + "。如需覆盖，请添加 --overwrite。"
        )


class ESM2ThreeBEmbedder:
    """Load ESM-2 3B in FP32 and reuse it for WT/mutant inference."""

    def __init__(
        self,
        model_location: str = "esm2_t36_3B_UR50D",
        device: str = "cpu",
    ) -> None:
        self.model_location = model_location
        self.requested_device = torch.device(device)
        self.device_warnings: list[str] = []

        print(f"正在加载 ESM-2(3B)：{model_location}", file=sys.stderr)
        self.model, self.alphabet = esm.pretrained.load_model_and_alphabet(
            model_location
        )
        self.model.eval()
        self.batch_converter = self.alphabet.get_batch_converter()
        self.device = self._select_and_move_device(self.requested_device)

    def _select_and_move_device(self, requested: torch.device) -> torch.device:
        if requested.type != "cuda":
            self.model.to(requested)
            return requested

        if not torch.cuda.is_available():
            warning = "请求使用CUDA，但当前PyTorch无法使用CUDA；已回退到CPU FP32。"
            self.device_warnings.append(warning)
            print(f"警告：{warning}", file=sys.stderr)
            return torch.device("cpu")

        index = requested.index if requested.index is not None else 0
        cuda_device = torch.device(f"cuda:{index}")
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(cuda_device)
        except TypeError:
            with torch.cuda.device(cuda_device):
                free_bytes, total_bytes = torch.cuda.mem_get_info()

        parameter_bytes = sum(
            parameter.numel() * parameter.element_size()
            for parameter in self.model.parameters()
        )
        reserve_bytes = 1024**3
        required_bytes = parameter_bytes + reserve_bytes
        if free_bytes < required_bytes:
            warning = (
                f"{cuda_device} 可用显存 {free_bytes / 1024**3:.2f} GiB，"
                f"不足以容纳FP32模型参数及基本运行空间"
                f"（至少约 {required_bytes / 1024**3:.2f} GiB）；"
                "已回退到CPU FP32。"
            )
            self.device_warnings.append(warning)
            print(f"警告：{warning}", file=sys.stderr)
            return torch.device("cpu")

        try:
            self.model.to(cuda_device)
        except RuntimeError as error:
            self.model.to("cpu")
            torch.cuda.empty_cache()
            warning = (
                f"ESM-2(3B) 无法载入 {cuda_device}（{error}）；"
                "已回退到CPU FP32。"
            )
            self.device_warnings.append(warning)
            print(f"警告：{warning}", file=sys.stderr)
            return torch.device("cpu")
        return cuda_device

    def embed_sequence(self, label: str, sequence: str) -> torch.Tensor:
        _, _, tokens = self.batch_converter([(label, sequence)])
        tokens = tokens.to(self.device)
        with torch.inference_mode():
            output = self.model(
                tokens,
                repr_layers=[REPRESENTATION_LAYER],
                return_contacts=False,
            )

        # Index 0 is BOS/CLS. The slice contains residues only and excludes EOS.
        embeddings = output["representations"][REPRESENTATION_LAYER][
            0, 1 : len(sequence) + 1
        ].detach().to(device="cpu", dtype=torch.float32)
        expected_shape = (len(sequence), EMBEDDING_DIM)
        if tuple(embeddings.shape) != expected_shape:
            raise RuntimeError(
                f"ESM-2(3B) 输出维度异常：期望 {expected_shape}，"
                f"实际 {tuple(embeddings.shape)}。"
            )
        if not torch.isfinite(embeddings).all():
            raise RuntimeError("ESM-2(3B) 输出中含有 NaN 或 Inf。")
        return embeddings.contiguous()

    def run_wild_and_mutant(
        self,
        sample_id: str,
        wild_type_sequence: str,
        mutation_text: str,
        output_dir: Union[str, Path],
        overwrite: bool = False,
    ) -> ESM2Result:
        sample_id, wild_type_sequence, mutation = validate_inputs(
            sample_id, wild_type_sequence, mutation_text
        )
        warnings = list(self.device_warnings)

        paths = output_paths(output_dir, sample_id, mutation)
        ensure_outputs_available(paths, overwrite)
        mutant_sequence = build_mutant_sequence(wild_type_sequence, mutation)

        wt_embeddings = self.embed_sequence(sample_id + "_WT", wild_type_sequence)
        mutant_embeddings = self.embed_sequence(
            sample_id + "_" + mutation.label, mutant_sequence
        )
        site_index = mutation.position - 1
        wt_site = wt_embeddings[site_index].clone()
        muta_site = mutant_embeddings[site_index].clone()
        if tuple(wt_site.shape) != (EMBEDDING_DIM,) or tuple(
            muta_site.shape
        ) != (EMBEDDING_DIM,):
            raise RuntimeError("WT或突变型位点特征维度不是 (2560,)。")

        wt_path, mutant_path, site_path, metadata_path = paths
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(wt_embeddings, wt_path)
        torch.save(mutant_embeddings, mutant_path)
        torch.save(
            {
                sample_id: {
                    "wt_site": wt_site,
                    "muta_site": muta_site,
                }
            },
            site_path,
        )

        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "sample_id": sample_id,
            "model": self.model_location,
            "representation_layer": REPRESENTATION_LAYER,
            "embedding_dim": EMBEDDING_DIM,
            "requested_device": str(self.requested_device),
            "actual_device": str(self.device),
            "precision": "float32",
            "wild_type_sequence": wild_type_sequence,
            "mutant_sequence": mutant_sequence,
            "sequence_length": len(wild_type_sequence),
            "embedded_length": len(wild_type_sequence),
            "mutation": mutation.label,
            "mutation_position": mutation.position,
            "wild_type_embedding_shape": list(wt_embeddings.shape),
            "mutant_embedding_shape": list(mutant_embeddings.shape),
            "wt_site_shape": list(wt_site.shape),
            "muta_site_shape": list(muta_site.shape),
            "warnings": warnings,
        }
        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)

        return ESM2Result(
            sample_id=sample_id,
            mutation=mutation,
            sequence_length=len(wild_type_sequence),
            embedded_length=len(wild_type_sequence),
            device=str(self.device),
            wild_type_embedding_path=wt_path,
            mutant_embedding_path=mutant_path,
            site_feature_path=site_path,
            metadata_path=metadata_path,
            wt_site=wt_site,
            muta_site=muta_site,
            warnings=tuple(warnings),
        )
