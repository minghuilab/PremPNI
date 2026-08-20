"""Strict single-sample and batch inference for the three final RNA-MLPs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import torch

from .mlp_model import DualTowerAffinityMLP


PROTEIN_DIM = 2560
RNA_DIM = 1280
DEFAULT_MODEL_ROOT = (
    Path(os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models"))
    / "mlp" / "protein_rna"
)
OPTIONAL_RESULT_COLUMNS = (
    "pdb_id", "pdb_mutation", "complex_mutation", "Direction",
    "forward_reverse", "Protein", "DNA", "RNA",
)


@dataclass(frozen=True)
class MLPModelSpec:
    split_seed: int
    trial: int
    checkpoint_relative_path: str
    hp_seed: int
    embed_dim: int
    prot_layers: int
    rna_layers: int
    dropout: float

    @property
    def name(self) -> str:
        return "Seed{}_trial{}".format(self.split_seed, self.trial)


FINAL_MODEL_SPECS: Sequence[MLPModelSpec] = (
    MLPModelSpec(21, 3, "RNA_F_F_Seed21/trial_3/best_network.pth", 114514, 512, 1, 1, 0.4283),
    MLPModelSpec(22, 9, "RNA_F_F_Seed22/trial_9/best_network.pth", 114514, 256, 2, 2, 0.3472),
    MLPModelSpec(32, 11, "RNA_F_F_Seed32/trial_11/best_network.pth", 3407, 512, 1, 2, 0.3001),
)


@dataclass(frozen=True)
class EnsemblePrediction:
    sample_id: str
    model_predictions: Dict[str, float]
    mean_ddg: float
    classification: str


def normalize_device(device: str) -> torch.device:
    value = str(device).strip().lower()
    if value == "auto":
        value = "cuda:0" if torch.cuda.is_available() else "cpu"
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


def torch_load_cpu(path: Union[str, Path]):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError("File not found: {}".format(path))
    try:
        return torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        return torch.load(path, map_location="cpu")


def as_feature_tensor(
    value: Union[np.ndarray, torch.Tensor], expected_dim: int, feature_name: str
) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        tensor = value.detach().cpu().to(torch.float32).contiguous()
    else:
        tensor = torch.as_tensor(value, dtype=torch.float32).contiguous()
    if tuple(tensor.shape) != (expected_dim,):
        raise ValueError(
            "{} must have shape ({},), got {}.".format(
                feature_name, expected_dim, tuple(tensor.shape)
            )
        )
    if not torch.isfinite(tensor).all():
        raise ValueError("{} contains NaN or Inf.".format(feature_name))
    return tensor


def extract_sample_features(
    sample_id: str, protein_dict: Mapping, rna_dict: Mapping
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Resolve one sample strictly; no missing feature is replaced with zeros."""
    if sample_id not in protein_dict:
        raise KeyError("Protein features missing sample_ID: {}".format(sample_id))
    if sample_id not in rna_dict:
        raise KeyError("RNA features missing sample_ID: {}".format(sample_id))
    protein_record = protein_dict[sample_id]
    if not isinstance(protein_record, Mapping):
        raise ValueError("Protein record for {} must be a dictionary.".format(sample_id))
    missing = [key for key in ("wt_site", "muta_site") if key not in protein_record]
    if missing:
        raise KeyError("Protein record for {} is missing {}.".format(sample_id, missing))
    rna_record = rna_dict[sample_id]
    if isinstance(rna_record, Mapping):
        if "mean_pooling" not in rna_record:
            raise KeyError("RNA record for {} is missing mean_pooling.".format(sample_id))
        rna_value = rna_record["mean_pooling"]
    else:
        # rinalmo_mean.pt intentionally stores {sample_ID: tensor}.
        rna_value = rna_record
    return (
        as_feature_tensor(protein_record["wt_site"], PROTEIN_DIM, sample_id + ".wt_site"),
        as_feature_tensor(protein_record["muta_site"], PROTEIN_DIM, sample_id + ".muta_site"),
        as_feature_tensor(rna_value, RNA_DIM, sample_id + ".RNA.mean_pooling"),
    )


