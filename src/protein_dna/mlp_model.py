"""Exact dual-tower MLP architecture used by Protein-DNA checkpoints."""

import torch
import torch.nn as nn


class MLPBlock(nn.Module):
    def __init__(self, in_dim, out_dim, num_layers, dropout=0.2):
        super().__init__()
        if num_layers < 1: raise ValueError("num_layers must be positive.")
        dims=[int(in_dim-i*(in_dim-out_dim)/num_layers) for i in range(num_layers)]+[out_dim]
        layers=[]
        for i in range(num_layers):
            layers.extend([nn.Linear(dims[i],dims[i+1]),nn.LeakyReLU(negative_slope=0.1),nn.Dropout(dropout)])
        self.net=nn.Sequential(*layers); self._init_weights()

    def _init_weights(self):
        for module in self.net:
            if isinstance(module,nn.Linear):
                nn.init.kaiming_uniform_(module.weight,mode="fan_in",nonlinearity="leaky_relu")
                if module.bias is not None: nn.init.zeros_(module.bias)

    def forward(self,inputs): return self.net(inputs)


class DualTowerAffinityMLP(nn.Module):
    def __init__(self,prot_in_dim=1280,prot_out_dim=256,dna_dim=256,prot_layers=3,dna_layers=2,dropout=0.3):
        super().__init__(); self.prot_norm=nn.LayerNorm(prot_in_dim); self.prot_branch=MLPBlock(prot_in_dim,prot_out_dim,prot_layers,dropout); self.dna_norm=nn.LayerNorm(dna_dim); self.dna_branch=MLPBlock(dna_dim,dna_dim,dna_layers,dropout)
        fused_dim=prot_out_dim*4+dna_dim; mid1=fused_dim//2; mid2=mid1//2
        self.prediction_head=nn.Sequential(nn.Linear(fused_dim,mid1),nn.LayerNorm(mid1),nn.LeakyReLU(negative_slope=0.1),nn.Dropout(dropout),nn.Linear(mid1,mid2),nn.LeakyReLU(negative_slope=0.1),nn.Dropout(dropout),nn.Linear(mid2,1)); self._init_head_weights()

    def _init_head_weights(self):
        for module in self.prediction_head:
            if isinstance(module,nn.Linear):
                nn.init.kaiming_uniform_(module.weight,mode="fan_in",nonlinearity="leaky_relu")
                if module.bias is not None: nn.init.zeros_(module.bias)

    def forward(self,wt_site,muta_site,dna):
        wt=self.prot_branch(self.prot_norm(wt_site)); muta=self.prot_branch(self.prot_norm(muta_site))
        protein=torch.cat([wt,muta,muta-wt,muta*wt],dim=-1); dna_feature=self.dna_branch(self.dna_norm(dna))
        return self.prediction_head(torch.cat([protein,dna_feature],dim=-1)).squeeze(-1)
