"""Strict S604 batch feature generation with ESM-2(3B)."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple, Union

import pandas as pd
import torch

from .esm2_3b import EMBEDDING_DIM, ESM2ThreeBEmbedder, validate_sequence


REQUIRED_COLUMNS = (
    "sample_ID",
    "Wt_Prot_Sequence",
    "Muta_Prot_Sequence",
    "mut_seq_idx",
)


def torch_load_cpu(path: Union[str, Path]):
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def validate_site_vector(sample_id: str, role: str, value: torch.Tensor) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise TypeError("{}.{} must be a torch.Tensor.".format(sample_id, role))
    value = value.detach().cpu().to(torch.float32).contiguous()
    if tuple(value.shape) != (EMBEDDING_DIM,):
        raise ValueError(
            "{}.{} must have shape ({},), got {}.".format(
                sample_id, role, EMBEDDING_DIM, tuple(value.shape)
            )
        )
    if not torch.isfinite(value).all():
        raise ValueError("{}.{} contains NaN or Inf.".format(sample_id, role))
    return value


def parse_s604_requests(
    dataframe: pd.DataFrame,
) -> Tuple[OrderedDict, List[str]]:
    """Map each unique sequence to all sample/site requests that consume it."""

    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: {}".format(missing))
    if dataframe.empty:
        raise ValueError("Dataset is empty.")
    if dataframe["sample_ID"].isna().any():
        raise ValueError("Dataset contains an empty sample_ID.")
    sample_ids = dataframe["sample_ID"].astype(str).tolist()
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Dataset contains duplicate sample_ID values.")

    requests = OrderedDict()
    for _, row in dataframe.iterrows():
        sample_id = str(row["sample_ID"]).strip()
        wt_sequence = validate_sequence(str(row["Wt_Prot_Sequence"]))
        muta_sequence = validate_sequence(str(row["Muta_Prot_Sequence"]))
        if len(wt_sequence) != len(muta_sequence):
            raise ValueError(
                "{} WT/mutant lengths differ: {} vs {}.".format(
                    sample_id, len(wt_sequence), len(muta_sequence)
                )
            )
        try:
            site_index = int(row["mut_seq_idx"])
        except (TypeError, ValueError) as error:
            raise ValueError("{} has an invalid mut_seq_idx.".format(sample_id)) from error
        if site_index < 0 or site_index >= len(wt_sequence):
            raise ValueError(
                "{} mut_seq_idx {} is outside sequence length {}.".format(
                    sample_id, site_index, len(wt_sequence)
                )
            )
        differences = [
            index
            for index, (wt, muta) in enumerate(zip(wt_sequence, muta_sequence))
            if wt != muta
        ]
        if differences != [site_index]:
            raise ValueError(
                "{} must contain exactly one substitution at mut_seq_idx {}; "
                "observed differences: {}.".format(sample_id, site_index, differences[:10])
            )
        requests.setdefault(wt_sequence, []).append((sample_id, "wt_site", site_index))
        requests.setdefault(muta_sequence, []).append((sample_id, "muta_site", site_index))
    return requests, sample_ids


def load_partial_features(path: Union[str, Path]) -> Dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    value = torch_load_cpu(path)
    if not isinstance(value, Mapping):
        raise ValueError("Partial ESM-2 feature file must contain a dictionary.")
    result: Dict[str, dict] = {}
    for sample_id, record in value.items():
        if not isinstance(record, Mapping):
            raise ValueError("Partial record {} must be a dictionary.".format(sample_id))
        result[str(sample_id)] = {}
        for role in ("wt_site", "muta_site"):
            if role in record:
                result[str(sample_id)][role] = validate_site_vector(
                    str(sample_id), role, record[role]
                )
    return result


def generate_s604_protein_features(
    requests: OrderedDict,
    sample_ids: List[str],
    embedder: ESM2ThreeBEmbedder,
    partial_path: Union[str, Path],
    resume: bool = False,
    save_every: int = 10,
) -> Dict[str, dict]:
    """Embed each unique sequence once and retain only requested site vectors."""

    partial_path = Path(partial_path)
    features = load_partial_features(partial_path) if resume else {}
    for sample_id in sample_ids:
        features.setdefault(sample_id, {})

    pending_sequences = []
    for sequence, consumers in requests.items():
        if any(role not in features[sample_id] for sample_id, role, _ in consumers):
            pending_sequences.append((sequence, consumers))
    print(
        "Unique protein sequences: {}; pending: {}".format(
            len(requests), len(pending_sequences)
        ),
        flush=True,
    )

    for sequence_number, (sequence, consumers) in enumerate(pending_sequences, start=1):
        embedding = embedder.embed_sequence(
            "S604_sequence_{}".format(sequence_number), sequence
        )
        for sample_id, role, site_index in consumers:
            if role not in features[sample_id]:
                features[sample_id][role] = validate_site_vector(
                    sample_id, role, embedding[site_index].clone()
                )
        del embedding
        if save_every > 0 and sequence_number % save_every == 0:
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(features, partial_path)
            print(
                "Saved partial ESM-2 features: {}/{} pending sequences".format(
                    sequence_number, len(pending_sequences)
                ),
                flush=True,
            )

    errors = []
    for sample_id in sample_ids:
        for role in ("wt_site", "muta_site"):
            if role not in features[sample_id]:
                errors.append("{}.{} missing".format(sample_id, role))
            else:
                features[sample_id][role] = validate_site_vector(
                    sample_id, role, features[sample_id][role]
                )
    if errors:
        raise RuntimeError(
            "Incomplete ESM-2 features ({}): {}".format(len(errors), errors[:20])
        )
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(features, partial_path)
    return features


def compare_protein_feature_files(candidate_path, reference_path, atol=1e-6):
    candidate = torch_load_cpu(candidate_path)
    reference = torch_load_cpu(reference_path)
    if not isinstance(candidate, Mapping) or not isinstance(reference, Mapping):
        raise ValueError("Both protein feature files must contain dictionaries.")
    candidate_ids, reference_ids = set(candidate), set(reference)
    if candidate_ids != reference_ids:
        raise ValueError(
            "sample_ID sets differ; candidate-only={}, reference-only={}.".format(
                sorted(candidate_ids - reference_ids)[:10],
                sorted(reference_ids - candidate_ids)[:10],
            )
        )
    report = {}
    for role in ("wt_site", "muta_site"):
        maxima, sums, counts = [], 0.0, 0
        for sample_id in sorted(candidate_ids):
            left = validate_site_vector(sample_id, role, candidate[sample_id][role])
            right = validate_site_vector(sample_id, role, reference[sample_id][role])
            difference = torch.abs(left - right)
            maxima.append((float(difference.max().item()), sample_id))
            sums += float(difference.sum().item())
            counts += difference.numel()
        worst_difference, worst_sample = max(maxima)
        report[role] = {
            "sample_count": len(candidate_ids),
            "atol": float(atol),
            "all_close": all(value <= atol for value, _ in maxima),
            "mismatched_samples": sum(value > atol for value, _ in maxima),
            "max_absolute_difference": worst_difference,
            "mean_absolute_difference": sums / counts,
            "worst_sample_ID": worst_sample,
        }
    return report
