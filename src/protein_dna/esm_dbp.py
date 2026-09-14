#!/usr/bin/env python3
"""Validate a protein/mutation, run ESM-DBP, and extract one site vector."""

from __future__ import annotations

import argparse
import os
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Union

import esm
import numpy as np
import torch
from esm.model.esm2 import ESM2


STANDARD_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
EMBEDDING_DIM = 1280
MUTATION_PATTERN = re.compile(r"^([A-Z])([1-9]\d*)([A-Z])$")
PROTEIN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
RECOMMENDED_MAX_PROTEIN_LENGTH = 1280


@dataclass(frozen=True)
class Mutation:
    reference: str
    position: int
    alternate: str

    @property
    def label(self) -> str:
        return f"{self.reference}{self.position}{self.alternate}"


@dataclass(frozen=True)
class PipelineResult:
    protein_name: str
    sequence_length: int
    mutation: Mutation
    full_embedding_path: Path
    mutation_embedding_path: Path
    mutation_embedding: np.ndarray
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class WildMutantPipelineResult:
    sample_id: str
    protein_name: str
    sequence_length: int
    mutation: Mutation
    wild_type_embedding_path: Path
    mutant_embedding_path: Path
    site_feature_path: Path
    metadata_path: Path
    wt_site: torch.Tensor
    muta_site: torch.Tensor
    warnings: tuple[str, ...]


def protein_length_warnings(sequence: str) -> tuple[str, ...]:
    if len(sequence) <= RECOMMENDED_MAX_PROTEIN_LENGTH:
        return ()
    return (
        f"Protein length {len(sequence)} exceeds the recommended training length "
        f"{RECOMMENDED_MAX_PROTEIN_LENGTH}; continuing computation.",
    )


def validate_protein_name(protein_name: str) -> str:
    protein_name = protein_name.strip()
    if not PROTEIN_NAME_PATTERN.fullmatch(protein_name):
        raise ValueError(
            "Protein names may contain only ASCII letters, digits, dots, underscores and hyphens, "
            "and must start with a letter or digit."
        )
    return protein_name


def validate_sequence(sequence: str) -> str:
    """Normalize case/whitespace and require the 20 standard amino acids."""
    sequence = re.sub(r"\s+", "", sequence).upper()
    if not sequence:
        raise ValueError("Protein sequence must not be empty.")

    invalid_positions = [
        (index, residue)
        for index, residue in enumerate(sequence, start=1)
        if residue not in STANDARD_AMINO_ACIDS
    ]
    if invalid_positions:
        details = ", ".join(
            f"{residue}@{position}"
            for position, residue in invalid_positions[:10]
        )
        if len(invalid_positions) > 10:
            details += f", ... ({len(invalid_positions)} positions total)"
        raise ValueError(
            "Protein sequence contains nonstandard amino acids; allowed residues: "
            f"{''.join(sorted(STANDARD_AMINO_ACIDS))}. Invalid positions: {details}"
        )
    return sequence


def validate_mutation(mutation_text: str, sequence: str) -> Mutation:
    mutation_text = mutation_text.strip().upper()
    match = MUTATION_PATTERN.fullmatch(mutation_text)
    if match is None:
        raise ValueError("Invalid mutation format; use a substitution such as A10V.")

    reference, position_text, alternate = match.groups()
    if reference not in STANDARD_AMINO_ACIDS:
        raise ValueError(f"Reference residue {reference!r} is not a standard amino acid.")
    if alternate not in STANDARD_AMINO_ACIDS:
        raise ValueError(f"Alternate residue {alternate!r} is not a standard amino acid.")
    if reference == alternate:
        raise ValueError("Reference and alternate residues are identical; no substitution is specified.")

    position = int(position_text)
    if position > len(sequence):
        raise ValueError(
            f"Mutation position {position} exceeds sequence length {len(sequence)}."
        )

    sequence_residue = sequence[position - 1]
    if sequence_residue != reference:
        raise ValueError(
            f"Mutation {mutation_text} does not match the input sequence: position {position} contains "
            f"{sequence_residue}, not {reference}."
        )
    return Mutation(reference, position, alternate)


def validate_inputs(
    protein_name: str, sequence: str, mutation_text: str
) -> tuple[str, str, Mutation]:
    protein_name = validate_protein_name(protein_name)
    sequence = validate_sequence(sequence)
    mutation = validate_mutation(mutation_text, sequence)
    return protein_name, sequence, mutation


def output_paths(
    output_dir: Union[str, Path], protein_name: str, mutation: Mutation
) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    return (
        output_dir / f"{protein_name}.fea",
        output_dir / f"{protein_name}_{mutation.label}_embedding.csv",
    )


