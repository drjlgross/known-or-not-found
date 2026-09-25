#!/usr/bin/env bash
# Chunk 4: rnaseq-de on GSE250273, LPS 4 h vs control 4 h (project root = known-or-not-found/).
# Copied into results/de/lps/reproducibility/RUN_COMMAND.sh after the run; that copy is authoritative for the bundle.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$HOME/claw-bio-test/ClawBio"     # rnaseq_de.py imports clawbio.common
export PYTHONDONTWRITEBYTECODE=1                      # keep the ClawBio checkout unmodified (no __pycache__)
export MPLCONFIGDIR="$PWD/.cache/matplotlib"          # keep matplotlib cache inside the project
export XDG_CACHE_HOME="$PWD/.cache"
.venv/bin/python "$HOME/claw-bio-test/ClawBio/skills/rnaseq-de/rnaseq_de.py" \
  --counts data/counts.csv --metadata data/metadata.csv \
  --formula "~ condition" --contrast "condition,LPS,control" \
  --backend pydeseq2 --output results/de/lps/
