# Chunk 4 Report: DE on the real dataset (GSE250273, LPS 4 h vs control 4 h)

**Date:** 2026-09-25
**Status:** ✅ Gate passed, and the ranking decision is made (2026-09-25): **padj < 1e-10, ordered by shrunken log2FC.** `data/top_genes.csv` has been regenerated under that rule (see "Final top 50" at the end). The status bullets below record the gate as reported.
- **Positive controls and PCA: pass.**
- **Backend: pydeseq2, confirmed.**
- **One decision is needed before Chunk 5:** the agreed top-50 ranking rule is degenerate on this dataset (see "Ranking problem"). `data/top_genes.csv` currently follows the agreed rule, pending your call.

## What ran
- **Command:** `src/run_de_lps.sh`, copied into the bundle as `results/de/lps/reproducibility/RUN_COMMAND.sh`.
  - Inputs: `data/counts.csv` and `data/metadata.csv`.
  - Options: `--formula "~ condition" --contrast "condition,LPS,control" --backend pydeseq2 --output results/de/lps/`.
  - ClawBio root on `PYTHONPATH`; caches kept in the project.
- **Provenance in `reproducibility/`:** `stdout.log`, `clawbio_commit.txt`, `pip_freeze.txt`, plus the skill's own `commands.sh`, `environment.yml` and `checksums.sha256`.
- **Samples:** Ctrl01–03 vs. TrtB01–03, 3 vs. 3. Library sizes are 18.3–27.9 M (`tables/qc_summary.csv`).

## Backend confirmation
- `report.md` line 9: `**Backend used**: pydeseq2`.
- `result.json`, `summary.backend_used`: `"pydeseq2"`. The stdout JSON also shows `"backend_used":"pydeseq2"`.
- **Note:** `lfc_shrinkage_applied: true` (coefficient `condition[T.LPS]`). The reported log2FC values are **shrunken** estimates, which moderates noisy fold changes for low-count genes. This applies to every fold change used downstream.
- **Gene filtering:** 55,357 genes before and 13,574 after the skill's low-count filter.

## Gate: positive controls (appropriate for 4 h LPS)

| Gene | baseMean | log2FC (shrunken) | padj |
|---|---|---|---|
| Tnf | 21,548 | 5.87 | 0 (below float precision) |
| Il1b | 68,788 | 12.55 | 1.5e-260 |
| Il6 | 5,661 | 13.68 | 3.2e-60 |
| Cxcl10 | 102,670 | 11.73 | 0 |
| Nos2 | 20,018 | 16.06 | 1.2e-55 |
| Cxcl2 / Ccl4 / Ptgs2 / Nfkbia | — | 9.28 / 8.63 / 10.59 / 5.05 | 0 |
| Acod1 (Irg1) / Il12b / Saa3 | — | 11.62 / 10.79 / 11.77 | 2e-99 / 2e-151 / 7e-202 |

- Every canonical control is induced very strongly.
- Tnf has the smallest fold change of the set. That fits 4 h: Tnf mRNA peaks at about 1–2 h, while Il6, Nos2 and Il1b are still rising at 4 h.
- **PCA** (`figures/pca.png`): PC1 explains **97.1%** of the variance and separates LPS (PC1 ≈ +62) from control (≈ −62). PC2 is 0.8%. There are no outliers.
- **Result: pass.**
- **Overall:** 5,047 genes are significantly up and 4,911 down (padj < 0.05).

## Top 50 (agreed rule) — `data/top_genes.csv`, by `src/select_top_genes.py`
- **Rule:** protein-coding genes with a real MGI symbol; padj < 0.05, log2FC > 0; padj ascending, ties broken by larger log2FC.
- **Counts:** 5,047 significantly up; 4,446 eligible.
- **Excluded genes that would otherwise have been in the top 50 (3):**
  - Mx1 and Mx2: `polymorphic_pseudogene` in GENCODE, because they are nonfunctional in C57BL/6. They are well-known interferon genes, though.
  - AW112010: a lncRNA.

## Ranking problem (decision needed)
**423 of the significantly induced genes have padj = 0**, meaning their p-values fell below the smallest floating-point number (about 1e-308). The skill's output has no test statistic to separate them. So:
- **All 50 selected genes have padj = 0.** The padj criterion does nothing within the list; the tie-break (log2FC) decides everything.
- **Whether a gene reaches padj = 0 depends mostly on expression level and dispersion, not on induction.** The agreed rule therefore drops the most strongly induced canonical genes:

