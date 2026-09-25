#!/usr/bin/env bash
# Chunk 5: Round 5 method (CLAUDE.md "Chunk 3 outcome") on all genes in data/top_genes.csv.
# Pilot ledger rows were moved to results/search/pilot5/ledger_pilot.tsv first, so data/paper_ledger.tsv holds
# exactly the top-K genes. Per-gene output: results/search/<gene>/. Log: results/search/_runs/chunk5.log.
set -uo pipefail
cd "$(dirname "$0")/.."
GENES=$(python3 -c "import csv; print(' '.join(r['gene'] for r in csv.DictReader(open('data/top_genes.csv'))))")
src/pc.sh --version
python3 src/search_gene.py --named-query --strict --two-quote --workers 4 -n 25 --outdir results/search $GENES
