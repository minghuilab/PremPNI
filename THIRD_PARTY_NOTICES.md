# Third-Party Notices

PremPNI uses third-party software and pretrained model assets. Those components
are not relicensed under the PremPNI Academic Non-Commercial License and remain
subject to their original terms.

| Component | Use in PremPNI | License | Upstream |
|---|---|---|---|
| ESM / ESM-2 | Protein representation | MIT | https://github.com/facebookresearch/esm |
| ESM-DBP | Protein-DNA protein representation | MIT | https://github.com/wwzll123/ESM-DBP |
| HyenaDNA | DNA representation | Apache-2.0 | https://github.com/HazyResearch/hyena-dna |
| RiNALMo | RNA representation | Apache-2.0 | https://github.com/lbcb-sci/RiNALMo |
| PyTorch / torchvision | Neural-network runtime | BSD-style licenses | https://pytorch.org/ |
| Transformers | HyenaDNA support code | Apache-2.0 | https://github.com/huggingface/transformers |
| einops | Tensor operations | MIT | https://github.com/arogozhnikov/einops |
| OmegaConf | HyenaDNA checkpoint configuration | BSD-3-Clause | https://github.com/omry/omegaconf |

License texts for the bundled pretrained-model projects are under
`third_party_licenses/`. License files for Python runtime packages are also
retained in their original `site-packages/*dist-info` directories inside the
image. Users must follow the citation and attribution requests documented by
each upstream project.

The PremPNI maintainers make no representation that the table replaces legal
review. Before making the image public or using it commercially, re-check the
current licenses and model-weight distribution terms at the upstream sources.
