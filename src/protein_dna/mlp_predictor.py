"""Strict single-sample and S1345 batch inference for Protein-DNA MLPs."""

from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict,Mapping,Sequence
import numpy as np
import pandas as pd
import torch
from .mlp_model import DualTowerAffinityMLP

PROTEIN_DIM=1280; DNA_DIM=256
DEFAULT_MODEL_ROOT=Path(os.environ.get("PREMPNI_MODEL_ROOT","/opt/prempni/models"))/"mlp"/"protein_dna"


@dataclass(frozen=True)
class MLPModelSpec:
    split_seed:int; trial:int; checkpoint_relative_path:str; hp_seed:int; embed_dim:int; prot_layers:int; dna_layers:int; dropout:float
    @property
    def name(self): return "Seed{}_trial{}".format(self.split_seed,self.trial)
    @property
    def prediction_column(self): return "pred_seed{}".format(self.split_seed)


FINAL_MODEL_SPECS:Sequence[MLPModelSpec]=(
    MLPModelSpec(46,8,"DNA_F_F_Seed46/trial_8/best_network.pth",42,256,1,1,0.4010),
    MLPModelSpec(66,0,"DNA_F_F_Seed66/trial_0/best_network.pth",114514,256,1,3,0.3789),
    MLPModelSpec(77,4,"DNA_F_F_Seed77/trial_4/best_network.pth",42,256,1,3,0.3544),
)


@dataclass(frozen=True)
class EnsemblePrediction:
    sample_id:str; model_predictions:Dict[str,float]; mean_ddg:float; classification:str


def normalize_device(device):
    value=str(device).strip().lower()
    if value=="auto": value="cuda:0" if torch.cuda.is_available() else "cpu"
    if value.isdigit(): value="cuda:{}".format(value)
    result=torch.device(value)
    if result.type=="cuda" and not torch.cuda.is_available(): raise RuntimeError("CUDA requested but unavailable.")
    if result.type=="cuda" and (result.index or 0)>=torch.cuda.device_count(): raise RuntimeError("CUDA device does not exist.")
    return result


def torch_load_cpu(path):
    path=Path(path)
    if not path.is_file(): raise FileNotFoundError("File not found: {}".format(path))
    try: return torch.load(path,map_location="cpu",weights_only=True)
    except TypeError: return torch.load(path,map_location="cpu")


def as_feature_tensor(value,expected_dim,name):
    tensor=value.detach().cpu().float().contiguous() if isinstance(value,torch.Tensor) else torch.as_tensor(value,dtype=torch.float32).contiguous()
    if tuple(tensor.shape)!=(expected_dim,): raise ValueError("{} must have shape ({},), got {}.".format(name,expected_dim,tuple(tensor.shape)))
    if not torch.isfinite(tensor).all(): raise ValueError("{} contains NaN or Inf.".format(name))
    return tensor


def extract_sample_features(sample_id,protein_dict,dna_dict):
    if sample_id not in protein_dict: raise KeyError("Protein features missing {}.".format(sample_id))
    if sample_id not in dna_dict: raise KeyError("DNA features missing {}.".format(sample_id))
    protein=protein_dict[sample_id]; dna=dna_dict[sample_id]
    if not isinstance(protein,Mapping) or any(k not in protein for k in ("wt_site","muta_site")): raise KeyError("{} protein record is incomplete.".format(sample_id))
    if isinstance(dna,Mapping):
        if "mean_pooling" not in dna: raise KeyError("{} DNA record lacks mean_pooling.".format(sample_id))
        dna=dna["mean_pooling"]
    return as_feature_tensor(protein["wt_site"],PROTEIN_DIM,sample_id+".wt_site"),as_feature_tensor(protein["muta_site"],PROTEIN_DIM,sample_id+".muta_site"),as_feature_tensor(dna,DNA_DIM,sample_id+".DNA.mean_pooling")


def load_sample_features(sample_id,protein_feature_path,dna_feature_path):
    return extract_sample_features(sample_id,torch_load_cpu(protein_feature_path),torch_load_cpu(dna_feature_path))


