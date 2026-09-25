# Chunk 3 Report: Paperclip search strategy

**Date:** 2026-09-24, pilot run about 17:52–18:20 UTC. paperclip v0.7.52 via `src/pc.sh`.
**Status:** ✅ Round 5 adopted (2026-09-25), along with the two Chunk 6 safeguards (bin confirmation by hand, title dedupe), which are now recorded in CLAUDE.md. The regrade of `results/search/pilot5/review_sample.md` is optional; its calls feed the Chunk 6 hand check.
- **Round 2 shows the bimodality came from my choice of pilot genes plus a retrieval gap.** It isn't built into the method. Across 12 genes the counts are graded (0, 1, 2, 3, 4, 6, 21, 23).
- **It also found a correctness problem:** the judge credits look-alike genes (Hdc ↔ HDAC1/2/4/5/10). An evidence-names-the-gene check fixes most of it.

Recommendations are at the end of the Round 2 section. The Round 1 material below is kept as history. Nothing is committed.

## Result in one table (chosen mechanics: `map`)

| Gene | Role | Query | Search ID | Map ID | Yes / 25 | No | Paper errors | Time (s) |
|---|---|---|---|---|---|---|---|---|
| Tnf | canonical | `Tnf LPS macrophage` | `s_3e96f027` | `m_436cf0f2` | **25** | 0 | 0 (1 timeout, recovered on retry) | 198.6 |
| Nos2 | canonical + alias test | `Nos2 LPS macrophage` | `s_3d92a9e1` | `m_6341269e` | **23** | 2 | 0 | 30.9 |
| Lipg | intended "moderately known" | `Lipg LPS macrophage` | `s_284209b8` | `m_68762c77` | **0** | 25 | 0 | 22.7 |
| Col27a1 | obscure, strongly induced | `Col27a1 LPS macrophage` | `s_c6d98963` | `m_d7c856c3` | **0** | 25 | 0 | 24.9 |

- All searches used `-s pmc,biorxiv,medrxiv,arxiv -n 25`.
- The four genes ran concurrently (`--workers 4`): **199 s wall-clock**.
- Rows are in `data/paper_ledger.tsv`: 100 rows, every one with a real paper ID and status `ok`. The parent sets were written with verdict `pending` before judging, and verdicts were filled in by script from the saved `map` export.
- Per-gene raw output is in `results/search/pilot/<gene>/`: `search.txt`, `parent.csv`, `map.txt`, `map_answers.txt`, `verdicts.csv` (with evidence quotes), and `summary.json`.

**Command:** `.venv/bin/python src/search_gene.py --outdir results/search/pilot --workers 4 Tnf Lipg Col27a1 Nos2`

**Test genes.** Chunk 4 hasn't run, and the authors' paper isn't in Paperclip. So I picked from a quick CPM fold-change ranking of `data/counts.csv` (protein-coding, LPS ≥ 10 CPM, every LPS replicate above every control). That ranking is for choosing test genes only and isn't DE.
- Col27a1: 0.1 → 60 CPM.
- Lipg: 0.2 → 652 CPM.

I added Nos2 as a fourth gene so the alias check runs through the full procedure.

## Mechanics settled

| Question from CLAUDE.md | Answer |
|---|---|
| Can the top-N parent set be listed before judging? | **Yes.** `search -n 25` caps N on the search itself. Paperclip's docs say a smaller N is a stable prefix of a larger one. The parent set is parsed from search stdout (rank, ID, title) and also exported with `results <sid> --save parent.csv`. |
| Can N be capped at 25 on the search? | **Yes** (`-n 25`). |
| Does filter's output contain only parent-set IDs? | **Yes, in every run** (the script asserts it). But filter has bigger problems, listed below. |
| Filter + set difference, or `map`? | **Recommend `map`.** Details below. |

### Why not `filter`

I ran `filter` with three question wordings (`results/search/pilot_filter_v1/`, `results/search/pilot_wording/v2`, `…/v3`). It is fast (under 1 s for 25 papers) but not accurate enough:

1. **It misses most real papers.**
   - With the wording from CLAUDE.md, it kept **3/25 for Tnf** and **7/25 for Nos2**, although almost every result is about LPS-induced TNF-α or iNOS.
   - Clear false negatives: Tnf ranks 2, 4, 5, 7, 8, 17, 21, 22, 23 and 25, for example "AS-703026 Inhibits LPS-Induced TNFα Production".
   - Adding "under any name, alias, or species ortholog" raised Tnf to 13 but left Nos2 at 4–5.
   - It appears to judge only the title plus the two-sentence generated summary that the export shows as "abstract."
2. **It's inconsistent.** Across wordings, the same Nos2 papers flip. Rank 6 goes yes → no, rank 14 no → yes, rank 24 yes → no.
3. **Stale read after in-place overwrite.**
   - `filter` overwrites the result set in place. In one run (Lipg, v2) it reported "25 → 0", but `results <sid>` immediately afterwards still listed all 25 pre-filter papers.
   - A naive set difference would have marked **all 25 "yes"**. My count check caught it and logged an error.
   - The script now re-reads until the listing's header shows the filter query, then checks counts.

### `map` (chosen)

**How it runs:**
- `map --from <sid> --limit 25 -j 25 --output-schema '{answer: yes|no, evidence: string}'`, with the question: *"Does this paper describe the expression of the gene {gene} (the gene, its mRNA, or its encoded protein, under any name, alias, or species ortholog) changing in response to LPS or bacterial infection? Answer yes or no, and quote the supporting sentence from the paper as evidence (empty string if no)."*
- There are no per-gene hints, so it scales to 50 genes unchanged.
- Answers come from `results <map_id> --save map_answers.txt`. The export has one block per paper with `[success]` or `[timeout]` status, `doc_id`, and the JSON answer. They're parsed by script.

**Findings:**
- **It reads the paper,** returns a checkable evidence quote, and every judged ID was in the parent set.
- **The only failure mode seen was Paperclip's 180 s per-paper timeout,** in 2 of the 7 `map` runs I made. In the manual Nos2 test (no retry) it was `bio_206e5a356c66`. In the Tnf pilot, the CLI printed the paper as `?`, and the retry succeeded, so the export no longer names it. It was probably the same bioRxiv paper, which is Tnf's rank 9.
- The script retries failed papers once (`map --resume <id> --retry-failed`). The Tnf retry succeeded.
- **A paper that still fails is recorded with status `error` and a blank verdict, never "no."**

**Cost to keep in mind:** a timeout adds about 3 minutes to that gene. Any credit or quota cost of `map` isn't shown by the CLI.

## Gate checks

### ✅ Separation
Tnf **25** vs. Col27a1 **0**. Nos2 **23**.

### ⚠ Filter accuracy: your review needed (20 calls)
The sample is 5 per gene, chosen by seeded random (seed 20260924), with "no" calls included wherever a gene had any. Tnf had no "no" calls, and Lipg/Col27a1 had no "yes" calls. The table is also saved at `results/search/pilot/review_sample.md`. Full evidence quotes are in each gene's `verdicts.csv`.