def load_sample_features(sample_id, protein_feature_path, rna_feature_path):
    protein_dict = torch_load_cpu(protein_feature_path)
    rna_dict = torch_load_cpu(rna_feature_path)
    if not isinstance(protein_dict, Mapping) or not isinstance(rna_dict, Mapping):
        raise ValueError("Protein and RNA feature files must contain dictionaries.")
    return extract_sample_features(sample_id, protein_dict, rna_dict)


def _extract_state_dict(checkpoint, checkpoint_path: Path):
    if not isinstance(checkpoint, Mapping):
        raise ValueError("Checkpoint {} must contain a state dictionary.".format(checkpoint_path))
    for key in ("state_dict", "model_state_dict"):
        if key in checkpoint and isinstance(checkpoint[key], Mapping):
            return checkpoint[key]
    return checkpoint


class ProteinRNAMLPEnsemble:
    """Load the three final F-F checkpoints once and reuse them."""

    def __init__(self, model_root=DEFAULT_MODEL_ROOT, device="cpu", specs=FINAL_MODEL_SPECS):
        self.model_root = Path(model_root)
        self.device = normalize_device(device)
        self.specs = tuple(specs)
        self.models: Dict[str, DualTowerAffinityMLP] = {}
        missing = [self.model_root / spec.checkpoint_relative_path for spec in self.specs
                   if not (self.model_root / spec.checkpoint_relative_path).is_file()]
        if missing:
            raise FileNotFoundError("Missing RNA-MLP checkpoint(s): {}".format(", ".join(map(str, missing))))
        for spec in self.specs:
            model = DualTowerAffinityMLP(
                prot_in_dim=PROTEIN_DIM, prot_out_dim=spec.embed_dim, dna_dim=RNA_DIM,
                prot_layers=spec.prot_layers, dna_layers=spec.rna_layers, dropout=spec.dropout,
            )
            checkpoint_path = self.model_root / spec.checkpoint_relative_path
            state_dict = _extract_state_dict(torch_load_cpu(checkpoint_path), checkpoint_path)
            try:
                model.load_state_dict(state_dict, strict=True)
            except RuntimeError as error:
                raise RuntimeError("Checkpoint {} does not match {}: {}".format(checkpoint_path, spec.name, error)) from error
            model.to(self.device)
            model.eval()
            self.models[spec.name] = model

    def predict(self, sample_id, wt_site, muta_site, rna_mean) -> EnsemblePrediction:
        predictions = self.predict_tensor_batches(
            as_feature_tensor(wt_site, PROTEIN_DIM, "wt_site").unsqueeze(0),
            as_feature_tensor(muta_site, PROTEIN_DIM, "muta_site").unsqueeze(0),
            as_feature_tensor(rna_mean, RNA_DIM, "RNA mean_pooling").unsqueeze(0), 1,
        )
        model_predictions = {spec.name: float(predictions[spec.name][0]) for spec in self.specs}
        mean_ddg = float(sum(model_predictions.values()) / len(model_predictions))
        classification = "destabilizing mutation" if mean_ddg >= 0 else "stabilizing mutation"
        return EnsemblePrediction(sample_id, model_predictions, mean_ddg, classification)

    def predict_tensor_batches(self, wt_sites, muta_sites, rna_means, batch_size=64):
        if batch_size < 1:
            raise ValueError("batch_size must be positive.")
        rows = wt_sites.shape[0]
        expected = ((rows, PROTEIN_DIM), (rows, PROTEIN_DIM), (rows, RNA_DIM))
        actual = (tuple(wt_sites.shape), tuple(muta_sites.shape), tuple(rna_means.shape))
        if actual != expected:
            raise ValueError("Batch feature shapes must be {}, got {}.".format(expected, actual))
        predictions = {spec.name: [] for spec in self.specs}
        with torch.no_grad():
            for start in range(0, rows, batch_size):
                end = min(start + batch_size, rows)
                wt = wt_sites[start:end].to(self.device)
                mut = muta_sites[start:end].to(self.device)
                rna = rna_means[start:end].to(self.device)
                for spec in self.specs:
                    values = self.models[spec.name](wt, mut, rna)
                    if not torch.isfinite(values).all():
                        raise RuntimeError("Model {} produced NaN or Inf.".format(spec.name))
                    predictions[spec.name].append(values.detach().cpu().numpy())
        return {name: np.concatenate(chunks).astype(np.float64, copy=False)
                for name, chunks in predictions.items()}


