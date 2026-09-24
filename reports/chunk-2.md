# Chunk 2 Report: Find and prepare the dataset

**Date:** 2026-09-24
**Status:** ⛔ AT GATE. **Final dataset: GSE250273**, WT BMDMs, LPS 4 h (TrtB01–03) vs. time-matched control (Ctrl01–03), as you decided. `data/counts.csv` and `data/metadata.csv` are rebuilt from it and all gate checks pass. Nothing is committed.

Everything below "History" is the earlier candidate analysis. It's superseded but kept for provenance.

## Dataset card: GSE250273

| Field | Value |
|---|---|
| Accession | GSE250273. Control: GSM7976553–55. LPS: GSM7976565–67. |
| Series title | *Metabolic rewiring promotes anti-inflammatory effects of glucocorticoids* |
| Linked paper | PMID 38600378. **Not in the Paperclip corpus** (see "LPS dose" below). |
| Species / strain | *Mus musculus*, C57BL/6J (Janvier Labs), 8–12 weeks old |
| Cell type | Bone marrow-derived macrophages. DMEM, 10% FCS, 10% L929 supernatant (M-CSF source). |
| Stimulus | LPS. **Dose: "100 ng as stated in GEO; unit not specified."** The GEO text says "100ng LPS", and the paper couldn't be checked. |
| **Time point** | **4 h** (early/intermediate). Chunk 4 controls should be judged on the early-to-mid response: Tnf, Il1b, Il6, Cxcl10 and Nos2 should all be strongly up. |
| Control | Untreated, **harvested at 4 h (time-matched)**, per the GEO title "Control, 4h". |
| Replicates | 3 vs 3. **Not labeled by mouse, so the design is unpaired.** |
| Chunk 4 design | Formula `~ condition`, contrast `condition,LPS,control`. |
| Count generation | NovaSeq 6000 → STAR → featureCounts v2.0.0 (`-p -s 0 -t exon -g gene_id`) with **GENCODE vM29**. Raw integer counts deposited. |
| **Genome build** | **GRCm39** (see below). ⚠ The GEO processing text says "GRCm38/mm10", but the counts' coordinates match GRCm39 exactly. We trust the coordinates. |
| Size | 55,357 genes, of which 23,167 have nonzero counts. Libraries are 18.3–27.9M reads. |
| Gene key | MGI symbols in mouse casing (`Tnf`, `Il1b`, `Nos2`), mapped from vM29 `gene_name`. The duplicate-symbol rule is below. |
| Arms excluded | Glucocorticoid (TrtA), glucocorticoid + LPS (TrtAB), and all 24 h samples. These are listed as held-out contrasts in `CLAUDE.md`, not to be built until after the demo. |

## What was done in this final pass

### 1. Deterministic sample mapping
`src/prep_dataset.py` was rewritten for GSE250273.
- **How the mapping works:**
  - It comes **only** from the series matrix `!Sample_description` field. For example, `TrtB01_4h` maps to count column `TrtB01` after stripping the `_4h`/`_24h` suffix.
  - Each description is joined to its `!Sample_title`, GSM accession, and `treatment:` characteristic.
  - Marker genes are not used for the mapping.
- **Checks that fail loudly** (the script exits with `MAPPING/INPUT ERROR: …`):
  - Descriptions must be unique, and the 24 descriptions must correspond one-to-one with the 24 count columns.
  - Each arm prefix (`Ctrl`, `TrtA`, `TrtB`, `TrtAB`) must map to exactly one GEO treatment across all 24 samples. This catches a shifted mapping.
  - For each selected sample, the title and treatment must equal hard-coded expected values, the genotype must be `WT`, and the sample must be 4 h.
  - Counts must have an integer dtype and be ≥ 0.
- **Negative tests** (run with output redirected to `.cache/`, so `data/` was never touched):
  - Expecting a glucocorticoid title for `TrtB01_4h` → `MAPPING/INPUT ERROR: TrtB01_4h: title 'BMDM cells, LPS stimulated, 4h, WT, replicate #1' != expected '…Glucocorticoid…'`.
  - Swapping TrtB for TrtA → `MAPPING/INPUT ERROR: TrtA01_4h: title '…Glucocorticoid stimulated…' != expected '…LPS stimulated…'`.
  - Both runs exited before writing anything.

