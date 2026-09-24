"""Build skill-format counts + metadata for GSE250273: WT BMDM, LPS 4 h (TrtB01-03) vs time-matched control (Ctrl01-03).

Inputs (data/raw/; sha256 in data/raw/download_checksums.sha256):
  GSE250273_genecount.txt.gz        featureCounts v2.0.0 raw counts (gene_id = versioned GENCODE vM29 IDs)
  GSE250273_series_matrix.txt.gz    sample title / GSM / description / treatment
  gencode.vM29.annotation.gtf.gz    Ensembl -> symbol (the annotation the counts were built on; GRCm39)

The column -> sample mapping comes ONLY from the series matrix !Sample_description field
(e.g. "TrtB01_4h" -> count column "TrtB01"). Marker genes are printed as a sanity check, not used for mapping.

Outputs (data/):
  counts.csv     genes x 6 samples; first column `gene` = MGI symbol (mouse casing, e.g. Tnf)
  metadata.csv   sample_id, condition (control|LPS), count_column, gsm, geo_title, geo_description
  gene_map.csv   gene (as written in counts.csv) -> ensembl_id, gene_name, gene_type, duplicated_symbol

Run: .venv/bin/python src/prep_dataset.py
"""
import gzip
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

# Selected samples, keyed by GEO !Sample_description. Expected title/treatment are asserted against GEO.
SELECTED = {
    "Ctrl01_4h": ("ctrl_1", "control", "BMDM cells, Control, 4h,WT, replicate #1", "Control"),
    "Ctrl02_4h": ("ctrl_2", "control", "BMDM cells, Control, 4h,WT, replicate #2", "Control"),
    "Ctrl03_4h": ("ctrl_3", "control", "BMDM cells, Control, 4h,WT, replicate #3", "Control"),
    "TrtB01_4h": ("lps_1", "LPS", "BMDM cells, LPS stimulated, 4h, WT, replicate #1", "LPS"),
    "TrtB02_4h": ("lps_2", "LPS", "BMDM cells, LPS stimulated, 4h, WT, replicate #2", "LPS"),
    "TrtB03_4h": ("lps_3", "LPS", "BMDM cells, LPS stimulated, 4h, WT, replicate #3", "LPS"),
}
MARKERS = ["Tnf", "Il1b", "Il6", "Cxcl10", "Nos2", "Tsc22d3", "Fkbp5", "Actb"]


def fail(msg: str) -> None:
    sys.exit(f"MAPPING/INPUT ERROR: {msg}")


def series_matrix_samples(path: Path) -> pd.DataFrame:
    cols = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            key, *vals = line.rstrip("\n").split("\t")
            vals = [v.strip('"') for v in vals]
            if key in ("!Sample_title", "!Sample_geo_accession", "!Sample_description"):
                cols[key[len("!Sample_"):]] = vals
            elif key == "!Sample_characteristics_ch1" and vals and ":" in vals[0]:
                tag = vals[0].split(":")[0]
                cols[tag] = [v.split(": ", 1)[1] for v in vals]
    return pd.DataFrame(cols)


