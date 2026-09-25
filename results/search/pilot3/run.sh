#!/usr/bin/env bash
# Chunk 3 Round 3 (2026-09-25): chosen setup (named query + strict + evidence-name check) on the
# 12 pilot genes, after the Paperclip server-side map --output-schema fix. CLI: paperclip 0.7.89.
#   n25 -> canonical ledger data/paper_ledger.tsv (Round 1 rows archived to results/search/pilot/ledger_round1.tsv)
#   n50 -> scratch ledger, to measure what ranks 26-50 add
set -uo pipefail
cd "$(dirname "$0")/../../.."
GENES="Tnf Nos2 Edn1 Slc7a2 Tnfsf15 Hdc Tarm1 Calhm6 Rnd1 Lipg Col27a1 Hcar2"
src/pc.sh --version
python3 src/search_gene.py --named-query --strict --workers 4 -n 25 \
  --outdir results/search/pilot3/named_strict_n25 $GENES
python3 src/search_gene.py --named-query --strict --workers 4 -n 50 \
  --outdir results/search/pilot3/named_strict_n50 \
  --ledger results/search/pilot3/named_strict_n50/ledger.tsv $GENES
