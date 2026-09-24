# known-or-not-found — Build Plan

*Literature triage for a differential-expression gene list. First application: LPS-stimulated macrophages.*

Run a ClawBio differential-expression skill on a public LPS-stimulated macrophage dataset, then use Paperclip to sort the top induced genes into **established in this context**, **limited evidence**, and **not found in the searched literature**, with every claim traceable to a saved search and a paper.

## DEFAULT MODE (read every session)

Read this whole file for context, but **execute only the chunk named in the prompt**. Build each chunk knowing how it fits with the chunks around it, then stop at that chunk's done criteria. Do not start the next chunk.

**Gate chunks (1, 2, 3, 4) are hard stops.** Report the gate result and wait for my go. Never proceed past a gate on your own.

**Reports.** At the end of every chunk, write the full report to `reports/chunk-N.md` (what was done, commands run, outputs produced, check results, anything surprising or unresolved). Print only the report path and a one-line status to the terminal.

**Git.** Never commit on your own. Commit only when I explicitly ask for it in a prompt, after I have verified the chunk's work. A commit means I observed the intended behavior working, not that a command exited 0.

## 🔒 SANDBOX: ABSOLUTE

All filesystem activity is confined to the project directory (the directory containing this file) and its subtree. Inside it, read, write, create, and delete are all fine. Outside it, do nothing: no reading, writing, moving, or deleting any file or directory beyond this root, for any reason, even if a chunk or prompt seems to ask for it.

**The one exception is read-only:** the ClawBio checkout at `~/claw-bio-test/ClawBio/` may be *read and executed* (to run the skill), never modified. If a step seems to require writing anything outside the project root, stop and ask instead of acting.

Downloads land in `./data/`. Tool output lands in `./results/`. Nothing is ever written elsewhere, including `/tmp` and any tool's default output path.

## Context (standing instructions, true every session)

**What we're building.** A pipeline from dataset to ranked table: public LPS vs. unstimulated macrophage RNA-seq → differential expression via ClawBio `rnaseq-de` → top K induced genes → one Paperclip search plus relevance filter per gene → each gene binned by qualifying-paper count → a demo table with citations.

**The claim to make:** "Of the top K LPS-induced genes in this dataset, X have established literature support in this context, Y have limited support, and Z were not found in the top 25 search results for their query."
**The claim to avoid:** "Z novel LPS-response genes discovered."

**Honesty guardrails (these constrain every output).**
- "Not found" means not found in the top 25 results for this query, on this date. It never means novel, and every output that shows the bin says so.
- Report the qualifying-paper **count** as the primary number. The rate (count ÷ N) is secondary and never used for binning, because it penalizes heavily studied genes (Tnf appears in many non-LPS contexts).
- The relevance filter is a model judgment (interpretive). Its calls get hand-checked on a sample and are never treated as ground truth.
- The DE result is only as trustworthy as its positive controls. If canonical LPS genes don't come out strongly induced, the problem is the data or the setup, not the biology.
- The LPS response depends strongly on time point. Early (about 1–4 h) and late (about 12–24 h) gene sets differ. Record the dataset's time point and judge the positive controls against it.

**Environment assumptions.**
- ClawBio checkout at `~/claw-bio-test/ClawBio/` (note the nested `ClawBio/` subdirectory). The skill is at `skills/rnaseq-de/rnaseq_de.py`.
- `rnaseq_de.py` imports `clawbio.common`, so it must run with the ClawBio root on `PYTHONPATH` (or from the ClawBio root). Confirm in Chunk 1.
- macOS: always invoke `python3`. Bare `python` is not on PATH (except inside an activated virtualenv).
- Paperclip CLI authenticated. As of v0.5.8, `-s` is **mandatory** on `search`/`searches`; use `-s pmc,biorxiv,medrxiv,arxiv`. Verify `filter` syntax with `--help` before first use. `reduce` was previously unavailable here, so any cross-paper rollup happens in pandas. **Invoke paperclip through `src/pc.sh`**, which strips `.venv` from `PATH`. With the venv active, paperclip's `env python3` shebang picks up the venv Python, which lacks `requests`, and crashes.

**rnaseq-de rules (load-bearing).**
- **Force the backend:** always pass `--backend pydeseq2`. With the default `auto`, the skill **silently falls back to a simpler method** if PyDESeq2 is missing or crashes. Every run must confirm, from the output report or result files, which backend actually ran. If the report doesn't say, that's a finding for the Chunk 1 report.
- **Contain the output:** always pass `--output results/de/<run_name>/`. Never accept a default path.
- **Input contract:** a count matrix (genes × samples, first column the gene ID); a metadata table with a `sample_id` column; a formula (e.g., `~ condition`); a contrast as `factor,numerator,denominator` (e.g., `condition,LPS,control`).

**Repo layout.**
```
data/       # downloaded dataset, skill-format counts + metadata, paper_ledger.tsv
results/    # de/<run>/ (skill output bundles), search/ (per-gene filtered results), final/
src/        # dataset prep, search runner, classification, report builder
reports/    # chunk-N.md, one per chunk
CLAUDE.md   # this file
README.md   # stub at Chunk 1, completed at Chunk 7
.venv/      # project virtualenv (gitignored)
```