**Resulting `data/metadata.csv`:**
```
sample_id,condition,count_column,gsm,geo_title,geo_description
ctrl_1,control,Ctrl01,GSM7976553,"BMDM cells, Control, 4h,WT, replicate #1",Ctrl01_4h
ctrl_2,control,Ctrl02,GSM7976554,"BMDM cells, Control, 4h,WT, replicate #2",Ctrl02_4h
ctrl_3,control,Ctrl03,GSM7976555,"BMDM cells, Control, 4h,WT, replicate #3",Ctrl03_4h
lps_1,LPS,TrtB01,GSM7976565,"BMDM cells, LPS stimulated, 4h, WT, replicate #1",TrtB01_4h
lps_2,LPS,TrtB02,GSM7976566,"BMDM cells, LPS stimulated, 4h, WT, replicate #2",TrtB02_4h
lps_3,LPS,TrtB03,GSM7976567,"BMDM cells, LPS stimulated, 4h, WT, replicate #3",TrtB03_4h
```

**Marker sanity check** (raw counts, printed by the script; **not** used for the mapping). The LPS samples show strong induction and suppressed glucocorticoid-response genes, which fits LPS alone:

| gene | ctrl_1 | ctrl_2 | ctrl_3 | lps_1 | lps_2 | lps_3 |
|---|---|---|---|---|---|---|
| Tnf | 1186 | 735 | 780 | 39206 | 36993 | 30308 |
| Il1b | 51 | 11 | 26 | 136070 | 109234 | 101001 |
| Il6 | 3 | 0 | 0 | 9931 | 9840 | 8581 |
| Cxcl10 | 85 | 90 | 46 | 193008 | 177113 | 146186 |
| Nos2 | 1 | 0 | 1 | 35736 | 32218 | 32187 |
| Tsc22d3 | 1186 | 777 | 842 | 39 | 26 | 30 |
| Fkbp5 | 1662 | 1137 | 1150 | 769 | 673 | 591 |
| Actb | 178427 | 124482 | 119838 | 297894 | 262397 | 222529 |

### 2. LPS dose: one Paperclip pass (not in corpus)
Run at 2026-09-24T17:42:52Z via `src/pc.sh` (paperclip v0.7.52). Output is in `data/geo_search/dose_GSE250273.txt`.

| Step | Command | Search ID | Result |
|---|---|---|---|
| Resolve PMID → PMC | `lookup pmid 38600378` | (none issued) | "No documents found." |
| Same resolution, by title | `lookup title "Metabolic rewiring promotes anti-inflammatory effects of glucocorticoids"` | (none issued) | "No documents found." |
| Same resolution, by accession | `grep "GSE250273" /papers/` | `s_aa3736e1` | No matches (default bounded scan) |

- The paper isn't in the corpus, so there was no methods text to grep and **no matching line to report**.
- Per your rule, the dose is recorded as **"100 ng as stated in GEO; unit not specified"** and I searched no further. That means no `--exhaustive` rerun and no other sources.
- The title and accession lookups were only alternative ways to resolve the same paper, not extra dose searches.

### 3. Genome build: GRCm39
- **Annotation:** `gencode.vM29.annotation.gtf.gz` from the EBI GENCODE FTP (release_M29), 28.7 MB, in `data/raw/`.
  - `gzip -t` passes, and the first line is `##description: evidence-based annotation of the mouse genome (GRCm39), version M29 (Ensembl 106)`.
  - It's checksummed in `data/raw/download_checksums.sha256`.
- **Check:** for each marker, the count file's `Chr`, min(`Start`), max(`End`) and exon-start set were compared against the vM29 `gene` and `exon` records, matched on the versioned gene ID. Output is in `data/geo_search/genome_build_check_GSE250273.txt`.

