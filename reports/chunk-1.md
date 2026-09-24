# Chunk 1 Report: Repo setup + rnaseq-de install and demo run

**Date:** 2026-09-24
**Status:** ✅ GATE PASSED. The demo ran with the **pydeseq2** backend (confirmed in three places). Nothing is committed. Waiting for your go before Chunk 2.

## Part A: Repo setup

| Item | Result |
|---|---|
| `git init` | Done. Empty repo with no commits and no remote. |
| Layout | `data/raw/`, `results/`, `src/`, `reports/` created (`results/de/demo/` from the run) |
| Virtualenv | `.venv/` (Python 3.14.6, from `python3 -m venv .venv`) |
| `.gitignore` | `.venv/`, `.env`, `.cache/`, `__pycache__/`, `*.pyc`, `.DS_Store`, `data/raw/`, `results/de/*/tables/normalized_counts.csv`, `results/de/*/figures/` |
| `README.md` | Stub with name, one-line description, the "not found ≠ novel" caveat, and a placeholder "How to run" section |

`git status` shows as untracked: `.gitignore`, `CLAUDE.md`, `README.md`, `results/`. `reports/` will show up too once this file exists.

**Other ignore candidates (not added yet):**
- `.cache/`: already added. It holds the matplotlib/XDG cache, which I redirected into the project (see Sandbox).
- The `results/de/*/figures/` PNGs are small for the demo (~120 KB total). I ignored them as the plan suggested. If you want the PCA/volcano plots in git for the demo, un-ignore them.
- Later, possibly large Paperclip raw outputs under `results/search/*/`. We'll decide in Chunk 3 once we see their size.

## Part B: Install

```bash
export PIP_NO_CACHE_DIR=1          # pip's cache would otherwise go to ~/Library/Caches
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install pandas numpy matplotlib scikit-learn scipy pydeseq2 opentelemetry-sdk
```

Key versions: pydeseq2 0.5.4, anndata 0.13.4, formulaic 1.2.2, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1, scikit-learn 1.9.1, matplotlib 3.11.2, opentelemetry-sdk 1.44.0. The full freeze is in `results/de/demo/reproducibility/pip_freeze.txt`.

`opentelemetry-sdk` is required even though SKILL.md doesn't list it. `clawbio.common.report` imports `clawbio.common.audit`, which imports opentelemetry at module level.

## Part B: Demo run

```bash
export PYTHONPATH="$HOME/claw-bio-test/ClawBio"
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$PWD/.cache/matplotlib"
export XDG_CACHE_HOME="$PWD/.cache"
.venv/bin/python ~/claw-bio-test/ClawBio/skills/rnaseq-de/rnaseq_de.py \
  --demo --backend pydeseq2 --output results/de/demo/
```
- The run took about 33 s wall-clock.
- **PYTHONPATH confirmed:** the skill needs the ClawBio root on `PYTHONPATH` because it imports `clawbio.common`.
- ClawBio checkout commit: `4aefedbe518e0d6c2500f5d0ae898163a6bc294f`.

**Backend confirmation (pydeseq2 in all three places):**
- `report.md` line 9: `**Backend used**: \`pydeseq2\``
- `result.json`, under `summary.backend_used`: `"pydeseq2"`
- The stdout JSON contains `"backend_used":"pydeseq2"`, and the PyDESeq2 Wald-test log is in `reproducibility/stdout.log`.

**Outputs (`results/de/demo/`):** `report.md`, `result.json`, `tables/{de_results,normalized_counts,qc_summary}.csv`, `figures/{pca,volcano,ma_plot}.png`, `reproducibility/{commands.sh,environment.yml,checksums.sha256}`. I also added `RUN_COMMAND.sh` (the exact invocation), `stdout.log`, `pip_freeze.txt`, and `clawbio_commit.txt`.

Demo sanity check: this is a 10-gene toy dataset with 3 vs. 3 samples and design `~ batch + condition`. GeneA, E, and J come out up; GeneB comes out down (all padj < 1e-14). The rest are not significant.

