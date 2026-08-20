#!/usr/bin/env python3
"""RiNALMo giga-v1 loading and strict per-chain RNA inference."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Sequence, Union

import torch


VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from rinalmo.data.alphabet import Alphabet  # noqa: E402
from rinalmo.data.constants import (  # noqa: E402
    CLS_TKN,
    EOS_TKN,
    MASK_TKN,
    PAD_TKN,
    RNA_TOKENS,
)
from rinalmo.model.model import RiNALMo  # noqa: E402


EMBEDDING_DIM = 1280
STANDARD_RNA_BASES = frozenset("ACGU")
DEFAULT_CHECKPOINT = Path(
    os.environ.get(
        "RINALMO_CHECKPOINT",
        str(
            Path(os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models"))
            / "rinalmo" / "rinalmo_giga_pretrained.pt"
        ),
    )
)


class AttrDict(dict):
    """Dictionary with attribute access used by the upstream model classes."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name, value):
        self[name] = value


def nested_attr_dict(value):
    if isinstance(value, dict):
        return AttrDict({key: nested_attr_dict(item) for key, item in value.items()})
    return value


def giga_config() -> AttrDict:
    alphabet = Alphabet(
        standard_tkns=RNA_TOKENS,
        special_tkns=[CLS_TKN, PAD_TKN, EOS_TKN, "<unk>", MASK_TKN],
    )
    return nested_attr_dict(
        {
            "alphabet": {
                "standard_tkns": RNA_TOKENS,
                "special_tkns": [
                    CLS_TKN,
                    PAD_TKN,
                    EOS_TKN,
                    "<unk>",
                    MASK_TKN,
                ],
            },
            "model": {
                "embedding": {
                    "num_embeddings": len(alphabet),
                    "embedding_dim": EMBEDDING_DIM,
                    "padding_idx": alphabet.pad_idx,
                },
                "token_dropout": {
                    "active": True,
                    "mask_ratio": 0.15,
                    "mask_tkn_prob": 0.8,
                    "mask_tkn_idx": alphabet.mask_idx,
                    "pad_tkn_idx": alphabet.pad_idx,
                },
                "transformer": {
                    "embed_dim": EMBEDDING_DIM,
                    "num_blocks": 33,
                    "num_heads": 20,
                    "use_rot_emb": True,
                    "attn_qkv_bias": False,
                    "attention_dropout": 0.1,
                    "transition_dropout": 0.0,
                    "residual_dropout": 0.1,
                    "transition_factor": 4,
                    "use_flash_attn": True,
                },
                "lm_mask_head": {
                    "embed_dim": EMBEDDING_DIM,
                    "alphabet_size": len(alphabet),
                },
            },
        }
    )


def validate_rna_sequence(sequence: str) -> str:
    if not isinstance(sequence, str):
        raise TypeError("RNA sequence must be a string.")
    sequence = re.sub(r"\s+", "", sequence).upper()
    if not sequence:
        raise ValueError("RNA sequence cannot be empty.")
    invalid = [
        (position, base)
        for position, base in enumerate(sequence, start=1)
        if base not in STANDARD_RNA_BASES
    ]
    if invalid:
        details = ", ".join(
            "{}@{}".format(base, position) for position, base in invalid[:10]
        )
        raise ValueError(
            "RNA sequence may contain only A, C, G and U; invalid bases: "
            + details
        )
    return sequence


def normalize_device(device: str) -> torch.device:
    value = str(device).strip().lower()
    if value.isdigit():
        value = "cuda:{}".format(value)
    result = torch.device(value)
    if result.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable in PyTorch.")
        index = 0 if result.index is None else result.index
        if index >= torch.cuda.device_count():
            raise RuntimeError(
                "CUDA device {} does not exist; {} device(s) available.".format(
                    index, torch.cuda.device_count()
                )
            )
    return result


class RiNALMoEmbedder:
    """Load giga-v1 once and compute one embedding per real nucleotide.

    Every RNA chain is passed through RiNALMo independently.  Each forward pass
    has its own CLS and EOS/SEP tokens; those two special-token vectors are
    checked and removed before returning the ``[sequence_length, 1280]`` tensor.
    """

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT,
        device: str = "cuda:1",
    ) -> None:
        self.checkpoint_path = Path(checkpoint_path).expanduser()
        if not self.checkpoint_path.is_file():
            raise FileNotFoundError(
                "RiNALMo checkpoint not found: {}".format(self.checkpoint_path)
            )
        self.device = normalize_device(device)

        config = giga_config()
        self.alphabet = Alphabet(**config.alphabet)
        self.model = RiNALMo(config)
        state_dict = torch.load(self.checkpoint_path, map_location="cpu")
        self.model.load_state_dict(state_dict, strict=True)
        del state_dict
        self.model.to(self.device)
        self.model.eval()

    def embed_sequence(self, sequence: str) -> torch.Tensor:
        """Embed one RNA chain and return only its nucleotide vectors."""

        sequence = validate_rna_sequence(sequence)
        tokens = torch.tensor(
            self.alphabet.batch_tokenize([sequence]),
            dtype=torch.int64,
            device=self.device,
        )
        expected_token_length = len(sequence) + 2
        if tuple(tokens.shape) != (1, expected_token_length):
            raise RuntimeError(
                "RiNALMo tokenizer length mismatch for an RNA chain: expected "
                "(1, {}), got {}. CLS/EOS removal is therefore unsafe.".format(
                    expected_token_length, tuple(tokens.shape)
                )
            )

        with torch.inference_mode():
            output = self.model(tokens, need_attn_weights=False)
        if "representation" not in output:
            raise RuntimeError("RiNALMo output is missing 'representation'.")
        full_representation = output["representation"]
        expected_full_shape = (1, expected_token_length, EMBEDDING_DIM)
        if tuple(full_representation.shape) != expected_full_shape:
            raise RuntimeError(
                "RiNALMo output shape mismatch: expected {}, got {}.".format(
                    expected_full_shape, tuple(full_representation.shape)
                )
            )

        # Token order is exactly: CLS, sequence nucleotides, EOS/SEP.
        representation = (
            full_representation[0, 1:-1]
            .detach()
            .to(device="cpu", dtype=torch.float32)
            .contiguous()
        )
        expected = (len(sequence), EMBEDDING_DIM)
        if tuple(representation.shape) != expected:
            raise RuntimeError(
                "RiNALMo nucleotide embedding shape mismatch: expected {}, got {}."
                .format(expected, tuple(representation.shape))
            )
        if not torch.isfinite(representation).all():
            raise RuntimeError("RiNALMo output contains NaN or Inf.")
        return representation

    def embed_chains_independently(
        self, sequences: Sequence[str]
    ) -> List[torch.Tensor]:
        """Run one RiNALMo forward pass per chain, preserving input order."""

        if not sequences:
            raise ValueError("At least one RNA chain is required.")
        return [self.embed_sequence(sequence) for sequence in sequences]

    def embed_sequences_jointly(self, sequences: Sequence[str]) -> torch.Tensor:
        """Compatibility alias: independently embed, then concatenate chains.

        Despite the historical method name, this function never inserts ``|``
        or ``<unk>`` and never performs a joint contextual forward pass.
        """

        return torch.cat(self.embed_chains_independently(sequences), dim=0)