**Conventions.**
- The gene symbol is the join key between the DE table and the search results. Record species casing (mouse `Tnf` vs. human `TNF`) once in Chunk 2 and use it everywhere.
- Everything reproducible: every output directory carries the command and inputs that made it.
- **Every download is verified before use.** Run `gzip -t` on compressed files, and check the expected header or first line (e.g. a GTF's `##description` line, a count file's column header). An exit code of 0 from `curl` isn't enough: servers can return an HTML error page under the requested name. A failed download is logged as a failure (`data/geo_search/download_failures.tsv`) and deleted, never kept as a data file. Checksums of kept downloads go in `data/raw/download_checksums.sha256`.

**Provenance ledger (minimal, so the demo stays the priority).** One file, `data/paper_ledger.tsv`, one row per paper per gene:
`gene · query · search_id · date · rank · paper_id (PMCID/PMID/DOI as returned) · title · verdict (yes/no) · status (ok/error)`
- The parent set (the full top-N search result) is written to the ledger **before** filtering. Filter keeps only positives, so verdict = yes for IDs that pass and verdict = no for the rest of the parent set, computed by script, never by the model.
- Per-gene counts are always **derived from the ledger by script**, never typed by the agent.
- A failed search writes one row with status = error. It is never recorded as zero papers.
- **Instrumentation must never block the demo.** Record the columns above and move on. No extra tooling, dashboards, or polish. Analysis happens after the demo, from the ledger.

## Build chunks (ordered, one prompt each)

### Chunk 1: Repo setup, then install and run rnaseq-de ⛔
**Goal:** A clean project repo, and proof that the skill runs locally with a confirmed backend.

**Part A: Repo setup.**
1. The project root is `known-or-not-found/`, the directory containing this CLAUDE.md. Work only inside it.
2. `git init` (if not already a repo). **Do not commit.** The initial commit happens only when I ask.
3. Create the layout: `data/raw/`, `results/`, `src/`, `reports/`.
4. Create a virtualenv inside the project: `python3 -m venv .venv`, then activate it. All installs go into `.venv`, never system-wide.
5. Write `.gitignore` covering at least: `.venv/`, `.env`, `__pycache__/`, `.DS_Store`, `data/raw/` (large downloads stay out of git), and `results/de/*/` normalized-count and figure outputs if they're large (keep `de_results.csv`, `report.md`, and reproducibility files committable). Note in the report anything else that should be ignored.
6. Write a stub `README.md`: the project name, a one-line description ("Literature triage for a differential-expression gene list: which induced genes are established, and which weren't found"), and a placeholder "How to run" section to fill in at Chunk 7.
7. The GitHub remote is my step. I'll create the repo and tell you when to add the remote. Do not create or push to any remote yourself.

**Part B: Install and run the skill.**
**Produces:** PyDESeq2 and the skill's dependencies installed in `.venv`, and a demo run (`--demo --backend pydeseq2 --output results/de/demo/`), invoked with the ClawBio root on `PYTHONPATH`.
**Done when:** the repo layout, `.gitignore`, and README stub exist; the demo completes; and the report states the backend used.
**GATE:** it runs, and the backend is confirmed to be pydeseq2. If PyDESeq2 won't install or crashes, stop. Do not proceed on the `simple` fallback.

### Chunk 2: Find and prepare the dataset ⛔
**Goal:** One public LPS-stimulated vs. unstimulated macrophage bulk RNA-seq dataset, in the skill's input format.
**Produces:** raw download in `data/raw/`; `data/counts.csv` and `data/metadata.csv` in skill format; a dataset card in the report covering accession, species, cell type (e.g., BMDM), LPS dose, **time point**, replicate count, and how counts were generated.
**Search:** GEO (Playwright is fine). Prefer mouse BMDMs, ≥3 replicates per condition, a processed count matrix already deposited, and a single time point (or one clearly selectable).
**Done when:** files are built and the sample labels map cleanly to LPS vs. control.
**GATE:** the dataset exists, the labels make sense, and counts are raw integers (not normalized values). Report the top 2–3 candidates with a recommendation and wait for my pick if it's not clear-cut.