def collect_dataframe_features(dataframe, protein_dict, rna_dict):
    if "sample_ID" not in dataframe.columns or dataframe["sample_ID"].isna().any():
        raise ValueError("Dataset must contain a non-empty sample_ID column.")
    wt_sites, muta_sites, rna_means, errors = [], [], [], []
    for sample_id in dataframe["sample_ID"].astype(str):
        try:
            wt, mut, rna = extract_sample_features(sample_id, protein_dict, rna_dict)
        except (KeyError, ValueError, TypeError) as error:
            errors.append("{}: {}".format(sample_id, error))
            continue
        wt_sites.append(wt); muta_sites.append(mut); rna_means.append(rna)
    if errors:
        raise ValueError("Feature validation failed for {} sample(s):\n{}".format(len(errors), "\n".join(errors[:20])))
    return torch.stack(wt_sites), torch.stack(muta_sites), torch.stack(rna_means)


def build_original_style_result(dataframe, predictions):
    required = ("sample_ID", "DDG", "PDBTest_Label", "MutationTest_Label")
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: {}".format(missing))
    if len(dataframe) != len(predictions):
        raise ValueError("Prediction count does not match dataset row count.")
    result = dataframe.copy()
    result["true"] = pd.to_numeric(result["DDG"], errors="raise").to_numpy()
    result["pred"] = predictions
    base = ["sample_ID", "true", "pred", "PDBTest_Label", "MutationTest_Label"]
    keep = base + [column for column in OPTIONAL_RESULT_COLUMNS if column in result.columns and column not in base]
    return result[keep].copy()


def split_s604_result(result):
    return {
        "S604": result.copy(),
        "S265": result.loc[result["PDBTest_Label"].astype(str).eq("PDBTest")].copy(),
        "S318": result.loc[result["MutationTest_Label"].astype(str).eq("MutationTest")].copy(),
    }


def regression_metrics(result):
    true = result["true"].to_numpy(dtype=np.float64)
    pred = result["pred"].to_numpy(dtype=np.float64)
    if len(true) == 0:
        return {"sample_size": 0, "pcc": None, "rmse": None, "mae": None}
    pcc = None if len(true) < 2 or np.std(true) == 0 or np.std(pred) == 0 else float(np.corrcoef(true, pred)[0, 1])
    return {"sample_size": int(len(true)), "pcc": pcc,
            "rmse": float(np.sqrt(np.mean((pred - true) ** 2))),
            "mae": float(np.mean(np.abs(pred - true)))}