| Gene | Rank under the agreed rule |
|---|---|
| Nos2 (log2FC 16.1) | 1250 |
| Il6 (13.7) | 1199 |
| Il1b (12.6) | 478 |
| Tnf | 60 |

In effect, the agreed rule is "the top log2FC among genes with padj below about 1e-308". That's an arbitrary floating-point threshold.

**Alternative: an explicit threshold, then shrunken log2FC.**

| Rule | Overlap with the current list | New in the list | Lowest log2FC / baseMean in the list |
|---|---|---|---|
| padj < 1e-10, then log2FC | 16/50 | Edn1, Nos2, Il6, Il1b, Il1a, Tnfsf15, Lipg, Saa3, Acod1, Il12b, Col27a1, Rnd1, Tarm1, Cxcl1, … | 8.63 / 98 |
| padj < 1e-50, then log2FC | 23/50 | Nos2, Il6, Il1b, Lipg, Saa3, Acod1, Col27a1, Rnd1, Tarm1, Il27, … | 7.87 / 370 |

(The full lists are reproducible with the snippet in this report's commands section below.)

**Recommendation: padj < 1e-10, then shrunken log2FC.**
- **The threshold is explicit.** Every gene in the list is overwhelmingly significant, so ranking among them by effect size means "most strongly induced", which is what the demo claims.
- **Shrinkage already guards against low-count noise.** The lowest baseMean in the list is 98.
- **It keeps Il6, Il1b and Nos2 in**, so the list looks right to a biologist.
- **It matches the pilot.** Chunk 3's pilot genes (Edn1, Lipg, Col27a1, Rnd1, Tarm1, Tnfsf15) come from this style of ranking.
- **Cost:** the list includes more obscure genes than the current one, so it will probably lean more toward "not found". That's an honest consequence of ranking by induction strength, and the report will state the rule.

## Commands
- `src/run_de_lps.sh`
- `.venv/bin/python src/select_top_genes.py`
- Comparison snippet: the eligible genes (same filter as `select_top_genes.py`) with `padj < thr` and `log2FoldChange > 0`, sorted by `log2FoldChange` descending, `head(50)`.

## Files
- `results/de/lps/`: `report.md`, `result.json`, `tables/{de_results,normalized_counts,qc_summary}.csv`, `figures/{pca,volcano,ma_plot}.png`, `reproducibility/`.
- `data/top_genes.csv`: the agreed rule, pending the ranking decision.
- `src/run_de_lps.sh`, `src/select_top_genes.py`.

## Final top 50 (decided rule: padj < 1e-10, ordered by shrunken log2FC)

`src/select_top_genes.py` (revised) → `data/top_genes.csv`.
- **Counts:** 2,866 genes up with padj < 1e-10; 2,681 eligible.
- **padj = 0:** 16 of the 50.
- **Lowest baseMean:** 98.
- **Excluded genes that would have ranked in the top 50 (3):**
  - U90926 (lncRNA, log2FC 15.3);
  - Cxcl11 (`polymorphic_pseudogene`, 12.6; nonfunctional in C57BL/6);
  - Mir155hg (lncRNA, 10.2).
- **Positive controls in the list:** Nos2 (#2), Il6 (#4), Il1b (#6), Cxcl10 (#10). Tnf (log2FC 5.87) is below the cutoff (#50 is 8.6), which is expected at 4 h.

**The list:** Edn1, Nos2, Shisa3, Il6, Tnfsf15, Il1b, Il1a, Lipg, Saa3, Cxcl10, Acod1, Gbp5, Il12b, Serpinb2, Itgb8, Cd69, Ptgs2, Steap4, Serpina3g, Socs3, Adamts4, Ifi205, Ccl12, Ptx3, Ccl5, Col27a1, Slamf1, Ptges, Il27, Rsad2, Serpina3f, Cxcl9, Hdc, Trim30c, Tmem200b, Cxcl2, Rnd1, Cxcl1, Tarm1, Cxcl3, Ccl17, Rasgrp1, Iigp1, Gbp6, Inhba, Gbp2, Tnfsf4, Mmp13, Bcl2a1a, Ccl4.

**Overlap with the Chunk 3 pilot:** 8 of the 12 pilot genes are in this list (Edn1, Nos2, Tnfsf15, Lipg, Col27a1, Hdc, Rnd1, Tarm1). Slc7a2, Calhm6 and Hcar2 aren't; neither is Tnf.
