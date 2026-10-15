"""Training-compatible HyenaDNA pipeline for one website sample."""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List,Sequence,Union
import torch
from .hyenadna import DEFAULT_CHECKPOINT_ROOT,HyenaDNAEmbedder
from .processing import DNAChain,build_fixed_embedding,choose_mode,mean_pool_embeddings,validate_chains,validate_identifier


@dataclass(frozen=True)
class HyenaDNAPipelineResult:
    sample_id:str; mode:str; job_dir:Path; chain_embeddings_path:Path; fixed_embedding_path:Path; fixed_mask_path:Path; mean_embedding_path:Path; combined_embedding_path:Path; metadata_path:Path; warnings:List[str]


def result_paths(output_root:Union[str,Path],sample_id:str):
    job_dir=Path(output_root)/sample_id; embeddings=job_dir/"embeddings"
    return {"job_dir":job_dir,"chain":embeddings/"hyenadna_chains.pt","fixed":embeddings/"hyenadna_fixed.pt","mask":embeddings/"hyenadna_fixed_mask.pt","mean":embeddings/"hyenadna_mean.pt","combined":embeddings/"hyenadna_features.pt","metadata":job_dir/"dna_metadata.json"}


def ensure_outputs_available(paths,overwrite):
    targets=[paths[key] for key in ("chain","fixed","mask","mean","combined","metadata")]; existing=[path for path in targets if path.exists()]
    if existing and not overwrite: raise FileExistsError("Output files exist: {}. Use --overwrite.".format(", ".join(map(str,existing))))


class HyenaDNAPipeline:
    def __init__(self,checkpoint_root=DEFAULT_CHECKPOINT_ROOT,device="cuda:0",embedder=None):
        self.embedder=embedder if embedder is not None else HyenaDNAEmbedder(checkpoint_root,device)

    def run(self,sample_id:str,chains:Sequence[DNAChain],output_root:Union[str,Path],mode="auto",overwrite=False):
        sample_id=validate_identifier(sample_id,"Sample_ID"); chains=validate_chains(chains); mode_used=choose_mode(mode,len(chains)); paths=result_paths(output_root,sample_id); ensure_outputs_available(paths,overwrite)
        total_length=sum(len(chain.sequence) for chain in chains); warnings=[]
        if total_length>128: warnings.append("DNA total length {} exceeds 128. mean_pooling uses every real base; only site_embedding is truncated.".format(total_length))
        chain_embeddings=self.embedder.embed_chains(chains); fixed,mask,processing_warnings=build_fixed_embedding(chain_embeddings,mode_used); warnings.extend(processing_warnings); mean=mean_pool_embeddings(chain_embeddings)
        paths["chain"].parent.mkdir(parents=True,exist_ok=True); torch.save(chain_embeddings,paths["chain"]); torch.save({sample_id:fixed},paths["fixed"]); torch.save({sample_id:mask},paths["mask"]); torch.save({sample_id:mean},paths["mean"]); torch.save({sample_id:{"site_embedding":fixed,"mean_pooling":mean}},paths["combined"])
        metadata={"sample_id":sample_id,"direction_requirement":"All DNA chains are provided 5-prime to 3-prime.","mode_requested":mode,"mode_used":mode_used,"chain_count":len(chains),"total_dna_length":total_length,"separator_token_count":0,"special_tokens_removed_per_chain":["CLS","SEP"],"pooling":"length-weighted mean over all real bases","chains":[{"chain_id":chain.chain_id,"sequence":chain.sequence,"length":len(chain.sequence),"direction":"5to3","embedding_shape":list(chain_embeddings[chain.chain_id].shape)} for chain in chains],"site_embedding_shape":list(fixed.shape),"mean_embedding_shape":list(mean.shape),"warnings":warnings}
        paths["metadata"].write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
        return HyenaDNAPipelineResult(sample_id,mode_used,paths["job_dir"],paths["chain"],paths["fixed"],paths["mask"],paths["mean"],paths["combined"],paths["metadata"],warnings)