| gene | vM29 gene_id | vM29 chr:start–end | file chr:minStart–maxEnd | start | end | exon starts ⊆ vM29 |
|---|---|---|---|---|---|---|
| Tnf | ENSMUSG00000024401.15 | chr17:35418357–35420983 | chr17:35418357–35420983 | ✅ | ✅ | ✅ |
| Il1b | ENSMUSG00000027398.14 | chr2:129206490–129213059 | chr2:129206490–129213059 | ✅ | ✅ | ✅ |
| Il6 | ENSMUSG00000025746.12 | chr5:30218112–30224979 | chr5:30218112–30224979 | ✅ | ✅ | ✅ |
| Cxcl10 | ENSMUSG00000034855.14 | chr5:92494497–92496748 | chr5:92494497–92496748 | ✅ | ✅ | ✅ |
| Nos2 | ENSMUSG00000020826.10 | chr11:78811613–78851080 | chr11:78811613–78851080 | ✅ | ✅ | ✅ |

**Result:**
- All five genes match vM29 **exactly**, including the versioned gene IDs. **The counts are on GRCm39**, which confirms your hunch.
- GEO's "GRCm38/mm10" processing text is wrong or out of date. This is noted on the dataset card.
- vM29 is therefore the annotation used for Ensembl-to-symbol mapping.
- All 55,357 count-file gene IDs are present in vM29. The script asserts this.

**Duplicate symbols:**
- **What happens:** 980 gene IDs fall into 79 groups that share a `gene_name`. Most are misc_RNA, rRNA and snRNA copies. 21 groups include a protein-coding gene, such as Aldoa, Ddit3, Ptp4a1 and Zc3h11a.
- **Rule:** annotation only, no counts involved. The **oldest (lowest-numbered) Ensembl accession keeps the plain symbol**. In vM29 that is the canonical locus, and the newer IDs are readthrough or fragment models. The other 901 IDs get `|ENSMUSG…` appended so the join key stays unique.
- **One imperfect case:** for `Snhg4`, the plain symbol goes to a low-count protein-coding model (…117694), while the expressed lncRNA is `Snhg4|ENSMUSG00000117869.2`. It's rarely relevant, but if a suffixed gene lands in the top 50 we'll handle it by hand.
- Full mapping: `data/gene_map.csv`, with columns gene, ensembl_id, gene_name, gene_type, duplicated_symbol.

### 4. Download verification
- A new convention in `CLAUDE.md` says every download is checked before use (`gzip -t` plus the expected header or first line). A failed download is logged and deleted, never kept.
- **All 13 kept downloads pass `gzip -t`.**
- **GSE82043's saved "series matrix" was an HTML "Object not found!" page**, even though `curl` exited 0. It was an unchecked download from the 4–8 h screen. **I deleted it** and logged it in `data/geo_search/download_failures.tsv`. It was not fetched again, since that series had already been rejected.
- `download_checksums.sha256` was regenerated over the 13 kept files.

### 5. Housekeeping
- **`src/pc.sh`:** a Paperclip wrapper that strips `.venv/bin` from `PATH` and unsets `VIRTUAL_ENV`. `CLAUDE.md`'s environment section now says to use it.
- **`data/raw/geo_search/` moved to `data/geo_search/`,** which is tracked in git (816 KB). It holds the search output, per-series sections, the dose and genome-build checks, and the failure log. Paths in the History section were updated to match.
- **`CLAUDE.md` changes:**
  - New section "Held-out contrasts (post-demo, only if the pipeline works)": Dex vs. control 4 h, Dex + LPS vs. LPS 4 h, and the same at 24 h. Not built or run.
  - The download-verification convention.
  - The dataset decision marked resolved.
- **Still in `data/raw/` (gitignored):**
  - Earlier candidate files: GSE184551, GSE201128 and GSE263905 counts and matrices.
  - The `screen_4to8h/` series matrices.
  - The vM29 GTF.
  These are kept as provenance for the History section. Delete them if you'd rather keep `data/raw/` minimal.

## Gate checks

| Check | Result |
|---|---|
| Dataset exists | ✅ `data/raw/GSE250273_genecount.txt.gz`: `gzip -t` OK, the featureCounts header is as expected, and it's checksummed. |
| Labels make sense | ✅ Mapping comes from `!Sample_description` → title → treatment, asserted as described in section 1. The marker check is consistent. |
| Raw integers | ✅ Integer dtype, minimum 0, maximum about 1.46M. featureCounts output. |

