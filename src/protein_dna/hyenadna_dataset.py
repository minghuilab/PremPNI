"""S1345 batch HyenaDNA feature generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

import pandas as pd
import torch

from .hyenadna import HyenaDNAEmbedder
from .processing import (
    DNAChain, HYENADNA_DIM, build_fixed_from_concatenated,
    concatenate_embeddings, mean_pool_embeddings, split_chain_sequences,
    validate_embedding, validate_dna_sequence,
)


def torch_load_cpu(path: Union[str, Path]):
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def parse_dataset_sequences(dataframe: pd.DataFrame) -> Tuple[Dict[str, List[str]], List[str]]:
    missing = [c for c in ("sample_ID", "na_seq") if c not in dataframe.columns]
    if missing: raise ValueError("Dataset is missing required columns: {}".format(missing))
    if dataframe[["sample_ID", "na_seq"]].isna().any().any(): raise ValueError("Dataset contains empty sample_ID or na_seq.")
    if dataframe["sample_ID"].astype(str).duplicated().any(): raise ValueError("Dataset contains duplicate sample_ID values.")
    sample_chains, unique, seen = {}, [], set()
    for _, row in dataframe.iterrows():
        sample_id = str(row["sample_ID"]).strip()
        chains = split_chain_sequences(str(row["na_seq"]))
        sample_chains[sample_id] = chains
        for chain in chains:
            if chain not in seen: seen.add(chain); unique.append(chain)
    return sample_chains, unique


def load_sequence_cache(path: Optional[Union[str, Path]]) -> Dict[str, torch.Tensor]:
    if path is None or not Path(path).exists(): return {}
    value = torch_load_cpu(path)
    if not isinstance(value, Mapping): raise ValueError("HyenaDNA cache must contain a dictionary.")
    result = {}
    for sequence, embedding in value.items():
        sequence = validate_dna_sequence(str(sequence), "cached DNA")
        validate_embedding("cached DNA", embedding, len(sequence))
        result[sequence] = embedding.detach().cpu().to(torch.float32).contiguous()
    return result


def embed_unique_sequences(
    sequences: List[str], embedder: HyenaDNAEmbedder,
    cache: Optional[Dict[str, torch.Tensor]] = None,
    cache_path: Optional[Union[str, Path]] = None, save_every: int = 10,
) -> Dict[str, torch.Tensor]:
    result = {} if cache is None else dict(cache)
    missing = [sequence for sequence in sequences if sequence not in result]
    for number, sequence in enumerate(missing, start=1):
        embedding = embedder.embed_chain(DNAChain("DNA_cache_{}".format(number), sequence))
        validate_embedding("DNA_cache_{}".format(number), embedding, len(sequence))
        result[sequence] = embedding
        if cache_path and save_every > 0 and number % save_every == 0:
            path = Path(cache_path); path.parent.mkdir(parents=True, exist_ok=True); torch.save(result, path)
            print("Saved HyenaDNA cache: {}/{}".format(number, len(missing)), flush=True)
    if cache_path:
        path = Path(cache_path); path.parent.mkdir(parents=True, exist_ok=True); torch.save(result, path)
    unresolved = [sequence for sequence in sequences if sequence not in result]
    if unresolved: raise RuntimeError("Missing HyenaDNA sequences: {}".format(unresolved[:10]))
    return result


def build_dataset_features(sample_chains: Mapping[str, List[str]], sequence_embeddings: Mapping[str, torch.Tensor]):
    features, manifest = {}, []
    for sample_id, sequences in sample_chains.items():
        missing = [sequence for sequence in sequences if sequence not in sequence_embeddings]
        if missing: raise KeyError("{} missing DNA features: {}".format(sample_id, missing))
        embeddings = [sequence_embeddings[sequence] for sequence in sequences]
        concatenated = concatenate_embeddings(sequences, embeddings)
        fixed, mask, warnings = build_fixed_from_concatenated(concatenated)
        chain_dict = {"DNA_{}".format(i): embedding for i, embedding in enumerate(embeddings, 1)}
        mean = mean_pool_embeddings(chain_dict)
        features[sample_id] = {"site_embedding": fixed, "mean_pooling": mean}
        manifest.append({
            "sample_ID": sample_id, "chain_count": len(sequences),
            "chain_lengths": [len(sequence) for sequence in sequences],
            "total_base_count": int(concatenated.shape[0]),
            "mean_pooling_base_count": int(concatenated.shape[0]),
            "site_real_length": int(mask.sum()), "warnings": warnings,
        })
    return features, manifest


def write_manifest(manifest, path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")


def compare_feature_files(candidate_path, reference_path, atol=1e-6):
    candidate, reference = torch_load_cpu(candidate_path), torch_load_cpu(reference_path)
    if not isinstance(candidate, Mapping) or not isinstance(reference, Mapping): raise ValueError("Both HyenaDNA files must contain dictionaries.")
    if set(candidate) != set(reference): raise ValueError("Candidate/reference sample_ID sets differ.")
    report = {}
    for feature_name in ("mean_pooling", "site_embedding"):
        maxima, total, count = [], 0.0, 0
        for sample_id in sorted(candidate):
            left, right = candidate[sample_id][feature_name].float(), reference[sample_id][feature_name].float()
            if tuple(left.shape) != tuple(right.shape): raise ValueError("{} shape differs for {}.".format(feature_name,sample_id))
            difference=torch.abs(left-right); maxima.append((float(difference.max()),sample_id)); total+=float(difference.sum()); count+=difference.numel()
        worst,worst_sample=max(maxima)
        report[feature_name]={"sample_count":len(candidate),"atol":float(atol),"all_close":all(v<=atol for v,_ in maxima),"mismatched_samples":sum(v>atol for v,_ in maxima),"max_absolute_difference":worst,"mean_absolute_difference":total/count,"worst_sample_ID":worst_sample}
    return report
