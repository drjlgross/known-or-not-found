"""Chunk 5 verification / Chunk 6 confirmation, round 1: a blind, stratified grading sheet from the ledger.

Budget: 4 graders x 35 checks = 140. Round 1 uses <= 33 per grader (132); the rest is reserved for round 2
(follow-ups on boundary genes that fall short of 3 confirmed, and third-grader adjudication of disagreements).
Checks go where an error would change a bin or the headline claim (seed 5):

  A1 limited genes (1-2 yes)          every yes row                      -> confirmed count is exact
  A2 boundary established (3-5 yes)    first 3 yes rows by rank           -> 3 confirmed = established; else round 2
  B  "not found" genes (0 yes)         3 no rows (downgraded first)       -> false negatives behind the headline claim
  C  other genes whose bin the checks change (model count vs. after checks)
                                       2 downgraded rows                  -> real yeses lost to the checks
  D  high-count established (>= 6 yes) 1 random yes row                   -> precision where the bin is safe
  E  12 random other genes             1 random plain no row              -> background false-negative rate
  Double grading: 20 round-1 tasks (6 from A1, 8 from A2, 6 from B) go to a second grader.

Outputs (results/review/):
  chunk5_review_sheet.csv  what graders see: no ledger verdict, model answer or downgrade reason (blind)
  chunk5_review_key.csv    task_id -> stratum, ledger verdict, model answer, downgrade, duplicate-title flag
"""
import csv
import json
import random
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import gene_names  # noqa: E402

OUT = ROOT / "results/review"
GRADERS = ["G1", "G2", "G3", "G4"]
ROUND1_CAP = 33
rng = random.Random(5)
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

top = [r["gene"] for r in csv.DictReader(open(ROOT / "data/top_genes.csv"))]
ledger = [r for r in csv.DictReader(open(ROOT / "data/paper_ledger.tsv"), delimiter="\t") if r["status"] == "ok"]


def bin_of(n: int) -> str:
    return "not found" if n == 0 else "limited" if n <= 2 else "established"


def link(pid: str, title: str) -> str:
    if pid.startswith("PMC"):
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{pid}/"
    return "https://www.biorxiv.org/search/" + urllib.parse.quote(title[:120])


G = {}
for g in top:
    v = {r["paper_id"]: r for r in csv.DictReader(open(ROOT / f"results/search/{g}/verdicts.csv"))}
    rows = sorted((r for r in ledger if r["gene"] == g), key=lambda r: int(r["rank"]))
    s = json.loads((ROOT / f"results/search/{g}/summary.json").read_text())
    no = [r for r in rows if r["verdict"] == "no"]
    G[g] = dict(v=v, rows=rows, yes=[r for r in rows if r["verdict"] == "yes"],
                down=[r for r in no if v[r["paper_id"]]["downgraded"]],
                plain=[r for r in no if not v[r["paper_id"]]["downgraded"]],
                flipped=bin_of(s["yes"]) != bin_of(s["yes_before_checks"]))

picks = []  # (gene, ledger row, stratum)
for g in top:
    d, n = G[g], len(G[g]["yes"])
    if n == 0:
        nos = d["down"][:3]
        nos += rng.sample(d["plain"], 3 - len(nos))
        picks += [(g, r, "B_not_found_no") for r in nos]
    elif n <= 2:
        picks += [(g, r, "A1_limited_yes") for r in d["yes"]]
    elif n <= 5:
        picks += [(g, r, "A2_boundary_yes") for r in d["yes"][:3]]
    else:
        picks += [(g, rng.choice(d["yes"]), "D_high_count_yes")]
    if n > 0 and d["flipped"] and d["down"]:
        picks += [(g, r, "C_downgraded") for r in rng.sample(d["down"], min(2, len(d["down"])))]
e_genes = rng.sample([g for g in top if G[g]["yes"] and G[g]["plain"]], 12)
picks += [(g, rng.choice(G[g]["plain"]), "E_random_no") for g in e_genes]

tasks = []
for g, r, stratum in picks:
    a = G[g]["v"][r["paper_id"]]
    titles = [norm(x["title"]) for x in G[g]["rows"]]
    tasks.append({"gene": g, "stratum": stratum, "row": r, "a": a,
                  "dup": titles.count(norm(r["title"])) > 1})
rng.shuffle(tasks)  # blind: task order doesn't reveal stratum or verdict

# double grading: 6 A1, 8 A2, 6 B
dbl = set()
for stratum, k in (("A1_limited_yes", 6), ("A2_boundary_yes", 8), ("B_not_found_no", 6)):
    pool = [i for i, t in enumerate(tasks) if t["stratum"] == stratum]
    dbl |= set(rng.sample(pool, min(k, len(pool))))

# assignment: whole genes to graders (balanced), then second copies to the least-loaded other grader
load = {x: 0 for x in GRADERS}
owner = {}
per_gene = {}
for t in tasks:
    per_gene[t["gene"]] = per_gene.get(t["gene"], 0) + 1
for g in sorted(per_gene, key=lambda g: -per_gene[g]):
    x = min(load, key=load.get)
    owner[g] = x
    load[x] += per_gene[g]
second = {}
for i in sorted(dbl):
    x = min((y for y in GRADERS if y != owner[tasks[i]["gene"]]), key=load.get)
    second[i] = x
    load[x] += 1
assert max(load.values()) <= ROUND1_CAP, load

sheet, key, n = [], [], 0
for i, t in enumerate(tasks):
    r, a = t["row"], t["a"]
    names = "; ".join(dict.fromkeys(gene_names.all_names(t["gene"]) + gene_names.human_names(t["gene"])))
    for grader in [owner[t["gene"]]] + ([second[i]] if i in second else []):
        n += 1
        tid = f"T{n:03d}"
        sheet.append({"task_id": tid, "grader_slot": grader, "double_graded": "yes" if i in second else "",
                      "gene": t["gene"], "gene_names": names, "rank": r["rank"], "paper_id": r["paper_id"],
                      "link": link(r["paper_id"], r["title"]), "title": r["title"],
                      "quote_result": a["evidence"], "quote_context": a["context"],
                      "grader": "", "call": "", "reason": "", "where_in_paper": "", "notes": ""})
        key.append({"task_id": tid, "gene": t["gene"], "paper_id": r["paper_id"], "stratum": t["stratum"],
                    "ledger_verdict": r["verdict"], "model_answer": a["model_answer"], "downgraded": a["downgraded"],
                    "duplicate_title_in_gene": "yes" if t["dup"] else ""})
sheet.sort(key=lambda x: (x["grader_slot"], x["gene"], x["task_id"]))
for name, rows in (("chunk5_review_sheet.csv", sheet), ("chunk5_review_key.csv", key)):
    with open(OUT / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
strata = {}
for t in tasks:
    strata[t["stratum"]] = strata.get(t["stratum"], 0) + 1
print(json.dumps({"round1_tasks": len(sheet), "unique_papers": len(tasks), "double_graded": len(second),
                  "per_grader": load, "round2_reserve": 4 * 35 - len(sheet), "strata": strata}, indent=1))