**Outputs:** `data/counts.csv` (55,357 genes × 6 samples, first column `gene`), `data/metadata.csv`, and `data/gene_map.csv`. All three are rebuilt with `.venv/bin/python src/prep_dataset.py`.

## Open items
- **Dose unit:** "100ng LPS" has no unit, and it can't be checked in Paperclip. Almost certainly 100 ng/mL in practice, but I'm recording it as unspecified, as you instructed.
- **Paperclip still auto-updates and still carries the stale `[repo: mva-lof-molecular]` context.** Both are unchanged from the History section.

---

# History (earlier candidate analysis; superseded by the final decision above)

### 1. Paperclip GEO search: parameters used

**Environment**
- The CLI was `paperclip` v0.7.49. It **auto-updated itself to v0.7.52** on the first call (see Surprises).
- All searches ran with source `-s geo`, cap `-n 25`, and default sort, with no year or date filter.
- Run date: 2026-09-24, about 17:15 UTC.
- Raw search output is saved under `data/geo_search/`: `q1.txt`, `q2_q3.txt`, and `q2_q4.txt`.

| # | Query (verbatim) | Search ID | Hits |
|---|---|---|---|
| 1 | `LPS stimulated bone marrow-derived macrophages RNA-seq mouse` | `s_c54779eb` | 25 |
| 2 | `macrophage lipopolysaccharide time course unstimulated control raw counts RNA-seq mouse` | `s_45bfe197` | **0** |
| 3 | `BMDM LPS 4 hours versus unstimulated bulk RNA-seq triplicates` | `s_ffa41668` (rerun: `s_7769b45b`) | **0** |
| 4 | `LPS macrophage RNA-seq` | `s_26f4c77f` | 25 |
| 5 | `lipopolysaccharide BMDM time course` | `s_5647cfa9` | 2 |
| 6 | `LPS unstimulated macrophages mouse` | `s_2f1f6487` | 25 |

Command form: `paperclip search -s geo -n 25 "<query>"`.

**Search behavior:** long queries with many terms returned 0 hits. The GEO search appears to require most terms to match, so short queries work better.

**Candidate screening.** I screened 12 series from queries 1, 4 and 6 that looked like mouse BMDM bulk RNA-seq with an LPS arm: GSE184551, GSE58993, GSE205238, GSE263905, GSE195687, GSE287441, GSE174141, GSE273173, GSE245834, GSE122070, GSE201128, and GSE213050.
- For each, I read `/geo/<GSE>/meta.json` plus the `Samples`, `Traits`, `SupplementaryFiles` and `FileList` sections, using `paperclip cat --full`. Copies are saved in `data/geo_search/<GSE>/`.
- The Paperclip GEO index has no sample-level protocol text (dose, pipeline). For the three finalists I took that from the GEO series matrix, downloaded from the NCBI FTP.

**Why the other nine were rejected:**

| Series | Reason |
|---|---|
| GSE205238 | Every sample is LPS-treated, so there's no unstimulated arm. n = 2. |
| GSE58993 | LPS-only design, n = 2. |
| GSE195687 | n = 1 per genotype. FPKM only. |
| GSE287441 | n = 1. TPM only. |
| GSE174141 | n = 2. |
| GSE245834 | LPS + IFNγ, not LPS alone. Normalized counts only. n = 2. |
| GSE122070 | n = 2. Normalized abundance only. |
| GSE213050 | The WT is Prep+/−, not a true wild type. |
| GSE273173 | LPS on day 7 in a trained-immunity design, not a clean acute LPS response. |

### 2. Top 3 candidates

| | **GSE201128** (recommended) | **GSE263905** | **GSE184551** |
|---|---|---|---|
| Design used | B6, no pre-treatment: unstim vs LPS | B6: unstim vs LPS | B6: unstim vs LPS |
| Replicates | 3 vs 3, **paired by mouse** | 3 vs 3 (mice A–C) | 3 vs 3 |
| Time point | **18 h (late)** | 2 h (early) | 2 h (early) |
| LPS dose | 10 ng/mL | **not stated** | **not stated** |
| Differentiation | BMDM (protocol per Gold 2012) | L929-conditioned medium | M-CSF 10 ng/mL |
| Counts | featureCounts, GSNAP, mm10. **Integer ✅** | featureCounts, STAR, GRCm39/GENCODE M32. **Integer ✅** | RSEM expected counts. **9% non-integer ❌** |
| Gene IDs | Ensembl **+ symbols** | Ensembl only (needs mapping) | Ensembl_symbol |
| Library size (millions of reads) | 30.6–40.9 | 14.6–30.4 | **3.7**–10.5 |
| Library prep | TruSeq stranded, NovaSeq | TruSeq directional, MiSeq | Smart-seq2 from 1 ng RNA (amplified) |

