"""S1345 batch ESM-DBP mutation-site feature generation."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple, Union

import numpy as np
import pandas as pd
import torch

from .esm_dbp import EMBEDDING_DIM, ESMDBPEmbedder, validate_sequence


MUTATION_PATTERN = re.compile(r"^([A-Z])([1-9][0-9]*)([A-Z])$")
REQUIRED_COLUMNS = (
    "sample_ID", "prot_seq", "Protein_Mutation",
    "Wt_Prot_Sequence", "Muta_Prot_Sequence",
)


def torch_load_cpu(path: Union[str, Path]):
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def validate_site_vector(sample_id: str, role: str, value) -> torch.Tensor:
    tensor = value.detach().cpu().to(torch.float32) if isinstance(value, torch.Tensor) else torch.as_tensor(value, dtype=torch.float32)
    tensor = tensor.contiguous()
    if tuple(tensor.shape) != (EMBEDDING_DIM,):
        raise ValueError("{}.{} must have shape ({},), got {}.".format(sample_id, role, EMBEDDING_DIM, tuple(tensor.shape)))
    if not torch.isfinite(tensor).all():
        raise ValueError("{}.{} contains NaN or Inf.".format(sample_id, role))
    return tensor


def parse_s1345_requests(dataframe: pd.DataFrame) -> Tuple[OrderedDict, List[str]]:
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: {}".format(missing))
    sample_ids = dataframe["sample_ID"].astype(str).tolist()
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("Dataset contains duplicate sample_ID values.")
    requests = OrderedDict()
    for _, row in dataframe.iterrows():
        sample_id = str(row["sample_ID"]).strip()
        wt_sequence = validate_sequence(str(row["prot_seq"]))
        stored_wt = validate_sequence(str(row["Wt_Prot_Sequence"]))
        stored_muta = validate_sequence(str(row["Muta_Prot_Sequence"]))
        if wt_sequence != stored_wt:
            raise ValueError("{} prot_seq differs from Wt_Prot_Sequence.".format(sample_id))
        match = MUTATION_PATTERN.fullmatch(str(row["Protein_Mutation"]).strip().upper())
        if match is None:
            raise ValueError("{} has invalid Protein_Mutation.".format(sample_id))
        reference, position_text, alternate = match.groups()
        position = int(position_text)  # Protein_Mutation is one-based in S1345.
        if position > len(wt_sequence) or wt_sequence[position - 1] != reference:
            raise ValueError("{} mutation does not match the one-based WT sequence.".format(sample_id))
        if reference == alternate:
            raise ValueError("{} mutation does not change the amino acid.".format(sample_id))
        site_index = position - 1
        built_muta = wt_sequence[:site_index] + alternate + wt_sequence[site_index + 1:]
        if built_muta != stored_muta:
            raise ValueError("{} Muta_Prot_Sequence is inconsistent with Protein_Mutation.".format(sample_id))
        requests.setdefault(wt_sequence, []).append((sample_id, "wt_site", site_index))
        requests.setdefault(stored_muta, []).append((sample_id, "muta_site", site_index))
    return requests, sample_ids


def load_partial_features(path: Union[str, Path]) -> Dict[str, dict]:
    path = Path(path)
    if not path.exists():
        return {}
    value = torch_load_cpu(path)
    if not isinstance(value, Mapping):
        raise ValueError("Partial ESM-DBP file must contain a dictionary.")
    result = {}
    for sample_id, record in value.items():
        if not isinstance(record, Mapping):
            raise ValueError("Partial record {} must be a dictionary.".format(sample_id))
        result[str(sample_id)] = {
            role: validate_site_vector(str(sample_id), role, record[role])
            for role in ("wt_site", "muta_site") if role in record
        }
    return result


def generate_s1345_protein_features(
    requests: OrderedDict,
    sample_ids: List[str],
    embedder: ESMDBPEmbedder,
    partial_path: Union[str, Path],
    resume: bool = False,
    save_every: int = 10,
) -> Dict[str, dict]:
    partial_path = Path(partial_path)
    features = load_partial_features(partial_path) if resume else {}
    for sample_id in sample_ids:
        features.setdefault(sample_id, {})
    pending = [
        (sequence, consumers) for sequence, consumers in requests.items()
        if any(role not in features[sample_id] for sample_id, role, _ in consumers)
    ]
    print("Unique protein sequences: {}; pending: {}".format(len(requests), len(pending)), flush=True)
    for number, (sequence, consumers) in enumerate(pending, start=1):
        embedding = embedder.embed_sequence("S1345_sequence_{}".format(number), sequence)
        if embedding.shape != (len(sequence), EMBEDDING_DIM) or not np.isfinite(embedding).all():
            raise RuntimeError("ESM-DBP returned an invalid embedding for sequence {}.".format(number))
        for sample_id, role, site_index in consumers:
            if role not in features[sample_id]:
                features[sample_id][role] = validate_site_vector(sample_id, role, embedding[site_index].copy())
        del embedding
        if save_every > 0 and number % save_every == 0:
            partial_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(features, partial_path)
            print("Saved partial ESM-DBP features: {}/{}".format(number, len(pending)), flush=True)
    errors = []
    for sample_id in sample_ids:
        for role in ("wt_site", "muta_site"):
            if role not in features[sample_id]:
                errors.append("{}.{}".format(sample_id, role))
            else:
                features[sample_id][role] = validate_site_vector(sample_id, role, features[sample_id][role])
    if errors:
        raise RuntimeError("Incomplete ESM-DBP features: {}".format(errors[:20]))
    partial_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(features, partial_path)
    return features


def compare_protein_feature_files(candidate_path, reference_path, atol=1e-6):
    candidate, reference = torch_load_cpu(candidate_path), torch_load_cpu(reference_path)
    if not isinstance(candidate, Mapping) or not isinstance(reference, Mapping):
        raise ValueError("Both ESM-DBP files must contain dictionaries.")
    if set(candidate) != set(reference):
        raise ValueError("Candidate/reference sample_ID sets differ.")
    report = {}
    for role in ("wt_site", "muta_site"):
        maxima, total, count = [], 0.0, 0
        for sample_id in sorted(candidate):
            left = validate_site_vector(sample_id, role, candidate[sample_id][role])
            right = validate_site_vector(sample_id, role, reference[sample_id][role])
            difference = torch.abs(left - right)
            maxima.append((float(difference.max()), sample_id))
            total += float(difference.sum()); count += difference.numel()
        worst, worst_sample = max(maxima)
        report[role] = {
            "sample_count": len(candidate), "atol": float(atol),
            "all_close": all(value <= atol for value, _ in maxima),
            "mismatched_samples": sum(value > atol for value, _ in maxima),
            "max_absolute_difference": worst,
            "mean_absolute_difference": total / count,
            "worst_sample_ID": worst_sample,
        }
    return report