def gtf_genes(path: Path) -> pd.DataFrame:
    rows = []
    with gzip.open(path, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.split("\t", 8)
            if f[2] != "gene":
                continue
            attr = f[8]
            rows.append({
                "ensembl_id": re.search(r'gene_id "([^"]+)"', attr).group(1),
                "gene_name": re.search(r'gene_name "([^"]+)"', attr).group(1),
                "gene_type": re.search(r'gene_type "([^"]+)"', attr).group(1),
            })
    return pd.DataFrame(rows).set_index("ensembl_id")


def main() -> None:
    raw = pd.read_csv(RAW / "GSE250273_genecount.txt.gz", sep="\t", comment="#", index_col=0)
    counts_all = raw.iloc[:, 5:]  # drop Chr, Start, End, Strand, Length

    # --- deterministic mapping from the series matrix -------------------------------------------
    sm = series_matrix_samples(RAW / "GSE250273_series_matrix.txt.gz")
    if sm["description"].duplicated().any():
        fail("duplicate !Sample_description values in series matrix")
    sm = sm.set_index("description")
    sm["count_column"] = sm.index.str.replace(r"_(4h|24h)$", "", regex=True)

    # Every GEO description must map to exactly one count column, and vice versa.
    if set(sm["count_column"]) != set(counts_all.columns):
        fail(f"series-matrix descriptions {sorted(sm['count_column'])} != count columns {sorted(counts_all.columns)}")

    # Arm prefixes must be internally consistent across all 24 samples (catches a shifted mapping).
    prefix_to_treatment = sm.groupby(sm["count_column"].str.extract(r"^([A-Za-z]+)")[0])["treatment"].unique()
    for prefix, treatments in prefix_to_treatment.items():
        if len(treatments) != 1:
            fail(f"prefix {prefix} maps to several treatments: {list(treatments)}")

    for desc, (_, _, want_title, want_treat) in SELECTED.items():
        if desc not in sm.index:
            fail(f"{desc} not found in series matrix")
        r = sm.loc[desc]
        if r["title"] != want_title:
            fail(f"{desc}: title {r['title']!r} != expected {want_title!r}")
        if r["treatment"] != want_treat:
            fail(f"{desc}: treatment {r['treatment']!r} != expected {want_treat!r}")
        if r["genotype"] != "WT" or not desc.endswith("_4h") or "4h" not in r["title"]:
            fail(f"{desc}: not a WT 4 h sample ({r['title']!r}, genotype {r['genotype']!r})")

    cols = [sm.loc[d, "count_column"] for d in SELECTED]
    counts = counts_all[cols].copy()
    vals = counts.to_numpy()
    if not (np.issubdtype(vals.dtype, np.integer) and (vals >= 0).all()):
        fail("counts are not raw non-negative integers")
    counts.columns = [SELECTED[d][0] for d in SELECTED]

    # --- Ensembl -> symbol via GENCODE vM29 ------------------------------------------------------
    ann = gtf_genes(RAW / "gencode.vM29.annotation.gtf.gz")
    missing = counts.index.difference(ann.index)
    if len(missing):
        fail(f"{len(missing)} count-file gene IDs absent from vM29 GTF, e.g. {list(missing[:5])}")
    gm = ann.loc[counts.index].copy()
    gm.index.name = "ensembl_id"
    gm["duplicated_symbol"] = gm["gene_name"].duplicated(keep=False)
    # Symbols shared by several gene IDs: the oldest (lowest-numbered) Ensembl accession keeps the plain
    # symbol -- in vM29 that is the canonical locus, the newer IDs being readthrough/fragment models.
    # The others get "|<ensembl_id>" appended so the join key stays unique. Annotation-only rule, no counts.
    acc_num = gm.index.str.extract(r"ENSMUSG(\d+)", expand=False).astype(int)
    gm["_acc"] = acc_num.to_numpy()
    oldest = gm.groupby("gene_name")["_acc"].transform("min") == gm["_acc"]
    gm["gene"] = np.where(oldest, gm["gene_name"], gm["gene_name"] + "|" + gm.index)
    gm = gm.drop(columns="_acc")
    assert gm["gene"].is_unique

    counts.index = gm["gene"].to_numpy()
    counts.index.name = "gene"
    counts.to_csv(OUT / "counts.csv")
    gm.reset_index()[["gene", "ensembl_id", "gene_name", "gene_type", "duplicated_symbol"]].to_csv(
        OUT / "gene_map.csv", index=False)

    meta = pd.DataFrame([
        {"sample_id": sid, "condition": cond, "count_column": sm.loc[d, "count_column"],
         "gsm": sm.loc[d, "geo_accession"], "geo_title": sm.loc[d, "title"], "geo_description": d}
        for d, (sid, cond, _, _) in SELECTED.items()
    ])
    meta.to_csv(OUT / "metadata.csv", index=False)

    # --- sanity check only (not used for mapping) ------------------------------------------------
    print(f"counts.csv: {counts.shape[0]} genes x {counts.shape[1]} samples; "
          f"{int(gm['duplicated_symbol'].sum())} genes in {gm.loc[gm['duplicated_symbol'], 'gene_name'].nunique()} "
          f"duplicated-symbol groups ({int(gm['gene'].str.contains('|', regex=False).sum())} suffixed)")
    print("library sizes (M):", (counts.sum(axis=0) / 1e6).round(1).to_dict())
    print(counts.loc[[m for m in MARKERS if m in counts.index]].to_string())


if __name__ == "__main__":
    main()