**Rough log2 fold change for positive controls,** computed as log2((mean LPS + 1)/(mean ctrl + 1)) on raw means. This is a sanity check only, not DE:

| Gene | GSE201128 (18 h) | GSE263905 (2 h) | GSE184551 (2 h) |
|---|---|---|---|
| Tnf | 2.0 | 5.2 | 8.2 |
| Il1b | 9.8 | 7.4 | 9.7 |
| Il6 | 5.8 | 10.0 | 5.4 |
| Cxcl10 | 4.7 | 7.5 | 8.3 |
| Nos2 | 13.8 | 9.2 | 6.2 |
| Actb | −0.2 | 0.3 | 0.8 |

All three respond strongly. The pattern matches the expected time points:
- **Tnf** peaks early and has mostly faded by 18 h.
- **Nos2** is a secondary-response gene, so it is largest at 18 h.

**Why I recommend GSE201128:**
1. **Clean input.** The counts are raw integers, and gene symbols come with the file, so we don't need a symbol-mapping step for the join key. The dose is documented, and it has the deepest libraries.
2. **Paired by mouse.** Each mouse contributes one control and one LPS sample. That allows `~ mouse + condition` in Chunk 4, which should absorb mouse-to-mouse variation.
3. **Better fit for the project's question.** At 2 h, the top induced genes are dominated by classic immediate-early and primary-response genes (Tnf, Cxcl1/2, Egr, Ier…), which are among the most studied genes in immunology. That pushes nearly everything into "established." At 18 h, the list includes secondary-response, metabolic and interferon-driven genes, so the "limited" and "not found" bins are more likely to hold something. This is a judgment call, and it's the main reason the choice isn't clear-cut.

**Case for GSE263905 instead:** the early time point is the textbook LPS response, and Tnf would be a strong positive control. The costs are an undocumented dose, an extra Ensembl-to-symbol mapping step (downloading the GENCODE M32 annotation), and shallower libraries sequenced on a MiSeq.

GSE184551 is last. RSEM expected counts would have to be rounded, the libraries are amplified from 1 ng of RNA, and the controls have only about 3.7M reads.

### 3. Dataset card: GSE201128 (built, later replaced by GSE250273)

| Field | Value |
|---|---|
| Accession | GSE201128 (GSM6051417–19 control; GSM6051429–31 LPS) |
| Title | The response to LPS of BMDMs treated with OSBP inhibitors |
| Submitter | Seattle Children's Research Institute. No linked PubMed ID in GEO. |
| Species | *Mus musculus*, C57BL/6, female |
| Cell type | Bone marrow-derived macrophages |
| Stimulus | LPS, 10 ng/mL |
| **Time point** | **18 h** (late). Chunk 4 controls should be judged on the late response: Nos2, Il1b, Cxcl10 and Il6 strongly up; Tnf only modestly up. |
| Subset used | `B6.none.none.0.{1,2,3}` (control) vs `B6.none.LPS.18.{1,2,3}` (LPS). No drug pre-treatment. The drug arms and Ch25h−/− samples are excluded. |
| Replicates | 3 vs 3. Mice 1–3 each give one control and one LPS sample. |
| Count generation | TruSeq stranded, NovaSeq 6000 → GSNAP (2018-07-04), mm10 with Ensembl GRCm38.78 splice sites → featureCounts (Subread 1.5.2). Raw integer counts deposited. |
| Size | 30,538 genes, of which 16,605 have nonzero counts in the 6 samples. Libraries are 30.6–40.9M reads. |
| Gene key | **MGI mouse symbols, capitalized first letter only (`Tnf`, `Il1b`, `Nos2`)**. This is the join key for all later chunks. Symbols are unique, and Ensembl IDs are kept in `data/gene_map.csv`. |

