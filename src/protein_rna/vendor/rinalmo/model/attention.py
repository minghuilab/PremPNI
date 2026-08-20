"""Attention layers compatible with the upstream RiNALMo state dictionary.

This vendored module intentionally has no dependency on the compiled
``flash_attn`` extension. ``FlashMultiHeadSelfAttention`` retains the upstream
parameter names (``Wqkv`` and ``out_proj``), but evaluates the same operation
with ordinary PyTorch tensor operations.
"""

import math

import torch
from torch import nn

from rinalmo.model.rope import RotaryPositionEmbedding


def dot_product_attention(
    q, k, v, attn_mask=None, key_pad_mask=None, dropout=None
):
    scale = math.sqrt(q.shape[-1])
    attn = torch.matmul(q, k.transpose(-1, -2)) / scale
    if attn_mask is not None:
        attn = attn.masked_fill(attn_mask, float("-inf"))
    if key_pad_mask is not None:
        attn = attn.masked_fill(
            key_pad_mask.unsqueeze(1).unsqueeze(2), float("-inf")
        )
    attn = attn.softmax(dim=-1)
    if dropout is not None:
        attn = dropout(attn)
    return torch.matmul(attn, v), attn


class MultiHeadAttention(nn.Module):
    def __init__(
        self,
        c_in,
        num_heads,
        attention_dropout=0.0,
        use_rot_emb=True,
        bias=False,
    ):
        super().__init__()
        if c_in % num_heads != 0:
            raise ValueError("Embedding size must be divisible by head count")
        self.c_in = c_in
        self.num_heads = num_heads
        self.c_head = c_in // num_heads
        self.use_rot_emb = use_rot_emb
        if use_rot_emb:
            self.rotary_emb = RotaryPositionEmbedding(self.c_head)
        self.to_q = nn.Linear(c_in, c_in, bias=bias)
        self.to_k = nn.Linear(c_in, c_in, bias=bias)
        self.to_v = nn.Linear(c_in, c_in, bias=bias)
        self.attention_dropout = nn.Dropout(p=attention_dropout)
        self.out_proj = nn.Linear(c_in, c_in, bias=bias)

    def forward(self, q, k, v, attn_mask=None, key_pad_mask=None):
        batch_size = q.shape[0]
        q = self.to_q(q).view(
            batch_size, -1, self.num_heads, self.c_head
        ).transpose(1, 2)
        k = self.to_k(k).view(
            batch_size, -1, self.num_heads, self.c_head
        ).transpose(1, 2)
        v = self.to_v(v).view(
            batch_size, -1, self.num_heads, self.c_head
        ).transpose(1, 2)
        if self.use_rot_emb:
            q, k = self.rotary_emb(q, k)
        output, attn = dot_product_attention(
            q,
            k,
            v,
            attn_mask,
            key_pad_mask,
            self.attention_dropout,
        )
        output = output.transpose(1, 2).contiguous().view(
            batch_size, -1, self.c_in
        )
        return self.out_proj(output), attn


class MultiHeadSelfAttention(nn.Module):
    def __init__(
        self,
        c_in,
        num_heads,
        attention_dropout=0.0,
        use_rot_emb=True,
        bias=False,
    ):
        super().__init__()
        self.mh_attn = MultiHeadAttention(
            c_in, num_heads, attention_dropout, use_rot_emb, bias
        )

    def forward(self, x, attn_mask=None, key_pad_mask=None):
        return self.mh_attn(x, x, x, attn_mask, key_pad_mask)


class FlashMultiHeadSelfAttention(nn.Module):
    """Packed-QKV attention with upstream-compatible parameter names."""

    def __init__(
        self,
        embed_dim,
        num_heads,
        attention_dropout=0.0,
        causal=False,
        use_rot_emb=True,
        bias=False,
    ):
        super().__init__()
        if embed_dim % num_heads != 0:
            raise ValueError("Embedding size must be divisible by head count")
        if causal:
            raise ValueError("The RiNALMo encoder is non-causal")
        self.embed_dim = embed_dim
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        self.use_rot_emb = use_rot_emb
        if use_rot_emb:
            self.rotary_emb = RotaryPositionEmbedding(self.head_dim)
            # The upstream FlashAttention rotary buffers are non-persistent.
            self.rotary_emb._non_persistent_buffers_set.add("inv_freq")
        self.Wqkv = nn.Linear(embed_dim, embed_dim * 3, bias=bias)
        self.attention_dropout = nn.Dropout(p=attention_dropout)
        self.out_proj = nn.Linear(embed_dim, embed_dim, bias=bias)

    def forward(
        self, x, key_padding_mask=None, return_attn_probs=False
    ):
        batch_size, seq_len, _ = x.shape
        qkv = self.Wqkv(x).view(
            batch_size,
            seq_len,
            3,
            self.num_heads,
            self.head_dim,
        )
        q, k, v = qkv.unbind(dim=2)
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        if self.use_rot_emb:
            q, k = self.rotary_emb(q, k)

        # In the upstream flash path True means a real (non-padding) token.
        padding_mask = (
            torch.logical_not(key_padding_mask)
            if key_padding_mask is not None
            else None
        )
        output, attn = dot_product_attention(
            q,
            k,
            v,
            key_pad_mask=padding_mask,
            dropout=self.attention_dropout,
        )
        output = output.transpose(1, 2).contiguous().view(
            batch_size, seq_len, self.embed_dim
        )
        output = self.out_proj(output)
        return output, (attn if return_attn_probs else None)
