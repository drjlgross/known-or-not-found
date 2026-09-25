# Chunk 5 Report: Per-gene search across the top K = 50

**Date:** 2026-09-25
**Status:** ✅ Done. The criterion was that every gene has ledger rows: all 50 genes have 25 rows each, and there are no search errors. Chunk 4 checks 5 (biologist review of the list) and 6 (rerun) were still pending when this ran, at your request. If the gene list changes, only the affected genes need re-searching.
**Bins below are provisional.** They come from model counts. CLAUDE.md sets the real bins from **hand-confirmed** counts in Chunk 6.

## What ran
1. **Pilot rows moved out.** The 12 pilot genes' rows went from `data/paper_ledger.tsv` to `results/search/pilot5/ledger_pilot.tsv` (300 rows). The ledger now holds only the top 50.
2. **Search.** `src/run_chunk5.sh` ran the Round 5 method on the genes in `data/top_genes.csv`:
   `search_gene.py --named-query --strict --two-quote --workers 4 -n 25 --outdir results/search`
   - paperclip 0.7.91.
   - 588 s wall-clock for 50 genes (about 12 s per gene effective at 4 workers).
   - Log: `results/search/_runs/chunk5.log`.
3. **A bug fix in the name check, followed by an offline recheck** (details below):
   - `src/gene_names.py` gained `normalize()`.
   - `src/recheck_verdicts.py` re-applied the checks to the saved model answers, with no new Paperclip calls. It uses the same `apply_checks` / `write_verdicts` functions as a live run; those were moved out of `process()` in `src/search_gene.py`, with no behavior change.
   - The pre-recheck ledger is at `results/search/_runs/ledger_before_recheck.tsv`, and each gene keeps `verdicts_pre_recheck.csv`. `summary.json` records the recheck with before-and-after counts. Log: `results/search/_runs/recheck.log`.

## Ledger
- **1,250 rows** (50 × 25): 1,243 `ok` and 7 `error`.
- **Verdicts:** 296 yes, 947 no, and 7 blank (the errors).
- **The 7 errors are paper-level judge timeouts,** 1 each in Nos2, Il6, Tnfsf15, Socs3, Ptx3, Ptges and Cxcl1. They're recorded as `status=error` with a blank verdict, never as "no". **None can change a bin:** the only low-count gene affected is Tnfsf15, which goes from 1 to at most 2 and stays "limited".
- **Consistency checks:**
  - Per-gene yes counts derived from the ledger match every `summary.json`.
  - No `pending` verdicts remain.
  - No stray IDs: every judged ID is in its parent set.
  - Between the live run and the recheck, the model-answer counts and error counts didn't change for any gene.

## Bug found and fixed: Greek letters in gene names
- **The problem:** the first pass gave **Il1b 3 yeses out of 24 model yeses.**
  - Papers write "IL-1β", "Il-1β" and "IL-1α", and PDF extraction leaves combining marks such as "IL-1̠b".
  - The name lists have "IL-1B" and "IL-1beta" (from MGI and HGNC), so the word-bounded matcher failed and downgraded real yeses.
- **The fix:** `normalize()` is applied to both the quote and each name before matching. It strips combining marks, maps Greek letters to their Latin initial (β → b), and maps a spelled-out Greek letter after a digit, hyphen or space to its initial.
- **Tests:** "IL-1β", "Il-1β", "IL-1̠b", "IL-1̓α" and "TNF-α" now match. The look-alikes are still rejected: CXCL12 for Ccl12, CX3CL1 for Cxcl1, HDAC3 for Hdc, IL-1β for Il1a, IFN-γ for Tnf.
- **Effect:** only 2 genes changed. **Il1b 3 → 22**, and **Il1a 6 → 13**. Neither changed bin.
- **Known remaining miss:** "interleukin (IL)-1β", where the symbol is split by a parenthesis, still doesn't match. It's rare, and the context quote usually carries the name anyway.
- **This also applies to future runs,** since live runs and the recheck use the same functions.

## Provisional bins (model counts, before Chunk 6 confirmation)

| Bin | Genes |
|---|---|
| established (≥3) | 30 |
| limited (1–2) | 12 |
| not found in top 25 (0) | 8 |
| search error | 0 |

**Not found in top 25:** Lipg, Itgb8, Col27a1, Trim30c, Tmem200b, Iigp1, Gbp6, Tnfsf4.

**Genes whose bin is changed by the script checks.** CLAUDE.md requires these to be listed, and they should be graded first in Chunk 6:

