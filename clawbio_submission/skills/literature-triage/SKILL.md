---
name: literature-triage
description: >-
  Sort a ranked differential-expression gene list into "established", "limited" and "not found in the top N"
  literature bins for a stimulus (v0.1: LPS / bacterial infection), using one full-text search per gene, a strict
  own-data relevance judgment, deterministic name and stimulus checks, and a per-paper provenance ledger.
license: MIT
metadata:
  version: "0.1.0"
  author: known-or-not-found hackathon team
  domain: literature
  tags:
    - literature
    - differential-expression
    - lps
    - macrophage
    - provenance
  inputs:
    - name: input_file
      type: file
      format:
        - csv
      description: Ranked gene list with a 'gene' column (optional log2FoldChange, padj), e.g. rnaseq-de output filtered to top K
      required: true
    - name: gene_names
      type: file
      format:
        - json
      description: gene -> list of names/aliases (MGI + HGNC ortholog names) and '<gene>__official' official name
      required: true
  outputs:
    - name: report
      type: file
      format:
        - md
      description: Bin summary and per-gene table, with the "not found is not novel" caveat
    - name: result
      type: file
      format:
        - json
      description: Machine-readable bins and counts
    - name: ledger
      type: file
      format:
        - tsv
      description: One row per paper per gene (query, search id, date, rank, paper id, title, verdict, status)
  dependencies:
    python: ">=3.10"
    packages: []
  demo_data:
    - path: examples/demo_cache/
      description: Cached Paperclip search + judge outputs for 4 genes (Nos2, Hdc, Tarm1, Lipg) from GSE250273, 2026-09-25
  endpoints:
    cli: python skills/literature-triage/literature_triage.py --input {input_file} --gene-names {gene_names} --output {output_dir}
  openclaw:
    requires:
      bins:
        - python3
    always: false
    emoji: "📚"
    homepage: https://github.com/ClawBio/ClawBio
    os:
      - darwin
      - linux
    install: []
    trigger_keywords:
      - which DE genes are already known
      - literature triage gene list
      - established vs not found in literature
      - LPS induced genes literature
---

# 📚 Literature Triage

Sort a differential-expression gene list into **established**, **limited** and **not found in the top N** literature
bins, with every count traceable to a saved search and a paper.

## Trigger

**Fire when:** the user has a ranked DE gene list (e.g. from `rnaseq-de`) and asks which genes are already known
to respond to the stimulus, which are thinly studied, or which weren't found in the literature.

**Do NOT fire when:** the user wants a literature *summary* of a topic (use `lit-synthesizer` / `pubmed-summariser`),
pathway enrichment, or a novelty claim. This skill never claims novelty.

## Why This Exists

Checking 50 genes by hand against the literature takes days, and ad-hoc searches leave no record. This skill runs
one fixed search per gene, judges each paper with a strict own-data question, and records every paper in a ledger,
so the output is auditable and the "not found" caveat is explicit.

## Core Capabilities

1. One full-text search per gene: `"<Symbol> (<official name>) LPS macrophage"`, top N = 25 (pmc, biorxiv, medrxiv, arxiv).
2. A structured yes/no judgment per paper, with a result quote and an optional context quote (methods or legend).
3. Deterministic checks: a yes is downgraded to no unless the quotes name the gene (MGI + HGNC ortholog names; Greek
   letters and PDF marks normalized) **and** name LPS or a bacterial infection.
4. A per-paper provenance ledger; counts and bins derived from it by script.

## Scope

**One skill, one task:** literature bins for a ranked gene list, for one stimulus (v0.1: LPS / bacterial infection).
It does not run DE, rank genes, or judge biological significance.

## Input Formats

| Format | Extension | Required fields | Example |
|---|---|---|---|
| Gene list | `.csv` | `gene` (ranked); optional `log2FoldChange`, `padj` | `examples/demo_de_results.csv` |
| Gene names | `.json` | `gene` → list of names; `<gene>__official` → official name | `examples/demo_gene_names.json` |

## Workflow

1. **Validate:** the input has a `gene` column; every gene has names in `--gene-names`.
2. **Search:** one Paperclip search per gene; the full ranked parent set goes into the ledger **before** judging.
3. **Judge:** `paperclip map` with a JSON schema (answer, evidence, context).
4. **Check:** name and stimulus checks, applied by script; the model's own answer is kept as `model_answer`.
5. **Count and bin** from the ledger: established ≥ 3 · limited 1–2 · not found in top N = 0 · search error.
6. **Report:** `report.md`, `result.json`, `tables/`, `genes/<gene>/verdicts.csv`, `reproducibility/`.

## CLI Reference

```bash
# Demo: offline, no account (replays cached outputs for 4 genes)
python skills/literature-triage/literature_triage.py --demo --output /tmp/lit_triage_demo

# Live: needs the authenticated `paperclip` CLI on PATH
python skills/literature-triage/literature_triage.py \
  --input top_genes.csv --gene-names gene_names.json --top-k 50 -n 25 --output /tmp/lit_triage
```

## Demo