def build_mutant_sequence(sequence: str, mutation: Mutation) -> str:
    """Apply one validated substitution to the wild-type sequence."""
    index = mutation.position - 1
    return sequence[:index] + mutation.alternate + sequence[index + 1 :]


def wild_mutant_output_paths(
    output_dir: Union[str, Path], protein_name: str, mutation: Mutation
) -> tuple[Path, Path, Path, Path]:
    output_dir = Path(output_dir)
    return (
        output_dir / f"{protein_name}_wt.fea",
        output_dir / f"{protein_name}_{mutation.label}_mutant.fea",
        output_dir / "esmdbp_site.pt",
        output_dir.parent / "protein_metadata.json",
    )


def ensure_wild_mutant_outputs_available(
    paths: tuple[Path, Path, Path, Path], overwrite: bool
) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Output files already exist: "
            + ", ".join(str(path) for path in existing)
            + ". Use --overwrite to replace existing files."
        )


def ensure_outputs_available(
    full_path: Path, mutation_path: Path, overwrite: bool
) -> None:
    existing = [path for path in (full_path, mutation_path) if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            f"Output files already exist: {joined}. Use --overwrite to replace existing files."
        )


class ESMDBPEmbedder:
    """Load ESM-DBP once and reuse it for one or more protein requests."""

    def __init__(self, model_dir: Union[str, Path], device: str = "cpu") -> None:
        self.model_dir = Path(model_dir)
        self.device = torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but CUDA is unavailable in this PyTorch environment.")

        checkpoint_path = self.model_dir / "ESM-DBP.model"
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"ESM-DBP checkpoint not found: {checkpoint_path}")

        self.alphabet = esm.data.Alphabet.from_architecture("ESM-1b")
        self.batch_converter = self.alphabet.get_batch_converter()
        self.model = ESM2(
            num_layers=33,
            embed_dim=EMBEDDING_DIM,
            attention_heads=20,
            alphabet=self.alphabet,
        )

        state_dict: Dict[str, torch.Tensor] = torch.load(
            checkpoint_path,
            map_location="cpu",
        )
        state_dict = {
            key[7:] if key.startswith("module.") else key: value
            for key, value in state_dict.items()
        }
        self.model.load_state_dict(state_dict)
        del state_dict

        self.model.to(self.device)
        self.model.eval()

    def embed_sequence(self, protein_name: str, sequence: str) -> np.ndarray:
        _, _, batch_tokens = self.batch_converter([(protein_name, sequence)])
        batch_tokens = batch_tokens.to(self.device)

        with torch.inference_mode():
            result = self.model(
                batch_tokens,
                repr_layers=[33],
                return_contacts=False,
            )

        residue_embeddings = result["representations"][33][
            0, 1 : len(sequence) + 1
        ]
        embeddings = residue_embeddings.detach().cpu().numpy().astype(
            np.float32,
            copy=False,
        )
        expected_shape = (len(sequence), EMBEDDING_DIM)
        if embeddings.shape != expected_shape:
            raise RuntimeError(
                f"Unexpected ESM-DBP output shape: expected {expected_shape}, got "
                f"{embeddings.shape}."
            )
        if not np.isfinite(embeddings).all():
            raise RuntimeError("ESM-DBP output contains NaN or Inf.")
        return embeddings

    def run(
        self,
        protein_name: str,
        sequence: str,
        mutation_text: str,
        output_dir: Union[str, Path],
        overwrite: bool = False,
    ) -> PipelineResult:
        protein_name, sequence, mutation = validate_inputs(
            protein_name, sequence, mutation_text
        )
        warnings = protein_length_warnings(sequence)
        full_path, mutation_path = output_paths(
            output_dir, protein_name, mutation
        )
        ensure_outputs_available(full_path, mutation_path, overwrite)

        embeddings = self.embed_sequence(protein_name, sequence)
        mutation_embedding = embeddings[mutation.position - 1].copy()

        full_path.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(full_path, embeddings, delimiter=" ", fmt="%.10f")
        np.savetxt(
            mutation_path,
            mutation_embedding.reshape(1, -1),
            delimiter=",",
            fmt="%.10f",
        )
        return PipelineResult(
            protein_name=protein_name,
            sequence_length=len(sequence),
            mutation=mutation,
            full_embedding_path=full_path,
            mutation_embedding_path=mutation_path,
            mutation_embedding=mutation_embedding,
            warnings=warnings,
        )

    def run_wild_and_mutant(
        self,
        sample_id: str,
        protein_name: str,
        wild_type_sequence: str,
        mutation_text: str,
        output_dir: Union[str, Path],
        overwrite: bool = False,
    ) -> WildMutantPipelineResult:
        """Compute WT/mutant embeddings and save both site vectors."""
        sample_id = validate_protein_name(sample_id)
        protein_name, wild_type_sequence, mutation = validate_inputs(
            protein_name,
            wild_type_sequence,
            mutation_text,
        )
        mutant_sequence = build_mutant_sequence(wild_type_sequence, mutation)
        paths = wild_mutant_output_paths(output_dir, protein_name, mutation)
        ensure_wild_mutant_outputs_available(paths, overwrite)
        warnings = protein_length_warnings(wild_type_sequence)

        wild_type_embeddings = self.embed_sequence(
            protein_name + "_WT",
            wild_type_sequence,
        )
        mutant_embeddings = self.embed_sequence(
            protein_name + "_" + mutation.label,
            mutant_sequence,
        )
        site_index = mutation.position - 1
        wt_site = torch.from_numpy(
            wild_type_embeddings[site_index].copy()
        ).to(torch.float32)
        muta_site = torch.from_numpy(
            mutant_embeddings[site_index].copy()
        ).to(torch.float32)
        if tuple(wt_site.shape) != (EMBEDDING_DIM,) or tuple(
            muta_site.shape
        ) != (EMBEDDING_DIM,):
            raise RuntimeError(
                "Unexpected wild-type or mutant site feature shape; both must be (1280,)."
            )

        wild_path, mutant_path, site_path, metadata_path = paths
        wild_path.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(wild_path, wild_type_embeddings, delimiter=" ", fmt="%.10f")
        np.savetxt(mutant_path, mutant_embeddings, delimiter=" ", fmt="%.10f")
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
            "protein_name": protein_name,
            "wild_type_sequence": wild_type_sequence,
            "mutant_sequence": mutant_sequence,
            "sequence_length": len(wild_type_sequence),
            "mutation": mutation.label,
            "mutation_position": mutation.position,
            "wild_type_residue": mutation.reference,
            "mutant_residue": mutation.alternate,
            "wild_type_embedding_shape": list(wild_type_embeddings.shape),
            "mutant_embedding_shape": list(mutant_embeddings.shape),
            "wt_site_shape": list(wt_site.shape),
            "muta_site_shape": list(muta_site.shape),
            "warnings": list(warnings),
        }
        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)

        return WildMutantPipelineResult(
            sample_id=sample_id,
            protein_name=protein_name,
            sequence_length=len(wild_type_sequence),
            mutation=mutation,
            wild_type_embedding_path=wild_path,
            mutant_embedding_path=mutant_path,
            site_feature_path=site_path,
            metadata_path=metadata_path,
            wt_site=wt_site,
            muta_site=muta_site,
            warnings=warnings,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the protein sequence and mutation, compute full ESM-DBP embeddings, and extract the mutation site's "
            "1280-dimensional features."
        )
    )
    parser.add_argument("--name", required=True, help="Protein name")
    parser.add_argument("--sequence", required=True, help="Protein amino acid sequence")
    parser.add_argument("--mutation", required=True, help="Mutation, for example A10V")
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models") + "/esm_dbp",
        help="Directory containing ESM-DBP.model",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("PREMPNI_OUTPUT_ROOT", "/output") + "/protein_dna",
        help="Output directory",
    )
    parser.add_argument("--device", default="cpu", help="cpu, cuda or cuda:0")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing output files",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        protein_name, sequence, mutation = validate_inputs(
            args.name, args.sequence, args.mutation
        )
        full_path, mutation_path = output_paths(
            args.output_dir, protein_name, mutation
        )
        ensure_outputs_available(
            full_path, mutation_path, args.overwrite
        )

        embedder = ESMDBPEmbedder(args.model_dir, args.device)
        result = embedder.run(
            protein_name=protein_name,
            sequence=sequence,
            mutation_text=mutation.label,
            output_dir=args.output_dir,
            overwrite=args.overwrite,
        )
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as error:
        parser.exit(2, f"Error: {error}\n")

    print(f"Protein: {result.protein_name}")
    print(f"Sequence length: {result.sequence_length}")
    print(f"Mutation: {result.mutation.label}")
    print(f"Full embeddings: {result.full_embedding_path}")
    print(
        "Mutation site features: "
        f"{result.mutation_embedding_path}, shape "
        f"{result.mutation_embedding.shape}"
    )
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