| Gene | Count | Before checks | What the downgrades are |
|---|---|---|---|
| Itgb8 | 0 | 1 | **Probably a real yes lost:** "integrin αvβ8" is the protein that contains Itgb8's product. The name check can't see that. (The study used human moDC.) |
| Trim30c | 0 | 2 | Quotes say "Trim30". That usually means Trim30a, so the downgrade is probably right, but it's ambiguous. |
| Iigp1 | 0 | 2 | Correct: the quotes are ISG lists or Gbp1, not Iigp1. |
| Ccl12 | 1 | 5 | Mostly correct look-alikes (CXCL12, MCP-1), but **PMC10167364 "CCL2, 12, and 17 … increased in response to LPS" is a real Ccl12 yes lost** to the abbreviated list. |
| Hdc | 2 | 9 | Mostly HDAC look-alikes (correct). PMC7379312 needs a look. |
| Bcl2a1a | 2 | 4 | **PMC11405755, "LPS stimulation strongly induced A1…", is probably a real yes lost.** "A1" is too short to be in the name list (the minimum is 4 characters). "A1" also can't tell Bcl2a1a from the b/c/d paralogs. |

So of the 8 "not found" genes, Itgb8 may belong in "limited".

**Adopted 2026-09-25 (now part of the Chunk 6 grading design below):** for genes whose bin is changed by the checks, graders also review the *downgraded* rows, not just the yes rows, and can confirm one as a yes in `data/review_verdicts.tsv`. As written, Chunk 6 only reviews yes rows, so these real yeses would stay lost.

## Per-gene counts
| rank | gene | log2FC | yes | yes_before_checks | paper_errors | search_id | provisional_bin |
|---|---|---|---|---|---|---|---|
| 1 | Edn1 | 17.9 | 4 | 4 | 0 | s_ce9c4eec | established |
| 2 | Nos2 | 16.1 | 20 | 22 | 1 | s_d6be8ace | established |
| 3 | Shisa3 | 15.0 | 2 | 2 | 0 | s_88320d4a | limited |
| 4 | Il6 | 13.7 | 19 | 20 | 1 | s_6a1d2e02 | established |
| 5 | Tnfsf15 | 13.1 | 1 | 1 | 1 | s_df3e5637 | limited |
| 6 | Il1b | 12.6 | 22 | 24 | 0 | s_4c510687 | established |
| 7 | Il1a | 12.5 | 13 | 14 | 0 | s_e202e116 | established |
| 8 | Lipg | 12.2 | 0 | 0 | 0 | s_efa4f396 | not found in top 25 |
| 9 | Saa3 | 11.8 | 11 | 17 | 0 | s_2b1ee5d5 | established |
| 10 | Cxcl10 | 11.7 | 10 | 13 | 0 | s_c4f8d4e8 | established |
| 11 | Acod1 | 11.6 | 19 | 19 | 0 | s_ad1d55b9 | established |
| 12 | Gbp5 | 11.2 | 9 | 9 | 0 | s_d5f2de0d | established |
| 13 | Il12b | 10.8 | 12 | 18 | 0 | s_3142adf7 | established |
| 14 | Serpinb2 | 10.8 | 4 | 4 | 0 | s_bfd7ede5 | established |
| 15 | Itgb8 | 10.7 | 0 | 1 | 0 | s_21093ae7 | not found in top 25 |
| 16 | Cd69 | 10.7 | 4 | 5 | 0 | s_2c0f04b2 | established |
| 17 | Ptgs2 | 10.6 | 18 | 20 | 0 | s_b4b9be4b | established |
| 18 | Steap4 | 10.5 | 1 | 1 | 0 | s_febe8111 | limited |
| 19 | Serpina3g | 10.5 | 3 | 4 | 0 | s_3cacaac7 | established |
| 20 | Socs3 | 10.3 | 13 | 15 | 1 | s_44f2cd59 | established |
| 21 | Adamts4 | 10.2 | 3 | 3 | 0 | s_ee990bcb | established |
| 22 | Ifi205 | 10.2 | 1 | 1 | 0 | s_d6771f90 | limited |
| 23 | Ccl12 | 10.2 | 1 | 5 | 0 | s_7e8c0d49 | limited |
| 24 | Ptx3 | 10.2 | 9 | 11 | 1 | s_b77a67c4 | established |
| 25 | Ccl5 | 10.0 | 6 | 8 | 0 | s_b300fa89 | established |
| 26 | Col27a1 | 9.9 | 0 | 0 | 0 | s_d39a10b2 | not found in top 25 |
| 27 | Slamf1 | 9.8 | 4 | 6 | 0 | s_d7462ee0 | established |
| 28 | Ptges | 9.8 | 6 | 7 | 1 | s_8b4fe51f | established |
| 29 | Il27 | 9.7 | 15 | 16 | 0 | s_c00f0200 | established |
| 30 | Rsad2 | 9.7 | 2 | 2 | 0 | s_789a80a0 | limited |
| 31 | Serpina3f | 9.7 | 1 | 1 | 0 | s_20b0dead | limited |
| 32 | Cxcl9 | 9.6 | 10 | 12 | 0 | s_94ed41dd | established |
| 33 | Hdc | 9.5 | 2 | 9 | 0 | s_805a9c7a | limited |
| 34 | Trim30c | 9.5 | 0 | 2 | 0 | s_38f448a0 | not found in top 25 |
| 35 | Tmem200b | 9.5 | 0 | 0 | 0 | s_5ed74d4f | not found in top 25 |
| 36 | Cxcl2 | 9.3 | 8 | 12 | 0 | s_3a9d9933 | established |
| 37 | Rnd1 | 9.3 | 1 | 1 | 0 | s_cc62c04f | limited |
| 38 | Cxcl1 | 9.3 | 5 | 10 | 1 | s_b4d5b980 | established |
| 39 | Tarm1 | 9.3 | 1 | 2 | 0 | s_bebc3c87 | limited |
| 40 | Cxcl3 | 9.1 | 3 | 8 | 0 | s_037a1293 | established |
| 41 | Ccl17 | 9.1 | 5 | 5 | 0 | s_5e3022fd | established |
| 42 | Rasgrp1 | 9.0 | 5 | 5 | 0 | s_34da7383 | established |
| 43 | Iigp1 | 8.8 | 0 | 2 | 0 | s_375456bc | not found in top 25 |
| 44 | Gbp6 | 8.7 | 0 | 0 | 0 | s_b19e385d | not found in top 25 |
| 45 | Inhba | 8.7 | 1 | 2 | 0 | s_b8de6693 | limited |
| 46 | Gbp2 | 8.7 | 9 | 11 | 0 | s_26a16ee8 | established |
| 47 | Tnfsf4 | 8.7 | 0 | 0 | 0 | s_179a646d | not found in top 25 |
| 48 | Mmp13 | 8.7 | 6 | 7 | 0 | s_bd782759 | established |
| 49 | Bcl2a1a | 8.6 | 2 | 4 | 0 | s_ba67ad68 | limited |
| 50 | Ccl4 | 8.6 | 5 | 8 | 0 | s_81b7b88e | established |

