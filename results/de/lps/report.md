# ClawBio RNA-seq Differential Expression Report

**Date**: 2026-09-25 14:52 UTC
**Samples**: 6
**Genes (pre-filter)**: 55357
**Genes (post-filter)**: 13574
**Formula**: `~ condition`
**Contrast**: `condition,LPS,control`
**Backend used**: `pydeseq2`
**LFC shrinkage**: `applied`
**LFC shrinkage coefficient**: `condition[T.LPS]`


## Pre-DE QC + PCA

- QC summary: `tables/qc_summary.csv`
- PCA figure: `figures/pca.png`

## Differential Expression

- Full results: `tables/de_results.csv`
- Volcano plot: `figures/volcano.png`
- MA plot: `figures/ma_plot.png`

### Top Genes (by adjusted p-value)

| Gene | log2FoldChange | padj |
|---|---:|---:|
| Golga3 | 2.515 | 0.000e+00 |
| Foxp4 | 4.765 | 0.000e+00 |
| Tlk2 | 2.905 | 0.000e+00 |
| Acsl1 | 3.341 | 0.000e+00 |
| Slc44a1 | 2.437 | 0.000e+00 |
| Snx10 | 3.380 | 0.000e+00 |
| Tax1bp1 | 3.086 | 0.000e+00 |
| Tgfbr1 | -2.883 | 0.000e+00 |
| Lcn2 | 6.604 | 0.000e+00 |
| Prkx | 2.677 | 0.000e+00 |

## Reproducibility

- Commands: `reproducibility/commands.sh`
- Environment: `reproducibility/environment.yml`
- Checksums: `reproducibility/checksums.sha256`

## Disclaimer

ClawBio is a research and educational tool. It is not a medical device and does not provide clinical diagnoses. Consult a healthcare professional before making any medical decisions.
