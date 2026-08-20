"""Exact dual-tower MLP architecture used by the Protein-RNA checkpoints."""

import torch
import torch.nn as nn


class MLPBlock(nn.Module):
    def __init__(self, in_dim, out_dim, num_layers, dropout=0.2):
        super().__init__()
        if num_layers < 1:
            raise ValueError("num_layers must be positive.")
        dims = [
            int(in_dim - index * (in_dim - out_dim) / num_layers)
            for index in range(num_layers)
        ]
        dims.append(out_dim)
        layers = []
        for index in range(num_layers):
            layers.extend(
                [
                    nn.Linear(dims[index], dims[index + 1]),
                    nn.LeakyReLU(negative_slope=0.1),
                    nn.Dropout(dropout),
                ]
            )
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self):
        for module in self.net:
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(
                    module.weight, mode="fan_in", nonlinearity="leaky_relu"
                )
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, inputs):
        return self.net(inputs)


class DualTowerAffinityMLP(nn.Module):
    """Keep historical dna_* parameter names for checkpoint compatibility."""

    def __init__(
        self,
        prot_in_dim=2560,
        prot_out_dim=256,
        dna_dim=1280,
        prot_layers=3,
        dna_layers=2,
        dropout=0.3,
    ):
        super().__init__()
        self.prot_norm = nn.LayerNorm(prot_in_dim)
        self.prot_branch = MLPBlock(
            prot_in_dim, prot_out_dim, prot_layers, dropout
        )
        self.dna_norm = nn.LayerNorm(dna_dim)
        self.dna_branch = MLPBlock(dna_dim, dna_dim, dna_layers, dropout)

        fused_dim = prot_out_dim * 4 + dna_dim
        mid_dim1 = fused_dim // 2
        mid_dim2 = mid_dim1 // 2
        self.prediction_head = nn.Sequential(
            nn.Linear(fused_dim, mid_dim1),
            nn.LayerNorm(mid_dim1),
            nn.LeakyReLU(negative_slope=0.1),
            nn.Dropout(dropout),
            nn.Linear(mid_dim1, mid_dim2),
            nn.LeakyReLU(negative_slope=0.1),
            nn.Dropout(dropout),
            nn.Linear(mid_dim2, 1),
        )
        self._init_head_weights()

    def _init_head_weights(self):
        for module in self.prediction_head:
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(
                    module.weight, mode="fan_in", nonlinearity="leaky_relu"
                )
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, wt_site, muta_site, rna):
        wt_feat = self.prot_branch(self.prot_norm(wt_site))
        muta_feat = self.prot_branch(self.prot_norm(muta_site))
        protein_fused = torch.cat(
            [wt_feat, muta_feat, muta_feat - wt_feat, muta_feat * wt_feat],
            dim=-1,
        )
        # Parameter names remain dna_* because the trained state_dict uses them.
        rna_feat = self.dna_branch(self.dna_norm(rna))
        return self.prediction_head(
            torch.cat([protein_fused, rna_feat], dim=-1)
        ).squeeze(-1)