| # | gene | rank | paper_id | verdict | title | map evidence (verbatim, truncated) |
|---|---|---|---|---|---|---|
| 1 | Tnf | 1 | PMC7275413 | yes | Progranulin inhibits LPS-induced macrophage M1 polarization via NF-кB | "…mRNA and protein expression of iNOS and TNF-α… and secretion of TNF-α also significantly increased (Fig. 1c, d, e, f…" |
| 2 | Tnf | 18 | PMC9411976 | yes | Mathematical modelling of activation-induced heterogeneity in TNF, IL6… | "…the percentage of TNF-positive BMDMs peaked at 4h post stimulation…" |
| 3 | Tnf | 21 | PMC2819999 | yes | Signaling pathways involved in LPS induced TNFalpha production in human adipocytes | "TNFalpha mRNA was detected in cells by RT-PCR and TNFalpha protein was detected in supernatants by ELISA assays." |
| 4 | Tnf | 22 | PMC3433324 | yes | Minocycline hydrochloride nanoliposomes inhibit the production of TNF-α… | "After stimulation with 10 µg/mL LPS, murine macrophages (ANA-1) were treated with… minocycline…" |
| 5 | Tnf | 23 | PMC2365439 | yes | RNA from LPS-stimulated macrophages induces the release of tumour necrosis factor-α… | "…cytoplasmatic RNA extracted from rat macrophages stimulated with… LPS…" |
| 6 | Nos2 | 9 | PMC5751240 | yes | LPS-Induced Nitric Oxide, PGE2, and Cytokine Production of Mouse and Human Macrophages… | "LPS-induced expression of NOS2 protein and mRNA were also repressed in RAW 264.7 cells…" |
| 7 | Nos2 | 12 | PMC150509 | yes | Activation of macrophage NF-κB and induction of inducible nitric oxide synthase by LPS | "Abundant iNOS mRNA was found in the LPS stimulated cells at 24 hours compared to untreated cells (Fig. 2)." |
| 8 | Nos2 | 13 | PMC3660024 | no | Comparative Study of The Effect of LPS on… BALB/c and C57BL/6 Peritoneal Macrophages | (empty) |
| 9 | Nos2 | 15 | PMC7851796 | yes | Dataset on the differentiation of THP-1 monocytes to LPS inducible adherent macrophages… | "…Ct values of TNF-α, IL-1β, and COX-2 were reduced by LPS treatment…" |
| 10 | Nos2 | 19 | PMC1781469 | no | Transcriptional profiling of the LPS induced NF-κB response in macrophages | (empty) |
| 11 | Lipg | 11 | PMC5743190 | no | LPS-induced inflammation in monocytes/macrophages is blocked by liposomal delivery of… | (empty) |
| 12 | Lipg | 15 | PMC6543837 | no | Macrophage Polarization: Different Gene Signatures in M1(LPS+)… | (empty) |
| 13 | Lipg | 18 | PMC7275413 | no | Progranulin inhibits LPS-induced macrophage M1 polarization… | (empty) |
| 14 | Lipg | 21 | PMC12847160 | no | Free Fatty Acids and LPS Synergistically Promote Macrophage M1 Polarization… | (empty) |
| 15 | Lipg | 25 | PMC4024643 | no | Translation control of TAK1 mRNA by hnRNP K modulates LPS-induced macrophage activation | (empty) |
| 16 | Col27a1 | 8 | PMC3660024 | no | Comparative Study of The Effect of LPS on… Peritoneal Macrophages | (empty) |
| 17 | Col27a1 | 12 | bio_5e67bb726e21 | no | IL-27 neutralization enhances macrophage polarization… | (empty) |
| 18 | Col27a1 | 15 | PMC9609449 | no | Effect of regulating macrophage polarization phenotype on intervertebral… | (empty) |
| 19 | Col27a1 | 18 | bio_206e5a356c66 | no | Mathematical modelling of activation-induced heterogeneity… | (empty) |
| 20 | Col27a1 | 24 | PMC10157156 | no | IL-27 induces an IFN-like signature in murine macrophages… | (empty) |

**My pre-read, which you should check rather than rely on:**
- **#9 looks wrong.** The quoted evidence is about TNF-α, IL-1β and COX-2, not Nos2.
- **#3, #4 and #5 have weak evidence.** The quotes are about methods and don't show TNF changing, though the titles suggest it does.
- **#8 is uncertain.** That paper may report NO but not iNOS itself.
- The 10 Lipg and Col27a1 "no" calls look right: none of those papers is about Lipg or Col27a1.
- If you judge more than 2–3 wrong, the next step is to require the evidence quote to name the gene (or an alias) and show a change. That could be a stricter question plus a check in the script.

### ✅ Speed

**Measured per gene:**
- search: 1.6–6.1 s;
- `map`: 21–26 s normally, or about 190 s when a paper hits the 180 s timeout (1 of the 4 pilot genes).

**Estimate for K = 50:**
- Run one gene at a time: 50 × about 30 s ≈ 25 min typical, and about 2.8 h if *every* gene hit a timeout.
- With `--workers 4` (as piloted): about 7–15 min typical, and about 45 min in the worst case.

**Well within the 2–3 h budget.** No need to reduce K or N.

### ✅ with a caveat: aliases
**Nos2 / iNOS:**
- **Passes:** the `Nos2 LPS macrophage` query retrieves papers under both names. Of its 25 results, 6 use iNOS or "inducible nitric oxide synthase" naming and 15 use NOS2/NOS-2 naming.
- `map` accepted both names: #7 was judged on "iNOS mRNA" and #6 on "NOS2".
- **Caveat:** an `iNOS LPS macrophage` query (`s_2c7d554f`) returns an almost entirely different top 25, overlapping by only **2 papers**. The name in the query strongly shapes what comes back.

**This matters more for less-studied genes. Lipg example** (`results/search/pilot/alias_check/`, `results/search/pilot_alias_test/`):

| Query | Search ID | Titles about Lipg / endothelial lipase | `map` yes |
|---|---|---|---|
| `Lipg LPS macrophage` (as specified) | `s_284209b8` | **0 / 25**. All generic LPS-macrophage papers. | 0 |
| same, plus `--also "endothelial lipase LPS macrophage"` | `s_1f54e3a9` | 0 / 25. `--also` reranks against the main query, so it didn't help. | 0 |
| `Lipg (endothelial lipase) LPS macrophage` | `s_d341e798` (map `m_e477b659`) | **13 / 25** | **1** |

The one "yes" is PMC12326425, from the paper's background section: *"Its expression is upregulated in response to acute inflammatory stimuli, endotoxin exposure, and alterations in vascular wall shear stress."* That's a secondary statement, not the paper's own data.

**What this means for the claim:**
- With symbol-only queries, an unfamiliar symbol returns 25 generic LPS papers. The gene then lands in "not found" whether or not literature exists under its protein name.
- That doesn't break the honest claim ("not found in the top 25 for this query"), but it makes the bin much less informative.

## Decisions for you