#### Gate checks
- **Dataset exists:** ✅ Raw file is `data/raw/GSE201128_rawCounts.tsv.gz`. The sha256 is in `data/raw/download_checksums.sha256`, and the download time was 2026-09-24T17:16Z.
- **Labels make sense:** ✅ `src/prep_dataset.py` checks every label against GEO's own characteristics (genotype, treatment = none, stimulus, stimtime, mouse) and asserts on any mismatch. The resulting `data/metadata.csv`:
  ```
  sample_id,condition,mouse,gsm,geo_title
  ctrl_m1,control,m1,GSM6051417,B6.none.none.0.1 (OSBP control)
  ...
  lps_m3,LPS,m3,GSM6051431,B6.none.LPS.18.3
  ```
- **Raw integers:** ✅ The script asserts an integer dtype and no negative values. The maximum value is about 1.8M, consistent with raw counts rather than normalized values.

#### Outputs
- `data/counts.csv`: first column `gene`, then samples `ctrl_m1..3` and `lps_m1..3`.
- `data/metadata.csv`: columns `sample_id, condition, mouse, gsm, geo_title`.
- `data/gene_map.csv`: symbol to Ensembl ID.
- `src/prep_dataset.py`: rebuilds all three from `data/raw/`.
- `data/raw/`: the three candidate count files, three series matrices, the checksum file, and `geo_search/`.

**Contrast for Chunk 4:** `condition,LPS,control`. Formula: `~ mouse + condition` (recommended, paired) or `~ condition`.

### Caveats and surprises

1. **The control isn't time-matched.** The controls have `stimtime: 0`, so they appear to be harvested when LPS was added, while the LPS samples spent 18 h more in culture. Genes that change with culture time alone could appear as "LPS-induced." Mitigation: every candidate gene's evidence gets checked against the literature anyway, but any top gene with no known inflammatory link deserves a second look.
2. **Mouse 3's LPS sample responds more weakly.** Tnf, Il6 and Nos2 are 3–4× lower in `lps_m3` than in m1/m2, while Il1b and Cxcl10 are similar. This is within normal variation, and the paired design helps. Watch for it in the Chunk 4 PCA.
3. **Paperclip auto-updated itself** (0.7.49 → 0.7.52) during the first search. The CLI did this on its own, and the write went to its own install location outside the project. I couldn't prevent it without knowing an opt-out. If you want to pin the version, it needs a setting on your side.
4. **Paperclip vs. the project venv.** With `.venv` active, paperclip's `#!/usr/bin/env python3` picks up the venv Python, which lacks `requests`, and it crashes. Workaround used, with no installs: run paperclip with `.venv/bin` removed from `PATH` and `VIRTUAL_ENV` unset. Chunk 3 onward will need the same. A small `src/pc.sh` wrapper would make that repeatable.
5. **A leftover Paperclip repo is active.** Every command printed `[repo: mva-lof-molecular]` from an unrelated earlier task. Paperclip's docs say to ignore it, so I didn't add anything to it. The searches may still be logged in its history. `paperclip git checkout -` would deactivate it, but I left it alone because it isn't this project's state.
6. **`data/raw/` is gitignored,** including `geo_search/` (324 KB of search output and sections). That output is the provenance for this chunk's candidate selection. **Suggestion:** move `geo_search/` to `data/geo_search/` so it's tracked. The count files (about 3 MB total) could also be tracked, since they're small.
7. **`.gitignore` updated as you asked:** `results/de/*/figures/` is no longer ignored, so figures will be committed. Only `normalized_counts.csv` is still ignored.

### Decision needed
- **Dataset:** GSE201128 (recommended, 18 h) or GSE263905 (2 h)?
- Optional: move `geo_search/` out of the ignored `data/raw/`?

---

### Addendum (2026-09-24, about 17:26–17:29 UTC): 4–8 h search and GSE263905 dose

