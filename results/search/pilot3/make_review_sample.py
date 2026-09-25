"""Draw the Chunk 3 hand-review sample (5 calls per gene; Tnf has only 1 no, so 4 yes + 1 no) from the canonical ledger + verdicts.csv.
Deterministic: seed 3. Per gene: up to 3 yes, rest no, preferring downgraded rows among the no's
(the name check is the riskiest rule)."""
import csv, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/search/pilot3/named_strict_n25"
PLAN = {"Tnf": 4, "Slc7a2": 3, "Hdc": 2}   # gene -> number of yes rows
rng = random.Random(3)
led = [r for r in csv.DictReader(open(ROOT / "data/paper_ledger.tsv"), delimiter="\t") if r["status"] == "ok"]
out = ["# Chunk 3 hand-review sample (Round 3, canonical ledger)", "",
       "Mark each row right/wrong. \"yes\" = the paper's own data show the gene's expression changing with LPS or bacterial infection.", ""]
for g, ny in PLAN.items():
    v = {r["paper_id"]: r for r in csv.DictReader(open(RUN / g / "verdicts.csv"))}
    rows = [r for r in led if r["gene"] == g]
    yes = [r for r in rows if r["verdict"] == "yes"]; no = [r for r in rows if r["verdict"] == "no"]
    down = [r for r in no if v[r["paper_id"]]["downgraded"]]; plain = [r for r in no if not v[r["paper_id"]]["downgraded"]]
    pick_no = rng.sample(down, min(2, len(down))); pick_no += rng.sample(plain, 5 - ny - len(pick_no))
    pick = sorted(rng.sample(yes, ny) + pick_no, key=lambda r: int(r["rank"]))
    out += [f"## {g} (search {rows[0]['search_id']}, query `{rows[0]['query']}`)", "",
            "| rank | paper | title | ledger verdict | model said | evidence quote | name check | your call |", "|---|---|---|---|---|---|---|---|"]
    for r in pick:
        x = v[r["paper_id"]]; ev = x["evidence"].replace("|", "/").replace("\n", " ")
        out.append(f"| {r['rank']} | {r['paper_id']} | {r['title'][:80]} | **{r["verdict"]}** | {"yes" if x["downgraded"] else x["answer"]} | {ev[:300]} | {x['downgraded'] or 'pass'} | |")
    out.append("")
(ROOT / "results/search/pilot3/review_sample.md").write_text("\n".join(out))
