"""Strict multi-chain RNA validation, concatenation and pooling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import torch
import torch.nn.functional as F

from .rinalmo_model import EMBEDDING_DIM, validate_rna_sequence


FIXED_LENGTH = 128
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class RNAChain:
    chain_id: str
    sequence: str
    direction: str = "5to3"


def validate_identifier(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError("{} must be a string.".format(label))
    value = value.strip()
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(
            "{} may contain only letters, digits, '.', '_' and '-', and must "
            "start with a letter or digit.".format(label)
        )
    return value


def parse_chain_argument(value: str) -> RNAChain:
    if "=" not in value:
        raise ValueError(
            "Invalid RNA chain argument {!r}; expected RNA_1=ACGU.".format(value)
        )
    chain_id, sequence = value.split("=", 1)
    return RNAChain(chain_id=chain_id, sequence=sequence)


def split_chain_sequences(value: str) -> List[str]:
    """Split the dataset ``na_seq`` field on ``|`` and validate every chain."""

    if not isinstance(value, str):
        raise TypeError("na_seq must be a non-empty string.")
    raw_chains = value.split("|")
    if any(not item.strip() for item in raw_chains):
        raise ValueError("na_seq contains an empty RNA chain around '|'.")
    return [validate_rna_sequence(item) for item in raw_chains]


def validate_chains(chains: Sequence[RNAChain]) -> List[RNAChain]:
    if not chains:
        raise ValueError("At least one 5-to-3 RNA chain is required.")
    validated: List[RNAChain] = []
    seen_ids = set()
    for chain in chains:
        chain_id = validate_identifier(chain.chain_id, "RNA chain ID")
        if chain_id in seen_ids:
            raise ValueError("Duplicate RNA chain ID: {}".format(chain_id))
        seen_ids.add(chain_id)
        if chain.direction != "5to3":
            raise ValueError(
                "RNA chain {} must be supplied in the 5-to-3 direction.".format(
                    chain_id
                )
            )
        validated.append(
            RNAChain(
                chain_id=chain_id,
                sequence=validate_rna_sequence(chain.sequence),
            )
        )
    return validated


def choose_mode(requested_mode: str, chain_count: int) -> str:
    """Retain the CLI option while enforcing the only supported method."""

    if chain_count < 1:
        raise ValueError("At least one RNA chain is required.")
    requested_mode = requested_mode.lower()
    if requested_mode not in {
        "auto",
        "training_compatible",
        "independent_chains",
    }:
        raise ValueError(
            "RNA mode must be auto, training_compatible or independent_chains."
        )
    return "independent_chains"


def validate_embedding(
    label: str,
    embedding: torch.Tensor,
    expected_length: int = None,
) -> None:
    if not isinstance(embedding, torch.Tensor):
        raise TypeError("{} must be a torch.Tensor.".format(label))
    if embedding.ndim != 2 or embedding.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            "{} must have shape [L, {}], got {}.".format(
                label, EMBEDDING_DIM, tuple(embedding.shape)
            )
        )
    if embedding.shape[0] < 1:
        raise ValueError("{} has zero nucleotide rows.".format(label))
    if expected_length is not None and embedding.shape[0] != expected_length:
        raise ValueError(
            "{} length mismatch: expected {}, got {}.".format(
                label, expected_length, embedding.shape[0]
            )
        )
    if not torch.isfinite(embedding).all():
        raise ValueError("{} contains NaN or Inf.".format(label))


def concatenate_chain_embeddings(
    sequences: Sequence[str], embeddings: Sequence[torch.Tensor]
) -> torch.Tensor:
    """Validate and concatenate only real nucleotide rows from all chains."""

    if len(sequences) != len(embeddings):
        raise ValueError(
            "RNA sequence/embedding count mismatch: {} vs {}.".format(
                len(sequences), len(embeddings)
            )
        )
    if not sequences:
        raise ValueError("At least one RNA chain embedding is required.")
    normalized = [validate_rna_sequence(sequence) for sequence in sequences]
    checked = []
    for index, (sequence, embedding) in enumerate(zip(normalized, embeddings), 1):
        validate_embedding(
            "RNA chain {}".format(index),
            embedding,
            expected_length=len(sequence),
        )
        checked.append(embedding.detach().cpu().to(torch.float32).contiguous())
    result = torch.cat(checked, dim=0)
    validate_embedding(
        "concatenated RNA",
        result,
        expected_length=sum(len(sequence) for sequence in normalized),
    )
    return result


def build_fixed_embedding(
    concatenated_embedding: torch.Tensor,
    max_length: int = FIXED_LENGTH,
) -> Tuple[torch.Tensor, torch.Tensor, List[str]]:
    """Sequentially truncate/right-pad an optional site tensor to 128 rows."""

    validate_embedding("concatenated RNA", concatenated_embedding)
    if max_length < 1:
        raise ValueError("max_length must be positive.")
    warnings: List[str] = []
    seq_len = concatenated_embedding.shape[0]
    if seq_len > max_length:
        fixed = concatenated_embedding[:max_length]
        warnings.append(
            "RNA total length {} exceeds {}; site_embedding was truncated. "
            "mean_pooling still uses all {} nucleotides.".format(
                seq_len, max_length, seq_len
            )
        )
    elif seq_len < max_length:
        fixed = F.pad(
            concatenated_embedding,
            (0, 0, 0, max_length - seq_len),
            mode="constant",
            value=0.0,
        )
    else:
        fixed = concatenated_embedding
    mask = torch.zeros(max_length, dtype=torch.bool)
    mask[: min(seq_len, max_length)] = True
    return fixed.contiguous(), mask, warnings


def mean_pool_embedding(concatenated_embedding: torch.Tensor) -> torch.Tensor:
    """Length-weighted mean over every real nucleotide across all RNA chains."""

    validate_embedding("concatenated RNA", concatenated_embedding)
    pooled = concatenated_embedding.mean(dim=0)
    if tuple(pooled.shape) != (EMBEDDING_DIM,):
        raise RuntimeError(
            "RNA mean-pooling shape mismatch: {}.".format(tuple(pooled.shape))
        )
    if not torch.isfinite(pooled).all():
        raise RuntimeError("RNA mean-pooling output contains NaN or Inf.")
    return pooled.contiguous()
