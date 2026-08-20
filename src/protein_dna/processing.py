"""Strict validation and training-compatible HyenaDNA post-processing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import torch
import torch.nn.functional as F


DNA_ALPHABET = frozenset("ACGT")
CHAIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
HYENADNA_DIM = 256
FIXED_LENGTH = 128


@dataclass(frozen=True)
class DNAChain:
    chain_id: str
    sequence: str
    direction: str = "5to3"


def validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError("{} must be a string.".format(label))
    value = value.strip()
    if not CHAIN_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "{} may contain only letters, digits, '.', '_' and '-', and must "
            "start with a letter or digit.".format(label)
        )
    return value


def validate_dna_sequence(sequence: str, chain_id: str = "DNA") -> str:
    if not isinstance(sequence, str):
        raise TypeError("DNA chain {} must be a string.".format(chain_id))
    sequence = re.sub(r"\s+", "", sequence).upper()
    if not sequence:
        raise ValueError("DNA chain {} cannot be empty.".format(chain_id))
    invalid = [
        (position, base)
        for position, base in enumerate(sequence, start=1)
        if base not in DNA_ALPHABET
    ]
    if invalid:
        details = ", ".join(
            "{}@{}".format(base, position) for position, base in invalid[:10]
        )
        raise ValueError(
            "DNA chain {} may contain only A/C/G/T/N; invalid bases: {}."
            .format(chain_id, details)
        )
    return sequence


def split_chain_sequences(value: str) -> List[str]:
    if not isinstance(value, str):
        raise TypeError("na_seq must be a string.")
    parts = value.split("|")
    if any(not part.strip() for part in parts):
        raise ValueError("na_seq contains an empty chain around '|'.")
    return [
        validate_dna_sequence(sequence, "DNA_{}".format(index))
        for index, sequence in enumerate(parts, start=1)
    ]


def validate_chains(chains: Sequence[DNAChain]) -> List[DNAChain]:
    if not chains:
        raise ValueError("At least one 5-to-3 DNA chain is required.")
    validated, seen_ids = [], set()
    for chain in chains:
        chain_id = validate_identifier(chain.chain_id, "DNA chain ID")
        if chain_id in seen_ids:
            raise ValueError("Duplicate DNA chain ID: {}".format(chain_id))
        seen_ids.add(chain_id)
        if chain.direction != "5to3":
            raise ValueError(
                "DNA chain {} must be supplied in the 5-to-3 direction.".format(
                    chain_id
                )
            )
        validated.append(
            DNAChain(chain_id, validate_dna_sequence(chain.sequence, chain_id))
        )
    return validated


def parse_chain_argument(value: str) -> DNAChain:
    if "=" not in value:
        raise ValueError(
            "Invalid DNA chain argument {!r}; expected DNA_1=ACGT.".format(value)
        )
    chain_id, sequence = value.split("=", 1)
    return DNAChain(chain_id, sequence)


def choose_mode(requested_mode: str, chain_count: int) -> str:
    """Preserve old CLI values while enforcing the S1345 training method."""

    if chain_count < 1:
        raise ValueError("At least one DNA chain is required.")
    if requested_mode.lower() not in {
        "auto", "compatible", "experimental", "training_compatible"
    }:
        raise ValueError("Unknown DNA processing mode: {}".format(requested_mode))
    return "training_compatible"


def validate_embedding(
    chain_id: str, embedding: torch.Tensor, expected_length: int = None
) -> None:
    if not isinstance(embedding, torch.Tensor):
        raise TypeError("DNA chain {} embedding must be a tensor.".format(chain_id))
    if embedding.ndim != 2 or embedding.shape[1] != HYENADNA_DIM:
        raise ValueError(
            "DNA chain {} must have shape [L, {}], got {}.".format(
                chain_id, HYENADNA_DIM, tuple(embedding.shape)
            )
        )
    if embedding.shape[0] < 1:
        raise ValueError("DNA chain {} has zero embedding rows.".format(chain_id))
    if expected_length is not None and embedding.shape[0] != expected_length:
        raise ValueError(
            "DNA chain {} length mismatch: expected {}, got {}.".format(
                chain_id, expected_length, embedding.shape[0]
            )
        )
    if not torch.isfinite(embedding).all():
        raise ValueError("DNA chain {} contains NaN or Inf.".format(chain_id))


def concatenate_embeddings(
    sequences: Sequence[str], embeddings: Sequence[torch.Tensor]
) -> torch.Tensor:
    if len(sequences) != len(embeddings) or not sequences:
        raise ValueError("DNA sequence/embedding counts must match and be non-zero.")
    checked = []
    for index, (sequence, embedding) in enumerate(zip(sequences, embeddings), 1):
        normalized = validate_dna_sequence(sequence, "DNA_{}".format(index))
        validate_embedding(
            "DNA_{}".format(index), embedding, expected_length=len(normalized)
        )
        checked.append(embedding.detach().cpu().to(torch.float32).contiguous())
    return torch.cat(checked, dim=0).contiguous()


def build_fixed_from_concatenated(
    concatenated: torch.Tensor, max_length: int = FIXED_LENGTH
) -> Tuple[torch.Tensor, torch.Tensor, List[str]]:
    validate_embedding("concatenated", concatenated)
    sequence_length = concatenated.shape[0]
    warnings: List[str] = []
    if sequence_length > max_length:
        fixed = concatenated[:max_length]
        warnings.append(
            "DNA total length {} exceeds {}; site_embedding was truncated. "
            "mean_pooling still uses all {} bases.".format(
                sequence_length, max_length, sequence_length
            )
        )
    elif sequence_length < max_length:
        fixed = F.pad(concatenated, (0, 0, 0, max_length - sequence_length))
    else:
        fixed = concatenated
    mask = torch.zeros(max_length, dtype=torch.bool)
    mask[: min(sequence_length, max_length)] = True
    return fixed.contiguous(), mask, warnings


def build_fixed_embedding(
    chain_embeddings: Dict[str, torch.Tensor],
    mode: str = "training_compatible",
    max_length: int = FIXED_LENGTH,
) -> Tuple[torch.Tensor, torch.Tensor, List[str]]:
    if not chain_embeddings:
        raise ValueError("No DNA chain embeddings were provided.")
    choose_mode(mode, len(chain_embeddings))
    for chain_id, embedding in chain_embeddings.items():
        validate_embedding(chain_id, embedding)
    concatenated = torch.cat(list(chain_embeddings.values()), dim=0)
    return build_fixed_from_concatenated(concatenated, max_length)


def mean_pool_embeddings(chain_embeddings: Dict[str, torch.Tensor]) -> torch.Tensor:
    """Length-weighted mean over all real bases in all DNA chains."""

    if not chain_embeddings:
        raise ValueError("No DNA chain embeddings were provided.")
    for chain_id, embedding in chain_embeddings.items():
        validate_embedding(chain_id, embedding)
    pooled = torch.cat(list(chain_embeddings.values()), dim=0).mean(dim=0)
    if tuple(pooled.shape) != (HYENADNA_DIM,) or not torch.isfinite(pooled).all():
        raise RuntimeError("HyenaDNA mean_pooling is invalid.")
    return pooled.contiguous()