`--demo` replays cached Paperclip outputs (search results + judge answers from 2026-09-25) for Nos2, Hdc, Tarm1 and
Lipg from GSE250273 (mouse BMDM, LPS 4 h). The checks, ledger, counts and report run for real. There are no network
calls and no account is needed.

## Algorithm / Methodology

- **Question (fixed):** does the paper report its own data showing the gene's expression changes in response to LPS or
  bacterial infection vs. unstimulated controls? No for other stimuli, no-change results, baselines or statements about
  other work. The full text is in `reproducibility/question.txt`.
- **Name check:** word-bounded match of any MGI or HGNC ortholog name in evidence + context, after normalization
  (IL-1β → IL-1b). This rejects look-alikes (HDAC3 for Hdc, CXCL12 for Ccl12).
- **Stimulus check:** the quotes must name LPS, endotoxin, infection, sepsis or a bacterial genus.
- **Primary number:** the qualifying-paper count. The rate (count ÷ N) is never used for binning, because it penalizes
  heavily studied genes.

## Example Queries

- "Which of my top 50 LPS-induced genes are already established in the literature?"
- "Triage this DE gene list against the LPS literature and show me the ones that weren't found."

## Example Output

```
| gene  | log2FC | qualifying count | yes before checks | paper errors | bin                |
|-------|--------|------------------|-------------------|--------------|--------------------|
| Nos2  | 16.06  | 20               | 22                | 1            | established        |
| Hdc   | 9.51   | 2                | 9                 | 0            | limited            |
| Tarm1 | 9.26   | 1                | 2                 | 0            | limited            |
| Lipg  | 12.16  | 0                | 0                 | 0            | not found in top N |
```

Hdc shows the checks at work: 7 of the model's 9 yeses were HDAC papers (look-alike genes), downgraded by script.

## Summary

Of a ranked gene list, the skill reports how many genes have established literature support for the stimulus, how
many have limited support, and how many were not found in the top N results for their query.

## Output Structure

```
output_dir/
├── report.md                  # bins, per-gene table, caveats
├── result.json                # bins and counts
├── tables/
│   ├── paper_ledger.tsv       # one row per paper per gene (source of every count)
│   └── gene_bins.csv
├── genes/<gene>/
│   ├── verdicts.csv           # model answer, quotes, matched names/stimulus, downgrade reason
│   └── map_answers.txt        # raw judge export
└── reproducibility/
    ├── commands.sh
    └── question.txt           # exact question and JSON schema
```

## Dependencies

- Python ≥ 3.10, standard library only.
- **Live mode only:** the `paperclip` CLI, authenticated (≥ 0.7.91). `--demo` needs nothing else.

## Gotchas

- **"Not found" is not "novel".** It means not found in the top N results for this query on this date.
- **The judge is a model and errs toward over-counting.** Hand grading of 22 yes calls found about 86% precision, and
  that grading isn't finished. Failure modes: background statements, knockout-vs-wild-type comparisons, other stimuli.
  Bins at 1–3 should be hand-confirmed.
- **The checks also drop real papers:** abbreviated lists ("CCL2, 12, and 17"), short aliases (Bcl2a1 "A1", below
  the 4-character minimum), protein-complex names ("integrin αvβ8" for Itgb8). The `yes_before_checks` column shows how
  much the checks moved each gene.
- **Cell type isn't restricted.** A dendritic-cell or in vivo result counts. If "in this context" must mean
  macrophages, counts will be lower. This is still an open design question.
- **Preprint and published versions** of one study can both count. Dedupe by title before reporting.
- **Paperclip auto-updates,** and one update (0.7.89) broke `map --output-schema` until a server-side fix. Check the
  version in `reproducibility/` on every live run.
- **The query and question are LPS-specific in v0.1.** Other stimuli need a new question, stimulus pattern and validation.

## Safety

- **Local-first caveat:** live mode sends gene symbols and the fixed question to the Paperclip service, which is not
  a public database like PubMed. No patient or expression data leave the machine; only gene names do.
- No credentials in code. Authentication belongs to the user's Paperclip CLI.
- The skill refuses a non-empty output directory, so earlier runs are never overwritten.

## Agent Boundary

The agent runs the skill and relays the bins **with the caveats**. It must not describe "not found" genes as novel
or unstudied, must not change counts by hand, and must not present bins as ground truth without hand grading.

## Integration with Bio Orchestrator

Downstream of `rnaseq-de`: take `de_results.csv`, select the top K induced genes (e.g. padj < 1e-10, ordered by
log2FC, protein-coding only), and pass them as `--input`. Chains with `lit-synthesizer` for deep reading of the
established genes.

## Maintenance

v0.1.0 (2026-09-25). Built and validated on GSE250273 (LPS 4 h vs. control, mouse BMDM). Blind hand grading is in
progress; precision and false-negative rates will be updated when it finishes.

## Citations

- GSE250273 (NCBI GEO): mouse BMDM, LPS 4 h vs. time-matched control.
- MGI marker list (MRK_List2.rpt) and HGNC complete set, for gene names.
- Paperclip CLI (search and map), used in live mode.
