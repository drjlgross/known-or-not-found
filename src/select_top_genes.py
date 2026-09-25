"""Chunk 4: top K induced genes from the rnaseq-de bundle -> data/top_genes.csv.

Rule (CLAUDE.md, revised 2026-09-25 at the Chunk 4 gate): protein-coding genes with a real MGI symbol only;
padj < 1e-10 and log2FC > 0; order by (shrunken) log2FC descending. The first rule (padj < 0.05, order by padj)
was degenerate: 423 genes tie at padj = 0 (float underflow), which dropped Nos2, Il6 and Il1b from the top 50.
Also reports genes excluded by the eligibility rule that would otherwise have ranked in the top K.
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import gene_names  # noqa: E402

K = 50
PADJ_MAX = 1e-10
DE = ROOT / "results/de/lps/tables/de_results.csv"
OUT = ROOT / "data/top_genes.csv"
PLACEHOLDER = re.compile(r"^(?:Gm\d+|\w+Rik)$")

de = pd.read_csv(DE)
gmap = pd.read_csv(ROOT / "data/gene_map.csv")[["gene", "gene_type"]]
de = de.merge(gmap, on="gene", how="left", validate="one_to_one")
assert de["gene_type"].notna().all(), "every DE gene must be in gene_map.csv"
mgi = set(gene_names._table().index)

up = de[(de["padj"] < PADJ_MAX) & (de["log2FoldChange"] > 0)].copy()
up = up.sort_values("log2FoldChange", ascending=False, kind="stable").reset_index(drop=True)


def why_excluded(r) -> str:
    if r["gene_type"] != "protein_coding":
        return f"gene_type={r['gene_type']}"
    if "|" in r["gene"]:
        return "duplicate-symbol suffix"
    if PLACEHOLDER.match(r["gene"]):
        return "Gm/Rik placeholder"
    if r["gene"] not in mgi:
        return "not a current MGI symbol"
    return ""


up["excluded"] = up.apply(why_excluded, axis=1)
elig = up[up["excluded"] == ""]
top = elig.head(K).copy()
top.insert(0, "rank", range(1, len(top) + 1))
top = top[["rank", "gene", "baseMean", "log2FoldChange", "padj"]]
top.to_csv(OUT, index=False)

cut = up.index[up["gene"] == top["gene"].iloc[-1]][0]
skipped = up.loc[:cut][up.loc[:cut, "excluded"] != ""]
print(f"up with padj < {PADJ_MAX:g}: {len(up)}; eligible: {len(elig)}; written: {len(top)} -> {OUT.relative_to(ROOT)}")
print(f"padj == 0 (numeric floor) among written top {K}: {(top['padj'] == 0).sum()}")
print(f"excluded genes that would have ranked within the top {K}: {len(skipped)}")
if len(skipped):
    print(skipped[["gene", "gene_type", "log2FoldChange", "padj", "excluded"]].to_string(index=False))