## Sandbox check
- **Nothing was written outside the project.** After the run, I ran `find -newer <run-start marker>` over `~/claw-bio-test/ClawBio`, `~/.clawbio`, `~/.matplotlib`, `~/.cache`, and `~/Library/Caches/pip`. It returned nothing.
- Guards used for this:
  - `PYTHONDONTWRITEBYTECODE=1` stops `__pycache__` being written into the ClawBio checkout.
  - `MPLCONFIGDIR`/`XDG_CACHE_HOME` point to `./.cache`.
  - `PIP_NO_CACHE_DIR=1` keeps pip from caching outside the project.
- **All future runs need the same guards.** `RUN_COMMAND.sh` is the template.
- ClawBio's `clawbio.common.audit` defaults to appending to `~/.clawbio/audit.jsonl`, which is outside the sandbox. `rnaseq_de.py` does **not** call the audit writer, only `write_result_json` into the output dir, so it was never triggered. The warning is for any future use of another ClawBio skill.

## Findings / surprises

1. **Backend fallback behavior.** The report and `result.json` both state the backend used, so a silent fallback would be visible. In the code (`run_de`, rnaseq_de.py:314–334), `auto` falls back to `simple` only when the PyDESeq2 **import** fails. A crash inside `deseq2()` raises under either setting instead of falling back. With `--backend pydeseq2`, an import failure raises `RuntimeError` rather than falling back. So the forced flag is doing its job.

2. **⚠ LFC shrinkage looks wrong and matters for Chunk 4.** `de_results.csv` reports the **shrunk** log2FC next to the **unshrunk** Wald p-values. The skill offers no option to turn shrinkage off. In the demo, shrinkage pushed some non-significant genes *away* from zero and flipped their sign:
   - GeneC went from −0.09 to **+1.47** (padj 0.68).
   - GeneI went from −0.06 to **+1.51** (padj 0.95).

   Real apeGLM shrinkage pulls estimates *toward* zero. This could be a toy-data artifact (10 genes, batch partly confounded with condition), a pydeseq2 0.5.4 quirk, or a coefficient mismatch in the skill.

   Chunk 4 selects "positive log2FC among the top by padj", which is sensitive to exactly this. **Proposal for Chunk 4:**
   - Check shrunk against unshrunk LFC sign on the real data. The unshrunk values are in `reproducibility/stdout.log`, and a sign check against normalized counts is another option.
   - If they disagree for any top gene, report it rather than trust the table.

   I'm reporting only. I have not changed anything, since the checkout is read-only.

   **Decision (2026-09-24): option 1 adopted for Chunk 4.** The unshrunk log2FC tracks the raw counts. GeneA's ~6× change comes out at 2.53, and the flat GeneC/GeneI come out at about 0. The shrunk column inflates the true hits and pushes the flat genes to about +1.5. The Wald p-values/padj come from the unshrunk model and are unaffected. Plan:
   - Run the skill as planned (`--backend pydeseq2`, `results/de/lps/`).
   - Also run a small `src/de_unshrunk.py` that calls PyDESeq2 directly on the same counts, metadata, design and contrast. It writes unshrunk log2FC next to the skill's shrunk log2FC and flags every gene whose sign disagrees.
   - **The top K are selected by padj among genes with unshrunk log2FC > 0.** Fold changes shown in the demo table are unshrunk.
   - Any sign disagreement among the top K is listed in the Chunk 4 report.
   - Likely cause (unconfirmed): apeGLM estimates its prior from only 10 genes, 4 of them strongly changed, and the optimizer probably misbehaves on such a tiny problem. This may not reproduce on a ~20k-gene dataset, but we check rather than assume.

3. **The skill's `commands.sh` is not replayable as written.** It says `python rnaseq_de.py ...`: bare `python` isn't on PATH, `PYTHONPATH` isn't set, and it records absolute paths to the demo inputs. `RUN_COMMAND.sh` in each bundle is the authoritative record.

4. **The skill refuses to write into a non-empty output directory.** A rerun needs a new `--output` name or a manual clear. That is good for provenance.

5. **Metadata mismatches.** `result.json` has an empty `input_checksum`, and its `skill` field is `"rnaseq"` rather than `"rnaseq-de"`. Input checksums do appear in `checksums.sha256`.

## Unresolved / for you
- ~~Finding 2 (LFC shrinkage) needs a decision at Chunk 4.~~ Resolved: option 1, using unshrunk LFC via `src/de_unshrunk.py` (see Finding 2).
- Whether to track figures in git (currently ignored).
- GitHub remote: waiting on you.