class ProteinDNAMLPEnsemble:
    def __init__(self,model_root=DEFAULT_MODEL_ROOT,device="cpu",specs=FINAL_MODEL_SPECS):
        self.model_root=Path(model_root); self.device=normalize_device(device); self.specs=tuple(specs); self.models={}
        for spec in self.specs:
            path=self.model_root/spec.checkpoint_relative_path
            model=DualTowerAffinityMLP(PROTEIN_DIM,spec.embed_dim,DNA_DIM,spec.prot_layers,spec.dna_layers,spec.dropout)
            checkpoint=torch_load_cpu(path); state=checkpoint.get("state_dict",checkpoint) if isinstance(checkpoint,Mapping) else checkpoint
            model.load_state_dict(state,strict=True); model.to(self.device); model.eval(); self.models[spec.name]=model

    def predict_tensor_batches(self,wt,mut,dna,batch_size=64):
        rows=wt.shape[0]; expected=((rows,PROTEIN_DIM),(rows,PROTEIN_DIM),(rows,DNA_DIM)); actual=(tuple(wt.shape),tuple(mut.shape),tuple(dna.shape))
        if actual!=expected: raise ValueError("Batch feature shapes must be {}, got {}.".format(expected,actual))
        result={spec.name:[] for spec in self.specs}
        with torch.no_grad():
            for start in range(0,rows,batch_size):
                end=min(start+batch_size,rows); w=wt[start:end].to(self.device); m=mut[start:end].to(self.device); d=dna[start:end].to(self.device)
                for spec in self.specs:
                    values=self.models[spec.name](w,m,d)
                    if not torch.isfinite(values).all(): raise RuntimeError("{} produced NaN/Inf.".format(spec.name))
                    result[spec.name].append(values.cpu().numpy())
        return {name:np.concatenate(chunks).astype(np.float64,copy=False) for name,chunks in result.items()}

    def predict(self,sample_id,wt_site,muta_site,dna_mean):
        predictions=self.predict_tensor_batches(as_feature_tensor(wt_site,PROTEIN_DIM,"wt_site").unsqueeze(0),as_feature_tensor(muta_site,PROTEIN_DIM,"muta_site").unsqueeze(0),as_feature_tensor(dna_mean,DNA_DIM,"DNA mean_pooling").unsqueeze(0),1)
        values={spec.name:float(predictions[spec.name][0]) for spec in self.specs}; mean=float(sum(values.values())/len(values)); classification="destabilizing mutation" if mean>=0 else "stabilizing mutation"
        return EnsemblePrediction(sample_id,values,mean,classification)


def collect_dataframe_features(dataframe,protein_dict,dna_dict):
    wt=[]; mut=[]; dna=[]; errors=[]
    for sample_id in dataframe["sample_ID"].astype(str):
        try: w,m,d=extract_sample_features(sample_id,protein_dict,dna_dict)
        except (KeyError,ValueError,TypeError) as error: errors.append("{}: {}".format(sample_id,error)); continue
        wt.append(w); mut.append(m); dna.append(d)
    if errors: raise ValueError("Feature validation failed for {} samples:\n{}".format(len(errors),"\n".join(errors[:20])))
    return torch.stack(wt),torch.stack(mut),torch.stack(dna)


def regression_metrics(true,pred):
    true=np.asarray(true,float); pred=np.asarray(pred,float); pcc=None if len(true)<2 or np.std(true)==0 or np.std(pred)==0 else float(np.corrcoef(true,pred)[0,1])
    return {"sample_size":int(len(true)),"pcc":pcc,"rmse":float(np.sqrt(np.mean((pred-true)**2))),"mae":float(np.mean(np.abs(pred-true)))}


def run_s1345_prediction(dataset_path,protein_feature_path,dna_feature_path,model_root,output_root,device="auto",batch_size=64,overwrite=False):
    dataframe=pd.read_csv(dataset_path,sep="\t"); protein=torch_load_cpu(protein_feature_path); dna=torch_load_cpu(dna_feature_path); wt,mut,dna_tensor=collect_dataframe_features(dataframe,protein,dna)
    ensemble=ProteinDNAMLPEnsemble(model_root,device); predictions=ensemble.predict_tensor_batches(wt,mut,dna_tensor,batch_size); output=Path(output_root); output.mkdir(parents=True,exist_ok=True)
    result=pd.DataFrame({"Model":"Seq-MLP (F-F)","Family":"Seq-MLP","Algorithm":"MLP","Setting":"F-F","Test_Set":"S1345","sample_ID":dataframe["sample_ID"].astype(str),"y_true":pd.to_numeric(dataframe["DDG"])})
    metrics={}
    for spec in ensemble.specs: result[spec.prediction_column]=predictions[spec.name]; metrics[spec.name]=regression_metrics(result["y_true"],predictions[spec.name])
    result["ensemble_pred"]=result[[spec.prediction_column for spec in ensemble.specs]].mean(axis=1); metrics["ensemble_mean"]=regression_metrics(result["y_true"],result["ensemble_pred"])
    csv_path=output/"Seq_MLP_F_F_S1345_ensemble_predictions.csv"; metrics_path=output/"S1345_metrics.json"
    if csv_path.exists() and not overwrite: raise FileExistsError("Output exists: {}. Use --overwrite.".format(csv_path))
    result.to_csv(csv_path,index=False); metrics_path.write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    return result,csv_path,metrics_path


def compare_prediction_files(candidate_path,reference_path,atol=1e-6):
    candidate=pd.read_csv(candidate_path); reference=pd.read_csv(reference_path); columns=["pred_seed46","pred_seed66","pred_seed77","ensemble_pred"]
    merged=candidate[["sample_ID"]+columns].merge(reference[["sample_ID"]+columns],on="sample_ID",suffixes=("_candidate","_reference"),validate="one_to_one")
    report={}
    for column in columns:
        difference=np.abs(merged[column+"_candidate"].to_numpy(float)-merged[column+"_reference"].to_numpy(float)); worst=int(np.argmax(difference))
        report[column]={"sample_count":int(len(merged)),"atol":float(atol),"all_close":bool(np.all(difference<=atol)),"mismatch_count":int(np.sum(difference>atol)),"max_absolute_difference":float(difference.max()),"mean_absolute_difference":float(difference.mean()),"worst_sample_ID":str(merged.iloc[worst]["sample_ID"])}
    return report
