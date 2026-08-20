"""Clean inference wrapper around the local HyenaDNA model implementation."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Sequence, Union

import torch

# HyenaDNA inference uses PyTorch only.  Prevent transformers from importing
# TensorFlow/TensorRT and emitting unrelated startup warnings.
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from .hyenadna_model import CharacterTokenizer, HyenaDNAPreTrainedModel
from .processing import DNAChain, HYENADNA_DIM


MODEL_NAME = "hyenadna-large-1m-seqlen"
MODEL_MAX_LENGTH = 1_000_000
DEFAULT_CHECKPOINT_ROOT = Path(
    os.environ.get("PREMPNI_MODEL_ROOT", "/opt/prempni/models")
) / "hyenadna"


def normalize_device(device: str) -> torch.device:
    device = str(device).strip().lower()
    if device.isdigit():
        device = f"cuda:{device}"
    torch_device = torch.device(device)
    if torch_device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("指定了CUDA设备，但当前PyTorch无法使用CUDA。")
    if torch_device.type == "cuda":
        index = torch_device.index or 0
        if index >= torch.cuda.device_count():
            raise RuntimeError(
                f"CUDA设备 {index} 不存在；当前可用GPU数量为 {torch.cuda.device_count()}。"
            )
    return torch_device


class HyenaDNAEmbedder:
    """Load HyenaDNA once and independently embed one or more 5′→3′ chains."""

    def __init__(
        self,
        checkpoint_root: Union[str, Path] = DEFAULT_CHECKPOINT_ROOT,
        device: str = "cuda:0",
    ) -> None:
        self.checkpoint_root = Path(checkpoint_root)
        self.device = normalize_device(device)
        checkpoint = self.checkpoint_root / MODEL_NAME / "weights.ckpt"
        if not checkpoint.is_file():
            raise FileNotFoundError(f"找不到HyenaDNA权重：{checkpoint}")

        print(
            f"正在加载 {MODEL_NAME} 到 {self.device}...",
            file=sys.stderr,
        )
        self.model = HyenaDNAPreTrainedModel.from_pretrained(
            str(self.checkpoint_root),
            MODEL_NAME,
            download=False,
            config=None,
            device=self.device,
            use_head=False,
            n_classes=2,
        )
        self.model.to(self.device)
        self.model.eval()
        self.tokenizer = CharacterTokenizer(
            characters=["A", "C", "G", "T", "N"],
            model_max_length=MODEL_MAX_LENGTH + 2,
            add_special_tokens=False,
            padding_side="left",
        )

    def embed_chain(self, chain: DNAChain) -> torch.Tensor:
        token_ids = self.tokenizer(
            chain.sequence,
            add_special_tokens=True,
        )["input_ids"]
        expected_token_count = len(chain.sequence) + 2
        if len(token_ids) != expected_token_count:
            raise RuntimeError(
                f"DNA链 {chain.chain_id} token数量异常：期望 "
                f"{expected_token_count}，实际 {len(token_ids)}。"
            )

        input_ids = torch.tensor(
            [token_ids],
            dtype=torch.long,
            device=self.device,
        )
        with torch.inference_mode():
            raw_embedding = self.model(input_ids)[0]

        # raw_embedding = [CLS] + real DNA residues + [SEP].  Since web
        # requests are embedded one chain at a time, no batch padding remains.
        embedding = raw_embedding[1 : len(chain.sequence) + 1]
        embedding = embedding.detach().cpu().to(torch.float32).contiguous()
        expected_shape = (len(chain.sequence), HYENADNA_DIM)
        if tuple(embedding.shape) != expected_shape:
            raise RuntimeError(
                f"DNA链 {chain.chain_id} 输出维度异常：期望 {expected_shape}，"
                f"实际 {tuple(embedding.shape)}。"
            )
        if not torch.isfinite(embedding).all():
            raise RuntimeError(f"DNA链 {chain.chain_id} 的特征含有NaN或Inf。")
        return embedding

    def embed_chains(self, chains: Sequence[DNAChain]) -> Dict[str, torch.Tensor]:
        return {chain.chain_id: self.embed_chain(chain) for chain in chains}