### Chunk 3: Paperclip search strategy ⛔
**Goal:** Confirm that per-gene searches separate established LPS genes from poorly characterized ones, fast enough to scale to about 50 genes.
**Procedure:**
1. Pick 3 test genes: one canonical (Tnf), one moderately known, and one obscure but strongly induced (from Chunk 4 if run, otherwise from the dataset authors' reported list).
2. For each, search `"<gene> LPS macrophage"` with `-s pmc,biorxiv,medrxiv,arxiv` and take the top N = 25.
3. Write the full top-25 parent set to `data/paper_ledger.tsv` **before** filtering.
4. Filter with: "Does this paper describe this gene's expression changing in response to LPS or bacterial infection?" Mark passing IDs yes and the rest of the parent set no (by script).
5. Record wall-clock time for search plus filter per gene.

**Mechanics to settle here (keep it quick; pick what works and move on):**
- Can the top-N parent set be listed before filtering, and can N be capped at 25 on the search itself (or truncated afterward)?
- Does filter's output contain only IDs from that parent set?
- If the parent set can't be listed, fall back to `map` over all 25 papers with a yes/no field, and time it.

**Produces:** `results/search/pilot/` and ledger rows for the three genes; the chosen mechanics (filter + set difference, or map) stated in the report.
**GATE (all must pass):**
- **Separation:** Tnf's count is clearly higher than the obscure gene's. If they're similar, stop and rethink.
- **Filter accuracy:** 5 filter calls per gene (15 total, a mix of yes and no rows from the ledger) are listed in the report with paper IDs for my review. If I judge more than 2–3 wrong, rewrite the filter question.
- **Speed:** time per gene × 50 fits within about 2–3 hours using the chosen mechanics. If not, recommend smaller K or N.
- **Aliases:** one alias-prone gene (Nos2 / iNOS) retrieves papers using either name.

### Chunk 4: Run DE on the real dataset ⛔
**Goal:** A trustworthy ranked table of LPS-induced genes.
**Produces:** `results/de/lps/` (skill bundle, `--backend pydeseq2`); the top K = 50 induced genes (by adjusted p-value, filtered to positive log2 fold change) in `data/top_genes.csv`.
**Done when:** the DE run completes and the backend is confirmed.
**GATE: positive controls.** Canonical LPS genes appropriate to the dataset's time point (e.g., Tnf, Il1b, Il6, Cxcl10, Nos2) come out strongly induced, and the PCA separates LPS from control. Report each control's fold change and adjusted p-value. If the controls fail, stop: it's wiring or data, not biology.

### Chunk 5: Per-gene search across the top K
**Goal:** Run the Chunk 3 procedure, unchanged, on all K genes.
**Produces:** `results/search/<gene>/` for each gene; `data/paper_ledger.tsv` complete for all K genes.
**Done when:** every gene has ledger rows (or an error row).
**Watch:** respect Paperclip rate limits (batch and back off). If a search errors, log it as an error, **never as zero**. A failed search reported as "not found" is exactly the failure this project is designed to catch.

### Chunk 6: Classify and check direction
**Goal:** Bin each gene and test whether the literature agrees with the dataset.
**Produces:** `results/final/gene_bins.csv` (counts computed from the ledger by script) with columns gene, log2FC, padj, qualifying count, rate (secondary), and bin (**established** ≥3 · **limited** 1–2 · **not found in top 25** 0 · **search error**).
**Optional (cut first if time runs short):** for established genes, extract the reported direction (up/down) from a small set of qualifying papers and compute the direction-agreement rate with the dataset. List every disagreement.
**Done when:** every gene is binned, and bin counts are in the report.
**Watch:** hand-spot-check 3 genes end to end (search → filter calls → count → bin) before trusting the table.

### Chunk 7: Demo artifact
**Goal:** The deliverable.
**Produces:** `results/final/demo_table` (gene, fold change, bin, 1–3 citations each) and `results/final/REPORT.md`: dataset card, positive-control results, method, bin summary, the "not found in top 25 for this query" caveat stated plainly, and the direction-agreement result if Chunk 6's optional step ran.
Every citation in the demo table is a paper ID that appears as a yes row in the ledger.
**Done when:** the table and report exist, and a short script (`src/verify.py`, a few lines) recomputes every count and bin from the ledger and matches the report exactly. Any mismatch fails the chunk.
**Check:** open 3 citations and confirm each supports the claim it's attached to.

## Scope levers (if the day runs long, in order)
1. Reduce K from 50 to 20.
2. Skip the direction check in Chunk 6.
3. Reduce N from 25 to 15 (and state the change in every output).
The ledger's core columns and the error-not-zero rule are **not** scope levers. They stay even when everything else gets cut.

## Held-out contrasts (post-demo, only if the pipeline works)
GSE250273 has more arms than the demo uses. The demo uses only LPS 4 h (TrtB01–03) vs. control 4 h (Ctrl01–03). **Don't build or run these until the demo is done and the pipeline is verified:**
- Dexamethasone vs. control, 4 h (TrtA vs. Ctrl)
- Dex + LPS vs. LPS, 4 h (TrtAB vs. TrtB): what glucocorticoids change in the LPS response
- The same contrasts at 24 h (Ctrl04–06, TrtA04–06, TrtB04–06, TrtAB04–06)

## Open decisions to resolve in flight
- ~~Which dataset (Chunk 2 gate).~~ Resolved: GSE250273, LPS 4 h vs. time-matched control (see `reports/chunk-2.md`).
- The filter question's wording, and filter + set difference vs. map (Chunk 3 gate).
- The final K and N (Chunk 3 speed check).
- The bin thresholds (≥3 / 1–2 / 0 are defaults; revisit after seeing the Chunk 5 distribution).