**Why this pass happened:** you prefer an early time point (you've used 4 h and 8 h). You asked for (1) a targeted 4–8 h search, then (2) a check of whether GSE263905's paper gives the LPS dose. Your rule: if the dose is found and nothing better turns up, use GSE263905. If the dose can't be recovered, use GSE201128 and note the culture-time caveat.

#### A1. 4–8 h Paperclip GEO searches

These used the same CLI setup as before, now at v0.7.52: `paperclip search -s geo -n 25 "<query>"`, default sort, no date filter. Output is saved in `data/geo_search/q5_q11_4to8h.txt`.

| # | Query (verbatim) | Search ID | Hits |
|---|---|---|---|
| 7 | `BMDM LPS 4h` | `s_6068edec` | 25 |
| 8 | `BMDM LPS 6h` | `s_6a6454a4` | 16 |
| 9 | `BMDM LPS 8h` | `s_26e90c6a` | 16 |
| 10 | `macrophage LPS 4 hours` | `s_c1be48a2` | 25 |
| 11 | `macrophage LPS 6 hours` | `s_83f47676` | 25 |
| 12 | `bone marrow macrophages LPS 4 hr RNA-seq` | `s_9adba998` | 2 |
| 13 | `LPS time course macrophages RNA-seq` | `s_ba47ada4` | 25 |

**Screening.** I screened 27 plausible mouse series the same way as before. Section text is in `data/geo_search/<GSE>/`. For six finalists I also pulled series matrices, which are in `data/raw/screen_4to8h/` plus the GSE250273 matrix in `data/raw/`.

**Rejected:**
- **Microarrays:** GSE101959, GSE115120, GSE121646, GSE192517, GSE20207, GSE33162.
- **n ≤ 2 or n = 1 per condition:** GSE181641, GSE181642 and GSE181643 (n = 2 time course); GSE141473 (n = 1); GSE93598 and GSE93735 (n = 2, FPKM).
- **No raw counts deposited:**
  - Normalized values or DE tables only: GSE163549, GSE261824, GSE141688, GSE255322, GSE278668.
  - GSE169730 has 6 h time-matched controls with n = 3, but only RPKM and DESeq2 spreadsheets.
- **Wrong cells or stimulus:** GSE238236 and GSE176174 (peritoneal macrophages); GSE115354 and GSE82043 Exp2 (LPS + IFNγ).
- **Wrong genotype:** GSE261444. The "WT" is KSRP+/−, and the cells were differentiated in GM-CSF.
- **Weaker than the winner:**
  - GSE225831: htseq counts at 2 h and 8 h, but data processing "none provided" and an unclear WT sample layout.
  - GSE211989: LPS time and dose not stated.

**Winner: GSE250273 (4 h).** Series title: *Metabolic rewiring promotes anti-inflammatory effects of glucocorticoids*. I did not look up the authors or the linked paper.
- **Design:** WT C57BL/6J BMDMs. 3 controls harvested **at 4 h (time-matched)** vs. 3 treated with **100 ng/mL LPS for 4 h**. The series also has glucocorticoid, glucocorticoid + LPS, and 24 h arms, which we'd exclude.
- **Culture:** DMEM, 10% FCS, 10% L929 supernatant as the M-CSF source.
- **Pipeline:** NovaSeq 6000 → STAR (mm10) → featureCounts v2.0.0 (GENCODE vM29). The file holds **raw integer counts** (verified: integer dtype, min 0, max about 1.46M). Libraries are 18.3–27.9M reads.
- **Sample key:** the count-file columns (`Ctrl`, `TrtA`, `TrtAB`, `TrtB`) are in a different order from GEO's sample list. GEO's `Sample_description` maps TrtA = glucocorticoid, TrtB = LPS, TrtAB = both. **I confirmed this from the data** (4 h samples, raw counts):

| Gene | Ctrl01–03 | TrtA (GC) | TrtAB (GC+LPS) | TrtB (LPS) |
|---|---|---|---|---|
| Tnf | 1186 / 735 / 780 | ~200 | ~35,000 | 39,206 / 36,993 / 30,308 |
| Il1b | 51 / 11 / 26 | ~3 | ~32,000 | 136,070 / 109,234 / 101,001 |
| Il6 | 3 / 0 / 0 | ~0 | ~8,300 | 9,931 / 9,840 / 8,581 |
| Cxcl10 | 85 / 90 / 46 | ~2 | ~58,000 | 193,008 / 177,113 / 146,186 |
| Nos2 | 1 / 0 / 1 | 0 | ~8,000 | 35,736 / 32,218 / 32,187 |
| Tsc22d3 (GC marker) | 1186 / 777 / 842 | ~22,000 | ~4,800 | 39 / 26 / 30 |
| Fkbp5 (GC marker) | 1662 / 1137 / 1150 | ~34,000 | ~9,500 | 769 / 673 / 591 |

**What the table shows:**
- TrtB has the strongest LPS response and no glucocorticoid signature, so it is LPS alone.
- The three LPS replicates agree closely, with none of the weak-replicate issue seen in GSE201128.
- Caveats:
  - Replicates aren't labeled by mouse, so an unpaired `~ condition` design is used.
  - IDs are Ensembl-only, so we need a symbol mapping (GENCODE vM29 annotation, same as their pipeline).

#### A2. GSE263905 dose: found

These are Paperclip corpus searches, with output in `data/geo_search/dose_GSE263905.txt`:
1. `paperclip grep "GSE263905" /papers/` returned `s_2495d67c`, one hit: **PMC11465231**. Its data availability table says "Gene Expression Omnibus | This paper | GEO: GSE263905".
2. `paperclip search -s pmc,biorxiv,medrxiv -n 10 "RIPK1 T169A knock-in macrophages LPS 5z7"` returned `s_bc270388`, and PMC11465231 is the #1 hit. This is Jetton et al. 2024, *Non-canonical autophosphorylation of RIPK1 drives timely pyroptosis to control Yersinia infection*. The same paper was found by two independent routes.
3. `paperclip grep -i "ng/ml|µg/ml|ug/ml|RNA-seq|RNA seq|RNA sequencing|LPS [(]" /papers/PMC11465231/content.lines`. Line 65 of that file says: "LPS Escherichia coli 011: B4 (**10 ng/mL for all BMDM assays** and 100 ng/mL for all MEFs, L4391)". The Figure 2 legend (line 89) confirms that the RNA-seq was on primary B6 and T169A BMDMs, N = 3 per genotype and stimulation.

   **Caveat:** the dose is stated for "all BMDM assays" in general, not specifically for the RNA-seq experiment.

(An earlier grep for `T169A` alone across `/papers/` matched mostly arXiv "DenseNet169A" noise. It wasn't useful and I didn't pursue it.)

#### A3. Where that leaves the decision

Both early options are now viable. Your rule says use GSE263905 unless something better turned up, and I think **GSE250273 is better**:

| | **GSE250273 (4 h)**, recommended | GSE263905 (2 h) | GSE201128 (18 h) |
|---|---|---|---|
| Time point | **4 h**, in your usual range | 2 h | 18 h |
| Dose | 100 ng/mL (GEO) | 10 ng/mL (paper, "all BMDM assays") | 10 ng/mL (GEO) |
| Control timing | **Time-matched, explicit** ("Control, 4h") | Probably matched, not stated | **Not matched** (0 h vs 18 h) |
| n | 3 vs 3 (unpaired) | 3 vs 3 (probably paired by mouse) | 3 vs 3 (paired) |
| Counts | featureCounts, integers | featureCounts, integers | featureCounts, integers |
| Depth / platform | 18–28M, NovaSeq | 15–30M, MiSeq | 31–41M, NovaSeq |
| Replicate consistency | Tight | Good | lps_m3 weak |
| Symbols | Need mapping (vM29) | Need mapping (M32) | Included |

**Recommendation: GSE250273.** It sits in your usual 4–8 h range, its time-matched controls are stated explicitly, the dose is documented, and the replicates are tight.

**Current file state:** `data/counts.csv`, `data/metadata.csv` and `data/gene_map.csv` are **still built from GSE201128**. Once you pick, I'll rebuild them with the chosen dataset:
- rewrite `src/prep_dataset.py`;
- add the GENCODE annotation download to `data/raw/` for the Ensembl-to-symbol mapping (the file is roughly tens of MB and is gitignored);
- rerun the gate checks.

All downloads are checksummed in `data/raw/download_checksums.sha256`.