## Files
- `data/paper_ledger.tsv`: 1,250 rows, the top 50 only.
- `results/search/<gene>/` for all 50 genes:
  - raw CLI output (`search.txt`, `map.txt`);
  - `parent.csv`, `map_answers.txt`;
  - `verdicts.csv` (model answer, evidence, context, matched names and stimulus terms, downgrade reason), plus `verdicts_pre_recheck.csv`;
  - `summary.json`.
- `results/search/_runs/`: `chunk5.log`, `recheck.log`, `ledger_before_recheck.tsv`, `chunk5_counts.md`.
- `results/search/pilot5/ledger_pilot.tsv`: the archived pilot rows.
- `src/run_chunk5.sh`, `src/recheck_verdicts.py`, `src/gene_names.py` (`normalize`), `src/search_gene.py` (`apply_checks` / `write_verdicts` refactor).

## For Chunk 6
- **Grade first:** the 6 check-flipped genes above, then the other "limited" and "not found" genes, then the established genes. For established genes, confirmation stops at 3 confirmed papers, so they're cheap.
- **Dedupe:** yes rows are not deduped yet. Chunk 6 collapses them by normalized title.

## Grading plan for Chunk 6 (adopted 2026-09-25)

The full rule is in CLAUDE.md, Chunk 6.
- **Budget:** 4 graders, at most 35 checks each.
- **Round 1:** 130 checks (110 distinct papers + 20 double-graded copies), 32–33 per grader, about 2 hours each.
- **Round 2:** 10 checks kept in reserve.
- **Built by:** `src/make_review_sheet.py` (seed 5).

| Stratum | Genes | Checks |
|---|---|---|
| A1: limited (1–2 yes), every yes | 12 | 16 |
| A2: borderline established (3–5 yes), first 3 yes by rank | 11 | 33 |
| B: not found (0 yes), 3 no rows each, downgraded rows first | 8 | 24 |
| C: other genes whose bin the checks change (Ccl12, Hdc, Bcl2a1a), 2 downgraded rows each | 3 | 6 |
| D: high count (≥6 yes), 1 random yes each | 19 | 19 |
| E: 12 random genes, 1 plain no each | 12 | 12 |
| Double-graded (from A1, A2, B) | n/a | +20 |

**Files:** in `results/review/`:
- `chunk5_review_sheet.csv`: blind, for Google Sheets;
- `chunk5_review_key.csv`: kept closed until grading ends;
- `GRADING_INSTRUCTIONS.txt`.
