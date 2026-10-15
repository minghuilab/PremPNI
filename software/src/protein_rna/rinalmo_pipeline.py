"""Independent-chain RiNALMo pipeline for one Protein-RNA sample."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Union

import torch

from .rinalmo_model import DEFAULT_CHECKPOINT, RiNALMoEmbedder
from .rinalmo_processing import (
    RNAChain,
    build_fixed_embedding,
    choose_mode,
    concatenate_chain_embeddings,
    mean_pool_embedding,
    validate_chains,
    validate_identifier,
)


@dataclass(frozen=True)
class RiNALMoPipelineResult:
    sample_id: str
    mode: str
    chain_embeddings_path: Path
    joint_embedding_path: Path
    fixed_embedding_path: Path
    fixed_mask_path: Path
    mean_embedding_path: Path
    combined_embedding_path: Path
    metadata_path: Path
    warnings: List[str]


def result_paths(output_root: Union[str, Path], sample_id: str):
    job_dir = Path(output_root) / sample_id
    embedding_dir = job_dir / "embeddings"
    return {
        "job_dir": job_dir,
        "chain": embedding_dir / "rinalmo_chains.pt",
        # Keep the old filename for downstream compatibility.  Its contents are
        # now a separator-free concatenation of independent-chain embeddings.
        "joint": embedding_dir / "rinalmo_joint.pt",
        "fixed": embedding_dir / "rinalmo_fixed.pt",
        "mask": embedding_dir / "rinalmo_fixed_mask.pt",
        "mean": embedding_dir / "rinalmo_mean.pt",
        "combined": embedding_dir / "rinalmo_features.pt",
        "metadata": job_dir / "rna_metadata.json",
    }


def ensure_outputs_available(paths, overwrite: bool) -> None:
    targets = [
        paths["chain"],
        paths["joint"],
        paths["fixed"],
        paths["mask"],
        paths["mean"],
        paths["combined"],
        paths["metadata"],
    ]
    existing = [path for path in targets if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Output files already exist: {}. Use --overwrite to replace them."
            .format(", ".join(str(path) for path in existing))
        )


class RiNALMoPipeline:
    """Embed each chain separately, concatenate bases, then pool all bases."""

    def __init__(
        self,
        checkpoint_path: Union[str, Path] = DEFAULT_CHECKPOINT,
        device: str = "cuda:1",
        embedder=None,
    ) -> None:
        self.embedder = (
            embedder
            if embedder is not None
            else RiNALMoEmbedder(checkpoint_path, device)
        )

    def run(
        self,
        sample_id: str,
        chains: Sequence[RNAChain],
        output_root: Union[str, Path],
        mode: str = "auto",
        overwrite: bool = False,
    ) -> RiNALMoPipelineResult:
        sample_id = validate_identifier(sample_id, "Sample_ID")
        chains = validate_chains(chains)
        mode_used = choose_mode(mode, len(chains))
        paths = result_paths(output_root, sample_id)
        ensure_outputs_available(paths, overwrite)

        total_length = sum(len(chain.sequence) for chain in chains)
        warnings: List[str] = []
        if total_length > 128:
            warnings.append(
                "RNA total length {} exceeds 128. The MLP mean_pooling feature "
                "still uses all nucleotides; only site_embedding is truncated."
                .format(total_length)
            )

        # A chain is never joined to another chain before RiNALMo inference.
        per_chain_tensors = self.embedder.embed_chains_independently(
            [chain.sequence for chain in chains]
        )
        concatenated_embedding = concatenate_chain_embeddings(
            [chain.sequence for chain in chains], per_chain_tensors
        )
        chain_embeddings = {
            chain.chain_id: embedding
            for chain, embedding in zip(chains, per_chain_tensors)
        }
        fixed, fixed_mask, processing_warnings = build_fixed_embedding(
            concatenated_embedding
        )
        warnings.extend(processing_warnings)
        mean_embedding = mean_pool_embedding(concatenated_embedding)

        paths["chain"].parent.mkdir(parents=True, exist_ok=True)
        torch.save(chain_embeddings, paths["chain"])
        torch.save({sample_id: concatenated_embedding}, paths["joint"])
        torch.save({sample_id: fixed}, paths["fixed"])
        torch.save({sample_id: fixed_mask}, paths["mask"])
        torch.save({sample_id: mean_embedding}, paths["mean"])
        torch.save(
            {
                sample_id: {
                    "site_embedding": fixed,
                    "mean_pooling": mean_embedding,
                }
            },
            paths["combined"],
        )

        metadata = {
            "sample_id": sample_id,
            "direction_requirement": "All RNA chains are provided 5-prime to 3-prime.",
            "mode_requested": mode,
            "mode_used": mode_used,
            "chain_count": len(chains),
            "total_rna_length": total_length,
            "concatenated_nucleotide_length": total_length,
            "separator_token_count": 0,
            "special_tokens_removed_per_chain": ["CLS", "EOS/SEP"],
            "pooling": "length-weighted mean over all real nucleotides",
            "chains": [
                {
                    "chain_id": chain.chain_id,
                    "sequence": chain.sequence,
                    "length": len(chain.sequence),
                    "direction": "5to3",
                    "embedding_shape": list(
                        chain_embeddings[chain.chain_id].shape
                    ),
                }
                for chain in chains
            ],
            "site_embedding_shape": list(fixed.shape),
            "concatenated_embedding_shape": list(
                concatenated_embedding.shape
            ),
            "site_mask_shape": list(fixed_mask.shape),
            "mean_embedding_shape": list(mean_embedding.shape),
            "warnings": warnings,
        }
        with paths["metadata"].open("w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False, indent=2)

        return RiNALMoPipelineResult(
            sample_id=sample_id,
            mode=mode_used,
            chain_embeddings_path=paths["chain"],
            joint_embedding_path=paths["joint"],
            fixed_embedding_path=paths["fixed"],
            fixed_mask_path=paths["mask"],
            mean_embedding_path=paths["mean"],
            combined_embedding_path=paths["combined"],
            metadata_path=paths["metadata"],
            warnings=warnings,
        )
