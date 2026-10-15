"""Batch RiNALMo feature generation for S604-style tabular datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

import pandas as pd
import torch

from .rinalmo_model import EMBEDDING_DIM, RiNALMoEmbedder
from .rinalmo_processing import (
    build_fixed_embedding,
    concatenate_chain_embeddings,
    mean_pool_embedding,
    split_chain_sequences,
    validate_embedding,
)


def _torch_load(path: Union[str, Path]):
    """Load tensors on PyTorch 2.0 and newer without device side effects."""

    path = Path(path)
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:  # PyTorch 2.0.1 does not consistently expose weights_only.
        return torch.load(path, map_location="cpu")


def validate_dataset_columns(
    dataframe: pd.DataFrame,
    sample_id_column: str,
    sequence_column: str,
) -> None:
    missing = [
        column
        for column in (sample_id_column, sequence_column)
        if column not in dataframe.columns
    ]
    if missing:
        raise ValueError("Dataset is missing required columns: {}".format(missing))
    if dataframe.empty:
        raise ValueError("Dataset is empty.")
    if dataframe[sample_id_column].isna().any():
        raise ValueError("Dataset contains an empty sample_ID.")
    duplicated = dataframe[sample_id_column].astype(str).duplicated(keep=False)
    if duplicated.any():
        examples = (
            dataframe.loc[duplicated, sample_id_column]
            .astype(str)
            .drop_duplicates()
            .head(10)
            .tolist()
        )
        raise ValueError("Duplicate sample_ID values: {}".format(examples))
    if dataframe[sequence_column].isna().any():
        bad_ids = (
            dataframe.loc[dataframe[sequence_column].isna(), sample_id_column]
            .astype(str)
            .head(10)
            .tolist()
        )
        raise ValueError("Missing na_seq for sample(s): {}".format(bad_ids))


def parse_dataset_sequences(
    dataframe: pd.DataFrame,
    sample_id_column: str = "sample_ID",
    sequence_column: str = "na_seq",
) -> Tuple[Dict[str, List[str]], List[str]]:
    """Return sample-to-chain mapping and unique chains in first-seen order."""

    validate_dataset_columns(dataframe, sample_id_column, sequence_column)
    sample_chains: Dict[str, List[str]] = {}
    unique_sequences: List[str] = []
    seen = set()
    for _, row in dataframe.iterrows():
        sample_id = str(row[sample_id_column]).strip()
        if not sample_id:
            raise ValueError("sample_ID cannot be blank.")
        try:
            sequences = split_chain_sequences(str(row[sequence_column]))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Invalid na_seq for sample {}: {}".format(sample_id, error)
            ) from error
        sample_chains[sample_id] = sequences
        for sequence in sequences:
            if sequence not in seen:
                seen.add(sequence)
                unique_sequences.append(sequence)
    return sample_chains, unique_sequences


def load_sequence_cache(path: Optional[Union[str, Path]]) -> Dict[str, torch.Tensor]:
    if path is None or not Path(path).exists():
        return {}
    value = _torch_load(path)
    if not isinstance(value, Mapping):
        raise ValueError("RiNALMo sequence cache must be a dictionary.")
    cache: Dict[str, torch.Tensor] = {}
    for sequence, embedding in value.items():
        sequences = split_chain_sequences(str(sequence))
        if len(sequences) != 1:
            raise ValueError("Cache key is not a single RNA chain: {}".format(sequence))
        normalized = sequences[0]
        validate_embedding(
            "cached RNA {}".format(normalized),
            embedding,
            expected_length=len(normalized),
        )
        cache[normalized] = embedding.detach().cpu().to(torch.float32).contiguous()
    return cache


def embed_unique_sequences(
    unique_sequences: List[str],
    embedder: RiNALMoEmbedder,
    cache: Optional[Dict[str, torch.Tensor]] = None,
    cache_path: Optional[Union[str, Path]] = None,
    save_every: int = 10,
) -> Dict[str, torch.Tensor]:
    """Embed only cache misses; missing or malformed features always raise."""

    result = {} if cache is None else dict(cache)
    missing = [sequence for sequence in unique_sequences if sequence not in result]
    for index, sequence in enumerate(missing, start=1):
        embedding = embedder.embed_sequence(sequence)
        validate_embedding(
            "RNA {}".format(sequence),
            embedding,
            expected_length=len(sequence),
        )
        result[sequence] = embedding
        if cache_path and save_every > 0 and index % save_every == 0:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            torch.save(result, cache_file)
            print(
                "Saved sequence cache: {}/{} new chains".format(index, len(missing)),
                flush=True,
            )
    if cache_path:
        cache_file = Path(cache_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        torch.save(result, cache_file)
    unresolved = [sequence for sequence in unique_sequences if sequence not in result]
    if unresolved:
        raise RuntimeError(
            "RiNALMo features are missing after inference: {}".format(unresolved[:10])
        )
    return result


def build_dataset_features(
    sample_chains: Mapping[str, List[str]],
    sequence_embeddings: Mapping[str, torch.Tensor],
) -> Tuple[Dict[str, dict], List[dict]]:
    """Create the exact nested dictionary consumed by RNA-MLP dataset.py."""

    features: Dict[str, dict] = {}
    manifest: List[dict] = []
    for sample_id, sequences in sample_chains.items():
        missing = [sequence for sequence in sequences if sequence not in sequence_embeddings]
        if missing:
            raise KeyError(
                "Missing RiNALMo feature(s) for sample {}: {}".format(
                    sample_id, missing
                )
            )
        per_chain = [sequence_embeddings[sequence] for sequence in sequences]
        concatenated = concatenate_chain_embeddings(sequences, per_chain)
        fixed, mask, warnings = build_fixed_embedding(concatenated)
        mean = mean_pool_embedding(concatenated)
        features[sample_id] = {
            "site_embedding": fixed,
            "mean_pooling": mean,
        }
        manifest.append(
            {
                "sample_ID": sample_id,
                "chain_count": len(sequences),
                "chain_lengths": [len(sequence) for sequence in sequences],
                "total_nucleotide_length": sum(len(sequence) for sequence in sequences),
                "site_real_length": int(mask.sum().item()),
                "mean_pooling_nucleotide_count": int(concatenated.shape[0]),
                "warnings": warnings,
            }
        )
    if len(features) != len(sample_chains):
        raise RuntimeError("Not every dataset sample received an RNA feature.")
    return features, manifest


def write_manifest(manifest: List[dict], path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)


def compare_feature_files(
    candidate_path: Union[str, Path],
    reference_path: Union[str, Path],
    atol: float = 1e-6,
) -> dict:
    """Compare nested S604 RNA features by sample_ID and feature name."""

    candidate = _torch_load(candidate_path)
    reference = _torch_load(reference_path)
    if not isinstance(candidate, Mapping) or not isinstance(reference, Mapping):
        raise ValueError("Both RNA feature files must contain dictionaries.")
    candidate_ids = set(map(str, candidate.keys()))
    reference_ids = set(map(str, reference.keys()))
    if candidate_ids != reference_ids:
        raise ValueError(
            "sample_ID sets differ; candidate-only={}, reference-only={}.".format(
                sorted(candidate_ids - reference_ids)[:10],
                sorted(reference_ids - candidate_ids)[:10],
            )
        )
    reports = {}
    for feature_name in ("mean_pooling", "site_embedding"):
        max_difference = -1.0
        sum_difference = 0.0
        element_count = 0
        mismatch_count = 0
        worst_sample = None
        for sample_id in sorted(candidate_ids):
            candidate_record = candidate[sample_id]
            reference_record = reference[sample_id]
            if not isinstance(candidate_record, Mapping) or feature_name not in candidate_record:
                raise KeyError("Candidate {} missing {}.".format(sample_id, feature_name))
            if not isinstance(reference_record, Mapping) or feature_name not in reference_record:
                raise KeyError("Reference {} missing {}.".format(sample_id, feature_name))
            left = candidate_record[feature_name].detach().cpu().to(torch.float32)
            right = reference_record[feature_name].detach().cpu().to(torch.float32)
            if tuple(left.shape) != tuple(right.shape):
                raise ValueError(
                    "{} shape differs for {}: {} vs {}.".format(
                        feature_name, sample_id, tuple(left.shape), tuple(right.shape)
                    )
                )
            difference = torch.abs(left - right)
            sample_max = float(difference.max().item())
            if sample_max > atol:
                mismatch_count += 1
            if sample_max > max_difference:
                max_difference = sample_max
                worst_sample = sample_id
            sum_difference += float(difference.sum().item())
            element_count += difference.numel()
        reports[feature_name] = {
            "sample_count": len(candidate_ids),
            "atol": float(atol),
            "all_close": mismatch_count == 0,
            "mismatched_samples": mismatch_count,
            "max_absolute_difference": max(max_difference, 0.0),
            "mean_absolute_difference": (
                sum_difference / element_count if element_count else 0.0
            ),
            "worst_sample_ID": worst_sample,
        }
    return reports
