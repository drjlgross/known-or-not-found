#!/usr/bin/env bash
# Chunk 3 Round 4 (2026-09-25): tightened question (QUESTION_STIM) + evidence must name the gene AND LPS/infection.
# Real ledger; Round 3 rows archived to results/search/pilot3/ledger_round3.tsv.
set -uo pipefail
cd "$(dirname "$0")/../../.."
GENES="Tnf Nos2 Edn1 Slc7a2 Tnfsf15 Hdc Tarm1 Calhm6 Rnd1 Lipg Col27a1 Hcar2"
src/pc.sh --version
python3 src/search_gene.py --named-query --strict --stimulus-check --workers 4 -n 25 \
  --outdir results/search/pilot4/named_stim_n25 $GENES