def run_s604_prediction(dataset_path, protein_feature_path, rna_feature_path,
                        model_root, output_root, device="auto", batch_size=64,
                        overwrite=False):
    dataset_path = Path(dataset_path)
    if not dataset_path.is_file():
        raise FileNotFoundError("Dataset not found: {}".format(dataset_path))
    dataframe = pd.read_csv(dataset_path, sep="\t")
    protein_dict, rna_dict = torch_load_cpu(protein_feature_path), torch_load_cpu(rna_feature_path)
    if not isinstance(protein_dict, Mapping) or not isinstance(rna_dict, Mapping):
        raise ValueError("Protein and RNA feature files must contain dictionaries.")
    wt, mut, rna = collect_dataframe_features(dataframe, protein_dict, rna_dict)
    ensemble = ProteinRNAMLPEnsemble(model_root=model_root, device=device)
    model_predictions = ensemble.predict_tensor_batches(wt, mut, rna, batch_size=batch_size)
    ensemble_prediction = np.mean(np.stack([model_predictions[s.name] for s in ensemble.specs]), axis=0)
    output_root = Path(output_root); output_root.mkdir(parents=True, exist_ok=True)
    written, metrics = {}, {}
    all_predictions = pd.DataFrame({"sample_ID": dataframe["sample_ID"].astype(str)})
    for name, values in list(model_predictions.items()) + [("ensemble_mean", ensemble_prediction)]:
        splits = split_s604_result(build_original_style_result(dataframe, values))
        target_dir = output_root / name; target_dir.mkdir(parents=True, exist_ok=True)
        written[name], metrics[name] = {}, {}
        for split_name, split_df in splits.items():
            path = target_dir / "{}_results.csv".format(split_name)
            if path.exists() and not overwrite:
                raise FileExistsError("Output exists: {}. Use --overwrite.".format(path))
            split_df.to_csv(path, index=False)
            written[name][split_name] = str(path)
            metrics[name][split_name] = regression_metrics(split_df)
        all_predictions[name] = values
    combined_path = output_root / "S604_all_model_predictions.csv"
    metrics_path = output_root / "S604_metrics.json"
    if combined_path.exists() and not overwrite:
        raise FileExistsError("Output exists: {}. Use --overwrite.".format(combined_path))
    all_predictions.to_csv(combined_path, index=False)
    with metrics_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2)
    return {"written": written, "combined_predictions": str(combined_path),
            "metrics": str(metrics_path), "sample_count": int(len(dataframe))}


def compare_prediction_csvs(candidate_path, reference_path, atol=1e-6):
    candidate, reference = pd.read_csv(candidate_path), pd.read_csv(reference_path)
    for label, frame in (("candidate", candidate), ("reference", reference)):
        missing = [column for column in ("sample_ID", "pred") if column not in frame]
        if missing:
            raise ValueError("{} CSV is missing {}.".format(label, missing))
        if frame["sample_ID"].astype(str).duplicated().any():
            raise ValueError("{} CSV contains duplicate sample_ID.".format(label))
    candidate["sample_ID"] = candidate["sample_ID"].astype(str)
    reference["sample_ID"] = reference["sample_ID"].astype(str)
    candidate_ids, reference_ids = set(candidate["sample_ID"]), set(reference["sample_ID"])
    if candidate_ids != reference_ids:
        raise ValueError("sample_ID sets differ; candidate-only={}, reference-only={}.".format(
            sorted(candidate_ids - reference_ids)[:10], sorted(reference_ids - candidate_ids)[:10]))
    merged = candidate[["sample_ID", "pred"]].merge(reference[["sample_ID", "pred"]], on="sample_ID",
                                                       suffixes=("_candidate", "_reference"), validate="one_to_one")
    delta = merged["pred_candidate"].to_numpy(float) - merged["pred_reference"].to_numpy(float)
    absolute = np.abs(delta); worst = int(np.argmax(absolute)) if len(absolute) else None
    return {"candidate": str(candidate_path), "reference": str(reference_path),
            "sample_count": int(len(merged)), "atol": float(atol),
            "all_close": bool(np.all(absolute <= atol)),
            "mismatch_count": int(np.sum(absolute > atol)),
            "max_absolute_difference": float(absolute.max()) if len(absolute) else 0.0,
            "mean_absolute_difference": float(absolute.mean()) if len(absolute) else 0.0,
            "worst_sample_ID": str(merged.iloc[worst]["sample_ID"]) if worst is not None else None}
