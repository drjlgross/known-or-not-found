#!/usr/bin/env bash
# Exact invocation used for this bundle (project root = known-or-not-found/).
# The skill's own commands.sh omits PYTHONPATH and the demo flag; this file is authoritative.
set -euo pipefail
export PYTHONPATH="$HOME/claw-bio-test/ClawBio"     # rnaseq_de.py imports clawbio.common
export PYTHONDONTWRITEBYTECODE=1                      # keep the ClawBio checkout unmodified (no __pycache__)
export MPLCONFIGDIR="$PWD/.cache/matplotlib"          # keep matplotlib cache inside the project
export XDG_CACHE_HOME="$PWD/.cache"
.venv/bin/python "$HOME/claw-bio-test/ClawBio/skills/rnaseq-de/rnaseq_de.py" \
  --demo --backend pydeseq2 --output results/de/demo/
