# ClawBio RNA-seq Differential Expression Report

**Date**: 2026-09-24 17:02 UTC
**Samples**: 6
**Genes (pre-filter)**: 10
**Genes (post-filter)**: 10
**Formula**: `~ batch + condition`
**Contrast**: `condition,treated,control`
**Backend used**: `pydeseq2`
**LFC shrinkage**: `applied`
**LFC shrinkage coefficient**: `condition[T.treated]`


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
| GeneA | 3.289 | 3.325e-82 |
| GeneB | -2.485 | 4.273e-78 |
| GeneE | 2.561 | 1.083e-17 |
| GeneJ | 2.286 | 1.464e-15 |
| GeneF | -0.059 | 9.931e-02 |
| GeneH | -0.086 | 4.106e-01 |
| GeneC | 1.474 | 6.823e-01 |
| GeneI | 1.506 | 9.502e-01 |
| GeneD | -0.077 | 9.635e-01 |
| GeneG | 0.144 | 9.635e-01 |

## Reproducibility

- Commands: `reproducibility/commands.sh`
- Environment: `reproducibility/environment.yml`
- Checksums: `reproducibility/checksums.sha256`

## Disclaimer

ClawBio is a research and educational tool. It is not a medical device and does not provide clinical diagnoses. Consult a healthcare professional before making any medical decisions.
