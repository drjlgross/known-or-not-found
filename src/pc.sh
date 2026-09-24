#!/usr/bin/env bash
# Run the paperclip CLI outside the project virtualenv.
# paperclip's shebang is `#!/usr/bin/env python3`; with .venv active that resolves to the venv
# Python, which lacks paperclip's deps (requests) and crashes. Strip .venv from PATH instead of
# installing anything.
# Usage: src/pc.sh search -s geo -n 25 "LPS macrophage"
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -vxF "$root/.venv/bin" | paste -sd: -)"
export PATH
unset VIRTUAL_ENV
exec paperclip "$@"