1. **Mechanics: `map` (recommended) vs. `filter`.** Evidence is above. `filter` misses most real papers, is inconsistent, and has a stale-read problem.
2. **Query wording (changes the CLAUDE.md spec, so it's your call).**
   - Recommend `"<Symbol> (<official gene name>) LPS macrophage"`, for example `Lipg (endothelial lipase) LPS macrophage`.
   - Names would come from MGI's marker report, a small new download into `data/raw/` that I'd verify under the new convention. That keeps it deterministic, with no hand-curated names.
   - If you approve, I'd rerun the four pilot genes with it before Chunk 5, because it may also change Tnf's and Nos2's top 25. That hasn't been tested yet.
3. **Does a background or introduction statement count as "yes"?** An example is PMC12326425 above.
   - The current question counts it.
   - Tightening to "reports its own data showing…" would make the "established" bin mean primary evidence. It would also lower counts, especially for heavily reviewed genes.
4. **K and N:** the speed check supports **K = 50 and N = 25** unchanged.

## Files and housekeeping

- `src/search_gene.py`: the per-gene runner.
  - Modes: `--mode map` (default) and `--mode filter`.
  - Other options: `--workers`, a `--ledger` override for scratch runs, `--question`, and `--also` (testing only).
  - The ledger is updated under a file lock because genes run concurrently. `*.lock` has been added to `.gitignore`.
- `data/paper_ledger.tsv`: the chosen `map` pilot rows only.
- **Superseded runs, kept for provenance, not in the ledger:**
  - `results/search/pilot/_probe/`: the first hand run. Its filter question included "TNF, TNF-alpha", so it isn't comparable with the others.
  - `results/search/pilot/_failed_parse_run/`: my first script run. My parser missed the author line between title and ID, so all four genes were logged as `error`. That was a bug in my code, not a search failure. The searches had succeeded, and the error rows are kept in that folder's `paper_ledger.tsv`.
  - `results/search/pilot_filter_v1/`: `filter` with the CLAUDE.md wording.
  - `results/search/pilot_wording/{v2,v3}/`: `filter` with alias-aware wordings.
  - `results/search/pilot_map/Nos2/`: the first manual `map` timing test (183 s, one timeout). Its question included a hint ("e.g. iNOS / NOS2"), so the final pilot reran Nos2 without it.
- **Still true:**
  - Paperclip prints `[repo: mva-lof-molecular]`, context left over from an unrelated earlier task. Nothing was added to it.
  - Searches cross into generic territory quickly. Col27a1's 25 results don't mention the gene. That's expected with semantic search, and the judging step handles it.


---

## Round 2 (2026-09-24, about 19:00–19:15 UTC): is per-gene sorting all-or-nothing?

**The concern:** Round 1 gave 25 / 23 / 0 / 0. All-pass or all-fail isn't an informative sorting.

**What was run.** Everything used `src/search_gene.py`, map mode, N = 25, 4 genes at a time, with scratch ledgers under `results/search/pilot2/`. The real ledger `data/paper_ledger.tsv` is unchanged.
- **Genes:** the 4 Round 1 genes plus **8 "middle" genes** from the same fold-change ranking that I expected to be somewhat studied: Hdc, Edn1, Tarm1, Calhm6, Slc7a2, Hcar2, Rnd1, Tnfsf15.
- **① Symbol-only query, current judge.** The 8 middle genes (`C_symbol_lenient`, 61 s wall). Round 1 values for the other 4.
- **② Symbol + name query:** `"<Symbol> (<MGI official name>) LPS macrophage"`, for example `Hdc (histidine decarboxylase) LPS macrophage`, with the current judge (`A_named_lenient`, 138 s wall for 12 genes).
- **③ Same as ②, plus a script check that the evidence quote names the gene.** Computed after the fact from ②'s saved evidence, with no new Paperclip calls.
- **④ Symbol + name query, strict question, plus the name check** (`B_named_strict`, 204 s wall; one Tnf paper timed out and was recovered on retry).
  - Strict question: *"…report its own experimental data (not background statements or citations of other work) showing that the expression of the gene {gene}… changes in response to LPS or bacterial infection? …quote the sentence reporting that result; it must name the gene or its protein…"*
  - Name check: a "yes" becomes "no" unless the quote contains the symbol, the MGI official name, or an MGI synonym (case-insensitive, whole-word match).
- **Corpus count,** a second, continuous number:
  - Paperclip boolean full-text search `(<all gene names>) AND ("LPS" OR "lipopolysaccharide") AND "macrophage"` over pmc, biorxiv, medrxiv and arxiv, with `--ranking bm25 --full-text -n 500`.
  - **Paperclip returns at most 500**, so the count is exact below the cap. At the cap (Tnf 484, Nos2 487, fewer than 500 after deduplication) it means "≥ about 500".
  - Names come from `src/gene_names.py`: the symbol, the MGI official name, and MGI synonyms of at least 4 characters, excluding RIKEN and Gm IDs.
- **Name source:** `data/raw/MRK_List2.rpt`, MGI's marker report, downloaded from `https://www.informatics.jax.org/downloads/reports/MRK_List2.rpt`, 78.8 MB.
  - Verified: plain-text file with the expected header row (`MGI Accession ID … Marker Synonyms (pipe-separated)`).
  - Filtered to current genes (Status O, Marker Type Gene); symbols are unique within that set.
  - sha256 appended to `download_checksums.sha256`.

### Results (qualifying papers out of top 25)

| gene | ① symbol, lenient | ② sym+name, lenient | ③ ② + name check | ④ sym+name, strict + name check | corpus count |
|---|---|---|---|---|---|
| Tnf | 25 | 25 | 23 | 23 | 484 (cap) |
| Nos2 | 23 | 24 | 20 | 21 | 487 (cap) |
| Hdc | 11 | 10 | 3 | 2 | 42 |
| Edn1 | 3 | 6 | 6 | 4 | 220 |
| Slc7a2 | 6 | 8 | 5 | 6 | 40 |
| Hcar2 | 1 | 4 | 0 | 0* | 166 |
| Tnfsf15 | 2 | 2 | 2 | 3 | 55 |
| Tarm1 | 0 | 2 | 1 | 1 | 4 |
| Calhm6 | 2 | 2 | 2 | 2 | 10 |
| Lipg | 0 | 1 | 0 | 0 | 10 |
| Rnd1 | 1 | 1 | 1 | 1 | 4 |
| Col27a1 | 0 | 0 | 0 | 0 | 2 |

\* At least one of Hcar2's downgrades was wrong; see finding 3. The table is also saved as `results/search/pilot2/comparison.md`.

### What this shows

1. **The Round 1 bimodality came mostly from which genes I picked.** With symbol-only queries (①), the 8 middle genes already spread out: 0, 1, 1, 2, 2, 3, 6, 11. Round 1 happened to test only extremes.
2. **The symbol + name query helps somewhat, with no clear losses.** Retrieval rose for Edn1 (3 → 6), Hcar2 (1 → 4), Tarm1 (0 → 2) and Lipg (0 → 1). Hdc (11 → 10) and Slc7a2 (6 → 8) stayed about level. Most of those gains don't survive the name check, though, so the query change matters less than the judge fix.
3. **The judge credits look-alike genes. This is the most important finding.**
   - In ④, the name check downgraded 14 "yes" calls. Most are the model accepting a *different* gene:
     - Hdc: quotes about **HDAC1, HDAC2, HDAC4, HDAC5, HDAC10** (5 papers), plus histamine-producing neutrophils and a generic methods sentence;
     - Slc7a2: **SLC37A2**;
     - Tarm1: **Trem-1**;
     - Hcar2: a table of other GPCRs (Gpr84, Htr2b);
     - Tnf: NO levels;
     - Nos2: a figure legend with no data.
   - Lenient mode almost certainly counts these too, which is why Hdc drops from 10–11 to 2–3 once the check is applied (② → ③).
   - **The check can also be wrong in the other direction.** Hcar2 PMC5301212, "LPS also markedly increased **HCA2** in primary mouse macrophages", is a real yes, but "HCA2" isn't among MGI's synonyms. Errors of this kind make counts too low.
   - Adding human ortholog aliases (HGNC) would fix most of them. That would be another download, so it's your call.
4. **The judge doesn't fully agree with itself.** On the same papers, the lenient and strict questions gave identical model answers for 283/297 (95%). Three papers went lenient "no" → strict "yes", which shouldn't happen, and 2 of those 3 were wrong anyway: an HDC protein increase caused by norepinephrine, and a generic methods sentence. Treat single-paper calls as noisy. Counts are more robust than individual calls.
5. **Retrieval is nearly, not fully, reproducible.** Runs ② and ④ used identical queries minutes apart. 9/12 genes returned the same top 25; 3 differed by one paper, at ranks 15, 16 and 22. The ledger records exactly which papers each run saw, and "on this date" covers the rest.
6. **The corpus count is graded but noisy, so use it as context, not for binning.**
   - It spans 2 → ≥ about 500 and broadly tracks ④.
   - But Hcar2 (166) and Edn1 (220) are high relative to ④. Hcar2's names include heavily used receptor aliases (Gpr109a, HM74). "endothelin 1" / "ET-1" appear in many LPS papers about other cell types.
   - It counts co-mentions anywhere in the full text, not evidence.

### Recommendations for the gate

1. **Mechanics:** `map` (unchanged from Round 1).
2. **Query:** `"<Symbol> (<MGI official name>) LPS macrophage"` (②/④). It retrieves more on-topic papers for less-studied genes and loses nothing measurable.
3. **Judge:** the **strict question + evidence-names-the-gene check (④)**.
   - "Established" then means *the paper's own data* show a change, which fits the honest claim best.
   - The check removes the look-alike errors deterministically.
   - Known cost: aliases missing from MGI (HCA2) cause undercounts.
   - Optional fix: add HGNC human aliases to the name list. It's one more verified download.
4. **Add the corpus count as a secondary column,** labeled "full-text co-mentions (capped at 500)". Never use it for binning, following the same rule as the rate.
5. **Bins under ④** (defaults ≥3 / 1–2 / 0), as a preview on these 12:
   - established: Tnf, Nos2, Edn1, Slc7a2, Tnfsf15;
   - limited: Hdc, Tarm1, Calhm6, Rnd1;
   - not found in top 25: Lipg, Col27a1, Hcar2*.

   All three bins are used, so the sorting is informative.
6. **K = 50, N = 25** still fit comfortably: ④ ran 12 genes in 204 s with one timeout.

**Nothing here has been adopted into the real ledger or CLAUDE.md.** It needs your go at the gate.

### Files (Round 2)
- `src/gene_names.py`: MGI names and synonyms, plus the evidence-name matcher.
- `src/search_gene.py`: new flags `--named-query`, `--strict` and `--corpus-count`. Also: an unknown symbol now logs a per-gene error row instead of crashing the batch.
- `results/search/pilot2/{A_named_lenient,B_named_strict,C_symbol_lenient}/<gene>/`:
  - raw CLI output;
  - `verdicts.csv` with columns evidence, evidence_names and downgraded;
  - `summary.json`, which includes the corpus count and its exact boolean expression for run A.
- `results/search/corpus_count_probe/`: the probes that established the 500 cap.

---

## Round 2b (2026-09-24): N = 50 test **blocked by a Paperclip auto-update**

**What was attempted:** the Round 2 strict setup (④) at `-n 50` on the same 12 genes (`results/search/pilot2/D_named_strict_n50/`), to measure what ranks 26–50 add.

**What happened:**
- All 12 searches succeeded (`Found 50 papers`), but all 12 `map` calls failed with `[error] Something went wrong. Please try again.`
- The script logged each as a **search error row** in the scratch ledger, not as zero papers, which is the intended behavior.

**Cause, confirmed by testing:** during this run the CLI auto-updated **0.7.52 → 0.7.89** (the banner `[paperclip] Updated 0.7.52 → v0.7.89` is in the run's output).
- 0.7.89's `map --help` no longer lists **`--output-schema`**, **`--retry-failed`**, or the structured-extraction workers. The remaining options are `--worker` (quick-reader, eligibility-screen, exhaustive-extraction), `--model`, `-n`, `--offset`, `-j`, `--resume` and `--save-as`.
- Isolation tests on an existing search (`s_a0f9095b`):

| Test | Result |
|---|---|
| any `--output-schema` call, even `--limit 2` | fails |
| `--limit 10` or `--limit 25` without a schema | works |

  So the failures come from the removed flag. They aren't caused by N = 50, concurrency, or quota.
- `eligibility-screen` in 0.7.89 returns **free text only**, for example "Yes, the paper reports its own experimental data… (L17)". Probe output is in `results/search/pilot2/_v0789_probe/`.

**Why it blocks the recommended setup:**
- **Verdicts:** without a schema, yes/no would have to be parsed from prose. That's less deterministic, and the ledger rule requires verdicts computed by script from a well-defined answer.
- **The name check:** free-text answers restate the gene name, so "evidence names the gene" would always pass unless the quoted sentence is extracted separately. That needs a prompt convention (e.g. "start with YES or NO, then give one verbatim quote in double quotes") and a parser. That's a redesign, and it isn't validated.
- **Retries:** failed papers can no longer get a separate retry pass (`--retry-failed` is gone). Whether `--resume` alone retries failures is untested.

**Sandbox note:** the update was written to paperclip's own install location, outside the project. Pinning or rolling back the version has to happen on your side; I can't touch it under the sandbox rule.

**The N = 50 question stays unanswered.** The rank-based guesses I gave earlier were extrapolations from ranks 1–25, not measurements.

### Round 2b follow-up: what the docs say (checked 2026-09-24)

**Summary: `--output-schema` is still documented everywhere. It looks like a regression in 0.7.89, not an intended removal.**

**What the docs say:**
- **Bundled docs** (`paperclip skill` under 0.7.89; saved at `results/search/pilot2/_v0789_probe/skill_0.7.89.txt`, lines 491–500) say: "`--output-schema` works with the default map reader. Pass a Draft 2020-12 JSON Schema for each paper's complete output… The old `--output_schema` spelling and legacy field maps remain temporary deprecated aliases."
- **Web docs** (paperclip.gxl.ai/docs, `map` section, fetched with WebFetch because the browser extension wasn't connected) list `--output-schema` as a supported `map` parameter with the same schema format. They also list `--document-ids` and `--filter`, which 0.7.89's `map --help` omits.
- **Changelog** (paperclip.gxl.ai/changelog, 0.7.52 → 0.7.89): no entry removes or changes `--output-schema` or `--retry-failed`. The 0.7.89 entry (today, 2026-09-24) says the MCP connector now "exposes one tool per CLI command, generated from the CLI itself". That suggests the command surface was regenerated in this release. That's my guess at the cause, not confirmed.

**Behavior under 0.7.89** (`map --from s_a0f9095b --limit 2 …`):

| Variant | Result |
|---|---|
| minimal schema `{"type":"object","properties":{"answer":{"type":"string"}}}` | `[error] Something went wrong.` |
| old spelling `--output_schema` | same error |
| our yes/no + evidence schema | same error |
| `--worker quick-reader` + minimal schema | same error |
| **made-up flag `--definitely-not-a-flag x`** | **runs normally; the flag is silently ignored** |

**What this means:**
- The schema flag is recognized and passed along, and then fails. It isn't ignored the way an unknown flag is.
- So the option is **documented but broken** in 0.7.89.
- Separately, **unknown flags are silently ignored**, so a mistyped flag would change a run without any warning. This is a reproducibility hazard for Chunk 5.

## Round 2c (2026-09-24): does `filter` work well enough in 0.7.89?

**Setup:**
- The 12 Round 2 genes, symbol + name query, `--mode filter`, run under paperclip 0.7.89.
  - **E:** the CLAUDE.md question.
  - **F:** the strict wording without the quote request ("…own experimental data (not background statements or citations)… under any name, alias, or species ortholog…").
- Wall time: 33 s (E) and 21 s (F) for all 12 genes.
- Output: `results/search/pilot2/{E_filter_claude,F_filter_strict}/`. Comparison table: `results/search/pilot2/filter_vs_strict.md`.
- The docs for `filter` are unchanged in 0.7.89: it still overwrites the result set in place and has no new options.

**A script fix was needed, and it was mine:** 0.7.89 reorders the `results` header to `Query: filter '<q>' --from <sid>`. My stale-read check expected the 0.7.52 order, so the first E/F attempt logged every gene as an error, correctly not as zero. The check now accepts either order. `filter` itself had applied correctly.

**Counts (out of 25), compared with the Round 2 strict `map` result (④, 0.7.52):**

| gene | ④ map strict + name check | E filter, CLAUDE.md wording | F filter, strict wording |
|---|---|---|---|
| Tnf | 23 | 11 | 16 |
| Nos2 | 21 | 6 | 18 |
| Slc7a2 | 6 | 0 | 1 |
| Edn1 | 4 | 0 | 3 |
| Tnfsf15 | 3 | 0 | 0 |
| Hdc | 2 | 2 | 1 |
| Calhm6 | 2 | 0 | 0 |
| Tarm1 | 1 | 0 | 0 |
| Rnd1 | 1 | 1 | 1 |
| Hcar2 / Lipg / Col27a1 | 0 | 0 | 0 |

**Paper-level agreement, F vs ④** (295 shared papers; retrieval differed by a paper or two for some genes):
- both yes: 37;
- F-only yes: 2;
- ④-only yes: 24.

**Hand check of the 10 disputed papers for Slc7a2, Tnfsf15 and Calhm6** (④ yes, F no):
- **F wrong, 5:**
  - Calhm6 PMC12766987, "Calhm6 is significantly induced by LPS", in a paper with Calhm6 in the title;
  - Calhm6 PMC10068325, "LPS… upregulated CALHM6";
  - Slc7a2 PMC6245571, "LPS strongly induced… Slc7a2";
  - Slc7a2 PMC6411972, Slc7a2 increased after mycobacterial infection;
  - Tnfsf15 PMC5358891, TNFSF15 induced by LPS in macrophages.
- **④ wrong, 5:**
  - Slc7a2 PMC2265428: a background statement that the own-data rule should have excluded;
  - Slc7a2 PMC6377304: knockout, no LPS;
  - Slc7a2 PMC7386301: *no* induction, in sheep;
  - Tnfsf15 PMC7689184: TACE cleavage, not expression;
  - Tnfsf15 PMC6130856: poly(I:C) and immune complexes, not LPS.

**What this shows:**
1. **`filter` has improved on canonical genes compared with Round 1.** With the strict wording, Tnf went 3 → 16 and Nos2 7 → 18. It's also **very precise**: only 2 yes calls ④ rejected.
2. **It still misses body-text evidence,** and that's exactly where the middle tier's evidence sits. Slc7a2, Tnfsf15, Calhm6 and Tarm1 fall to 0–1. **The middle tier collapses again**, and the output returns to the bimodal pattern you objected to. It most likely still judges only the title plus the generated summary.
3. **④ has real false positives** among the disputed papers: 5 of 10 above. The name check stops look-alike genes, but not wrong-stimulus, no-change, or background calls.
4. **Neither is ground truth.** The disputed papers split evenly, so the per-gene hand review at the gate is essential, whichever mechanism is chosen.

**Conclusion:** `filter` in 0.7.89 isn't good enough on its own for this pipeline. The middle tier is where the "limited" vs. "not found" claim lives, and `filter` drops it. `map` with a schema remains the better mechanism, but it's blocked under 0.7.89 (Round 2b).

## Round 2d (2026-09-25, 12:22 UTC): `map --output-schema` works again

This was a narrow retest after the server-side patches. **The CLI is still `paperclip 0.7.89`**, so the fix was on the server. `map --help` still doesn't list `--output-schema` or `--retry-failed`. Output is in `results/search/pilot2/_schema_retest/`.

| Test | Result |
|---|---|
| Minimal schema `{"type":"object","properties":{"answer":{"type":"string"}}}`, 2 papers (`m_615dd659`) | ✅ Runs. Each paper returns a JSON object. |
| **Our schema** (`answer` enum yes/no + `evidence`), 3 papers from the Rnd1 search `s_a0f9095b` (`m_5736a043`) | ✅ Strict JSON. `results --save` export parsed by `parse_map_export`: PMC9161769 yes (with an evidence quote), PMC3420873 no, PMC6696182 no. This matches the Round 2 strict call for Rnd1. |
| **End to end**, `search_gene.py --named-query --strict Rnd1` (`s_4c1e99c1` / `m_e75034f7`) | ✅ 25 papers, 1 yes / 24 no, 0 paper errors, 30 s. Same count as ④ in Round 2. |
| `map --resume m_5736a043 --retry-failed`, and `--resume` without the flag, on a *completed* map | ⚠ Both return `[error] Something went wrong.` This may just mean "nothing to resume", but a real retry of a failed paper is untested on 0.7.89. The script is safe either way: if the retry doesn't recover a paper, that paper stays `status=error` and is never counted as "no". |

**Still open:**
- the N = 50 measurement (Round 2b);
- tightening the strict question for the failure modes found in Round 2c (wrong stimulus, no change, background);
- your hand review;
- the version question: on 0.7.89 the schema path works but is undocumented in `--help`, and unknown flags are silently ignored.


---

## Round 3 (2026-09-25): chosen setup run into the real ledger, plus the N = 50 measurement

**What ran:** `results/search/pilot3/run.sh`, with the log in `run.log`.
- Setup: `search_gene.py --named-query --strict --workers 4`, run on the 12 Round 2 genes twice:
  - at `-n 25`, into `data/paper_ledger.tsv`;
  - at `-n 50`, into the scratch ledger `results/search/pilot3/named_strict_n50/ledger.tsv`.
- **Ledger change:** the Round 1 rows (4 genes, symbol-only query, lenient question) moved to `results/search/pilot/ledger_round1.tsv`. The real ledger now holds only the chosen method: 12 genes × 25 = 300 rows.
- **The CLI auto-updated again, to paperclip 0.7.91** (the first line of `run.log`). `map --output-schema` worked on every call.

### Counts (yes out of 25; ledger-derived)

| Gene | Round 2 ④ | **Round 3 N=25** | paper errors | N=50 run: yes in ranks 1–25 | yes in 26–50 | Bin (≥3 / 1–2 / 0) |
|---|---|---|---|---|---|---|
| Tnf | 23 | **21** | 3 | 23 | 21 | established |
| Nos2 | 21 | **19** | 1 | 19 | 19 | established |
| Edn1 | 4 | **5** | 0 | 4 | 0 | established |
| Slc7a2 | 6 | **6** | 0 | 6 | 3 | established |
| Tnfsf15 | 3 | **2** | 0 | 2 | 0 | **limited** (was established in Round 2) |
| Hdc | 2 | **2** | 0 | 2 | 1 | limited |
| Tarm1 | 1 | **1** | 0 | 1 | 0 | limited |
| Calhm6 | 2 | **2** | 0 | 2 | 0 | limited |
| Rnd1 | 1 | **1** | 0 | 1 | 0 | limited |
| Lipg | 0 | **0** | 0 | 0 | 0 | not found in top 25 |
| Col27a1 | 0 | **0** | 0 | 0 | 0 | not found in top 25 |
| Hcar2 | 0 | **0** | 0 | 0 | 0 | not found in top 25 |

- **Paper errors:** 4 papers timed out (Tnf ranks 7, 12, 21; Nos2 rank 10). They are in the ledger as `status=error` with an empty verdict, never as "no". Neither gene is near a bin boundary.

### Findings

1. **The patched Paperclip reproduces Round 2.**
   - Counts are within ±2 for every gene.
   - The 0 / limited / established structure is unchanged.
   - Every bin is still used.
2. **Retrieval is now fully stable.** For all 12 genes, the top 25 of the N = 50 search was the same 25 papers as the N = 25 search, run minutes apart. Compared with Round 2 (a day earlier), 8 genes had the same top 25; Nos2, Tnfsf15 and Lipg differed by one paper, and Tnf by two.
3. **Count noise comes from the name check, not from the model's yes/no.**
   - On the same papers, the N = 25 and N = 50 judges disagreed on 3 of about 296 (1%): Tnf PMC2211976, Nos2 PMC6920088, Edn1 PMC13483658.
   - In all 3 the model said yes both times. The second time it quoted a different sentence that doesn't name the gene ("mRNA levels…", "NO flux…", "This study also found this result."), so the name check downgraded it.
   - The Tnf and Nos2 downgrades are false negatives: the papers are real yeses.
4. **Bin boundaries are sensitive to this noise.**
   - Tnfsf15 went 3 → 2, established → limited, because of the Round 2 vs. Round 3 difference.
   - Edn1 sits at 4–5.
   - A single noisy call can move a gene across the ≥3 line. The report should say so, and a gene at exactly 2–3 deserves a look in the Chunk 6 spot check.
5. **N = 50 doesn't earn its cost.**
   - Ranks 26–50 add yeses only for genes that are already established (Tnf +21, Nos2 +19, Slc7a2 +3).
   - The only bin change is Hdc (2 → 3), and its extra yes is **wrong**: PMC6359378, rank 28, is about HDC after wire implantation, not LPS or infection. That's the known wrong-stimulus failure mode.
   - No gene moved out of "not found".
   - **Recommend N = 25.**
6. **Speed:**
   - 12 genes took 200 s wall-clock at 4 workers (N = 25) and 192 s at N = 50.
   - The slow genes are the ones with paper timeouts (Tnf and Nos2, about 195 s each); the rest take 25–38 s.
   - Estimate for K = 50: about 15 min. That's well inside the 2–3 h budget.

### Hand review (gate item)

`results/search/pilot3/review_sample.md` has 15 calls from the real ledger, drawn by `make_review_sample.py` (seed 3):
- Tnf: 4 yes, 1 no. Tnf has only one "no" among its 22 judged papers.
- Slc7a2: 3 yes, 2 no.
- Hdc: 2 yes, 3 no.
- The "no" picks are weighted toward name-check downgrades, because that's the riskiest rule.

**My own read, for you to confirm or overrule:**
- 11 look right.
- 2 look wrong:
  - Hdc PMC13493966: the stimulus is norepinephrine, not LPS (this same paper was flagged in Round 2);
  - Slc7a2 PMC2265428: the quote is a background statement ("Several pro-inflammatory mediators including LPS can regulate… CAT2").
- 1 is debatable: Slc7a2 PMC7386301. The quote reports *no* induction in sheep. The paper may show induction in other species.
- The 3 downgrades (SLC37A2 ×2, HDAC3) are correct look-alike rejections.

That puts it right at the "2–3 wrong" line. The errors are the failure modes already listed in Round 2c (wrong stimulus, background statement, no change). If you judge more than 2–3 wrong, the fix is to tighten the strict question for those three cases, then rerun these 12 genes (about 4 min).

### Decisions for the gate
1. Hand review verdict on the 15 calls, and whether to tighten the question.
2. **N = 25** (recommended) and **K = 50** (fits the time budget).
3. Adopt named query + strict + name check. On approval, I'll record the method, K and N in CLAUDE.md's open decisions.
4. Optional: add HGNC human aliases to reduce name-check false negatives (HCA2, and the "NO flux" type of quote).
5. **Paperclip version drift:** 0.7.52 → 0.7.89 → 0.7.91 in two days, and one of those updates broke `map`. Consider pinning the version before Chunk 5, on your side, because it's outside the sandbox.

### Files (Round 3)
- `results/search/pilot3/run.sh`, `run.log`
- `results/search/pilot3/named_strict_n25/<gene>/` (source of the real ledger rows) and `named_strict_n50/<gene>/` + `named_strict_n50/ledger.tsv`
- `results/search/pilot3/make_review_sample.py`, `review_sample.md`
- `results/search/pilot/ledger_round1.tsv` (archived Round 1 ledger)


---

## Round 4 (2026-09-25): tightened question plus a stimulus check

**Why:** in your hand review of Round 3, you judged 3 of 15 calls wrong by checking whether the snippet supports the verdict. My read of the same sample (paper vs. question) found 2 more. All the confirmed failures have the same shape: the model said yes, but the quote doesn't show an LPS- or infection-driven change in the gene. The quotes were:
- a baseline condition;
- a no-change result;
- a background statement;
- a change caused by another stimulus (norepinephrine).

**Changes** (`src/search_gene.py`, `src/gene_names.py`):
- **New flag `--stimulus-check`** (used with `--strict`). The old question and behavior are unchanged without the flag.
- **New question (`QUESTION_STIM`):**
  - The change must be relative to unstimulated or uninfected controls.
  - The answer must be no when the only evidence is another stimulus, a no-change result, a baseline condition, or a statement about other work.
  - The single quoted sentence must name the gene, name LPS or the infection, and state the change.
- **New script check:** a yes whose quote names no LPS or infection term is downgraded to no, with the reason recorded. The existing name check still applies.
  - The terms are in `gene_names.STIMULUS`: LPS, lipopolysaccharide, endotoxin, lipid A, infect\*, bacteri\*, sepsis/septic, CLP/cecal ligation, and common bacterial genera.
  - The matched terms are saved in the `evidence_stimulus` column of `verdicts.csv`.

**Run:** `results/search/pilot4/run.sh` (log in `run.log`), paperclip 0.7.91. Same 12 genes, N = 25, 4 workers, into the real ledger.
- Round 3's ledger rows were archived to `results/search/pilot3/ledger_round3.tsv`.
- **Ledger:** 300 rows, all `status=ok`. 51 yes, 249 no.
- **Speed:** 116 s wall-clock, with no paper timeouts this time.

### Counts (yes out of 25, from the ledger)

| Gene | Round 3 | **Round 4** | Bin |
|---|---|---|---|
| Tnf | 21 (+3 errors) | **19** | established |
| Nos2 | 19 (+1 error) | **17** | established |
| Edn1 | 5 | **3** | established (on the boundary) |
| Slc7a2 | 6 | **5** | established |
| Tnfsf15 | 2 | **2** | limited |
| Hdc | 2 | **1** | limited |
| Tarm1 | 1 | **1** | limited |
| Calhm6 | 2 | **2** | limited |
| Rnd1 | 1 | **1** | limited |
| Lipg | 0 | **0** | not found in top 25 |
| Col27a1 | 0 | **0** | not found in top 25 |
| Hcar2 | 0 | **0** | not found in top 25 |

**No bin changed** from Round 3. Every gene's top 25 was identical to Round 3's, so all differences below are judge differences.

### What the tightening did (12 verdicts changed on the same papers; all listed in the review file)

**The four disputed Round 3 calls:**

| Paper | Round 3 problem | Round 4 |
|---|---|---|
| Hdc PMC13493966 | norepinephrine | **fixed**: the stimulus check downgraded it |
| Slc7a2 PMC7386301 | no-change quote | **fixed**: the model now says no |
| Tnf PMC7018708 | baseline quote | still yes; the new quote (IL-10 pretreatment "diminished" LPS-induced TNF) implies LPS induction but doesn't state it against a control. Borderline. |
| Slc7a2 PMC2265428 | background statement | **not fixed**: the same background quote still gets yes |

**New problems:**
- **New false negatives from the stimulus check.** The same study appears twice, as preprint and published versions (Tnf `bio_206e5a356c66` and `PMC9411976`). Its quote says "4h post stimulation" without naming LPS, so it was downgraded. It's a real yes. This is the expected cost of the check.
- **A new wrong yes the checks can't catch.** Slc7a2 PMC6377304 is quoted as "IFN-γ + LPS stimulation resulted in robust expression of … Nos2 and Il1b … in both WT and Slc7a2–/– BMmacs". The gene is named only as the knockout, and the change is in other genes. The name check passes because "Slc7a2" appears in the sentence.
- **A no → yes on a review article.** Nos2 PMC4188127 ("Of Mice and Men") is a review, and the quote is a table entry summarizing another study. It violates the own-data rule.
- **Model answers changed on 7 papers without a downgrade.** One is the review article above (no → yes); the other 6 went yes → no, including Edn1 PMC13483658, the thin "This study also found this result" paper, which is correct now. The rest need your eye (listed in the review file).

**Preprint/published duplicates:** the parent sets can contain the same work twice (bioRxiv plus PMC; seen for Tnf and in Col27a1's set). If both are yes, the paper is counted twice. It's harmless here, because both copies are now no, but at count 2–3 it could move a bin. **For Chunk 6, dedupe the yes rows by normalized title before counting.** The ledger itself keeps both rows.

### Hand review (gate item)

`results/search/pilot4/review_sample.md`, drawn by `make_review_sample.py`:
- **Main sample:** Tnf 3 yes / 2 no, Slc7a2 3 / 2, Hdc 1 / 4. Hdc has only one yes now.
- **Optional table:** all 12 verdicts that changed between Round 3 and Round 4.

**My read of the main 15:** about 12–13 right. The weak rows:
- Slc7a2 PMC6377304: wrong yes (see above).
- Slc7a2 PMC6411972: borderline. The comparison is between two mycobacterial strains, not infected vs. uninfected.
- Tnf `bio_206e5a356c66` and `PMC9411976`: the downgrades are right by the rule, but the papers are real yeses.

### Decisions for the gate
1. Your regrade of the Round 4 sample, and whether to keep Round 4 or go back to Round 3. My recommendation is to **keep Round 4**:
   - It fixes the wrong-stimulus and no-change errors.
   - It doesn't change any bin.
   - Its false negatives fall on heavily studied genes, where they don't matter.
   - The remaining errors (background statements, knockout-only mentions) are rare and are noted as known limits.
2. N = 25, K = 50: unchanged. 12 genes now take about 2 min.
3. Dedupe yes rows by normalized title in Chunk 6.
4. Carried over from Round 3: optional HGNC aliases, and pinning the Paperclip version.


---

## Round 5 (2026-09-25): evidence may span two passages; human aliases in the name check

**Why:** you raised the concern that the checks were too strict, because papers often name the stimulus in the methods or a figure legend and report the gene's change somewhere else. The Round 4 downgrades bore this out:
- **Hcar2 PMC5301212** is a real yes (HCA2 induced by LPS in RAW264.7 cells). It was dropped because "HCA2" is a human alias missing from MGI. That left Hcar2 wrongly in "not found".
- The Tnf "4h post stimulation" study (preprint + published) was dropped because the result sentence doesn't name LPS.

**Changes:**
- **New flag `--two-quote`** (used with `--strict`). The earlier flags are unchanged.
  - **Question (`QUESTION_TWO`):** the same as Round 4, but the model gives two quotes:
    - `evidence`: the result sentence;
    - `context`: an optional sentence from elsewhere (methods or legend) naming the gene or stimulus that the result sentence leaves out.
  - **Schema:** `SCHEMA_TWO` adds the required `context` string.
  - **Checks:** the name and stimulus checks run on both quotes together.
- **Name check adds HGNC human-ortholog names**, joined on the MGI accession ID. This covers the symbol, name, alias and previous symbols, and alias names (at least 4 characters, clone IDs removed).
  - When one mouse gene maps to several human genes, only the exact-symbol ortholog is kept. For example, Hcar2 maps to both HCAR2 and HCAR3, and HCAR3/HCA3 names are excluded.
  - The retrieval query is unchanged.
- **New download:** `data/raw/hgnc_complete_set.txt`, from `storage.googleapis.com/public-download-files/hgnc/tsv/tsv/`.
  - Verified: plain text, with the expected header (`symbol`, `alias_symbol`, `prev_symbol`, `mgd_id`, …), 45,112 lines.
  - The sha256 is in `download_checksums.sha256` and the date in `download_date.txt`.
- **Sensitivity column:** `verdicts.csv` now keeps `model_answer` (before checks) and `context`. `summary.json` has `yes_before_checks`.

**Run:** `results/search/pilot5/run.sh` (log in `run.log`), paperclip 0.7.91. 206 s wall-clock. One Tnf paper timed out and is recorded as `status=error`.
- Round 4 ledger rows are archived to `results/search/pilot4/ledger_round4.tsv`.
- All 12 genes returned the same top 25 as Round 4.

### Counts

| Gene | Round 4 | **Round 5** | yes before checks | Bin |
|---|---|---|---|---|
| Tnf | 19 | **22** (+1 error) | 22 | established |
| Nos2 | 17 | **19** | 23 | established |
| Edn1 | 3 | **4** | 4 | established |
| Slc7a2 | 5 | **6** | 7 | established |
| Tnfsf15 | 2 | **2** | 2 | limited |
| Hdc | 1 | **1** | 10 | limited (the checks remove 9 HDAC look-alikes) |
| Tarm1 | 1 | **1** | 2 | limited (the check removes a TREM-1 look-alike) |
| Calhm6 | 2 | **2** | 2 | limited |
| Rnd1 | 1 | **1** | 1 | limited |
| Lipg | 0 | **0** | 0 | not found in top 25 |
| Col27a1 | 0 | **0** | 0 | not found in top 25 |
| Hcar2 | 0 | **2** | 3 | **limited** (was wrongly "not found") |

- **"Not found" genes:** Lipg and Col27a1 are 0 even before checks. The model itself said no to all 25 papers, so no check put them there.
- **Bins the checks change:** Hdc (10 → 1) and Tarm1 (2 → 1). Both downgrades are correct look-alike rejections (HDAC1–5 and TREM-1).

### What worked
- **Hcar2 PMC5301212:** now yes. Its evidence is "expression was significantly enhanced following stimulation by LPS", and the context is the Figure 1 legend naming HCA2. This fixes the one known wrong "not found".
- **Tnf "4h post stimulation" study:** now yes.
- **Nos2 PMC4188127:** the review article is back to no.
- **Round 4 fixes held:** Hdc PMC13493966 (norepinephrine) and Slc7a2 PMC7386301 (no change) are still no.

### What it cost: the context quote loosens the stimulus check
A methods sentence naming LPS now satisfies the stimulus check even when the quoted result comes from a different condition. Together with semantic errors that no string check can catch, several low-count yeses are weak.

**Wrong yeses:**

| Paper | Problem |
|---|---|
| Tnfsf15 PMC6130856 | The result is for immune complex and poly(I:C); LPS comes from the methods sentence. |
| Slc7a2 PMC5526900 | *Leishmania* is a protozoan, not a bacterium. "infected" passes the check. |
| Slc7a2 PMC3237590 and PMC6377304 | The change is in iNOS or NO in the knockout, not in Slc7a2. |
| Hcar2 PMC10357040 | Background statement about adipocytes, with a citation. |
| Slc7a2 PMC2265428 | Background statement (unchanged since Round 3). |
| Tnf PMC7018708 | Baseline quote (back again). |

**Questionable yeses:**

| Paper | Problem |
|---|---|
| Tarm1 PMC11702950 | Compares atg5−/− with wild type, not LPS with control. |
| Edn1 PMC3826139 | Conditioned medium, not LPS directly. |
| Edn1 PMC7779813 | Compares mmLDL + LPS with LPS alone. |

**Tally for the six limited genes after this round (9 yeses in total):**
- 6 are solid;
- 2 are wrong (Tnfsf15 PMC6130856, Hcar2 PMC10357040);
- 1 is questionable (Tarm1).

No gene is wrongly in "not found".

### Where this leaves the method
- **Errors now lean toward over-counting.** For this project that's the safer direction: it can only *understate* how many genes are "not found", so the headline claim stays conservative.
- **The remaining errors are semantic,** such as the wrong comparison, a knockout-only mention, the wrong organism, or a background statement. Another round of string checks won't fix them.
- **Per the stopping rule, I recommend adopting Round 5 and stopping refinement here,** with two safeguards moved into Chunk 6:
  1. **Confirm the bin by hand.** For every gene with at least one yes, walk its yes rows in rank order and confirm them until 3 solid yeses are found, or the yeses run out. A gene is "established" only with 3 confirmed; otherwise the confirmed count sets the bin.
     - This caps the work at 3 confirmations per established gene; well-studied genes like Tnf confirm in the first 3 rows.
     - The cost is roughly 60–100 papers at K = 50.
     - Overrides are recorded as a separate reviewed-verdict column, derived from a review file by script, and never typed into counts.
  2. **Dedupe yes rows by normalized title.** The Tnf preprint + published pair is now yes twice.
- **Report language:** "limited" counts are model judgments that can include weak evidence. "Not found" still means not found in the top 25 results for this query.

### Hand review (gate item)
`results/search/pilot5/review_sample.md` (drawn by `make_review_sample.py`, seed 3):
- **Main table:** 15 calls, Tnf 3/2, Slc7a2 3/2, Hdc 1/4. The quotes show evidence // context.
- **Optional table:** the 12 verdicts that changed from Round 4.

My read of the main 15: Slc7a2 PMC3237590 and PMC5526900 are wrong yeses; PMC6411972 is borderline (a comparison between strains); the rest look right.

**Correction to my first draft of this section:** the sample isn't unluckily weak for Slc7a2; the gene itself is.
- Of Slc7a2's 6 yeses, only PMC6245571 is solid. PMC6411972 is borderline, and the other 4 are wrong (PMC3237590, PMC5526900, PMC6377304, PMC2265428).
- Slc7a2's true count may be 1–2 ("limited"), not 6 ("established").
- **So over-counting can also push a gene over the ≥3 line into "established"**, not just raise limited counts.
- That is still the conservative direction for the "not found" claim, but it matters for the "established" number. It changes safeguard 1 below.

### Decisions for the gate
1. Your regrade, and adopting Round 5 (recommended) versus Round 4.
2. Moving the two safeguards into Chunk 6 (hand-check yeses for count-1–3 genes; dedupe by title). This needs a small CLAUDE.md edit on your go.
3. N = 25, K = 50: unchanged. About 3.5 min per 12 genes.
4. Pinning the Paperclip version (on your side).
