#!/usr/bin/env bash
# Chunk 3 Round 5 (2026-09-25): evidence + context quotes (QUESTION_TWO / SCHEMA_TWO); name + stimulus checks run on
# both quotes; name check adds HGNC human-ortholog names. Real ledger; Round 4 rows archived to
# results/search/pilot4/ledger_round4.tsv.
set -uo pipefail
cd "$(dirname "$0")/../../.."
GENES="Tnf Nos2 Edn1 Slc7a2 Tnfsf15 Hdc Tarm1 Calhm6 Rnd1 Lipg Col27a1 Hcar2"
src/pc.sh --version
python3 src/search_gene.py --named-query --strict --two-quote --workers 4 -n 25 \
  --outdir results/search/pilot5/two_quote_n25 $GENES
