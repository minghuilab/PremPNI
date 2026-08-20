# Vendored runtime

This directory contains the pure-Python RiNALMo 1.0.0 source used by the
`gnn_pyg` compatibility wrapper. The FlashAttention-specific attention module
is replaced by a numerically equivalent PyTorch implementation so the existing
PyTorch 2.0.1+cu117 environment does not need a compiled `flash_attn` extension.
