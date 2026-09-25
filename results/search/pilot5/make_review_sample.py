"""Draw the Chunk 3 Round 5 hand-review sample (evidence + context quotes, HGNC aliases; same draw rules as Round 3: 5 calls per gene; Tnf has only 1 no, so 4 yes + 1 no) from the canonical ledger + verdicts.csv.
Deterministic: seed 3. Per gene: up to 3 yes, rest no, preferring downgraded rows among the no's
(the name check is the riskiest rule)."""
import csv, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/search/pilot5/two_quote_n25"
PLAN = {"Tnf": 3, "Slc7a2": 3, "Hdc": 2}   # gene -> number of yes rows
rng = random.Random(3)
led = [r for r in csv.DictReader(open(ROOT / "data/paper_ledger.tsv"), delimiter="\t") if r["status"] == "ok"]
out = ["# Chunk 3 hand-review sample (Round 5, canonical ledger)", "",
       "Mark each row right/wrong. \"yes\" = the paper's own data show the gene's expression changing with LPS or bacterial infection.", ""]
for g, ny in PLAN.items():
    v = {r["paper_id"]: r for r in csv.DictReader(open(RUN / g / "verdicts.csv"))}
    rows = [r for r in led if r["gene"] == g]
    yes = [r for r in rows if r["verdict"] == "yes"]; no = [r for r in rows if r["verdict"] == "no"]
    down = [r for r in no if v[r["paper_id"]]["downgraded"]]; plain = [r for r in no if not v[r["paper_id"]]["downgraded"]]
    ny = min(ny, len(yes))
    pick_no = rng.sample(down, min(2, len(down), 5 - ny)); pick_no += rng.sample(plain, 5 - ny - len(pick_no))
    pick = sorted(rng.sample(yes, ny) + pick_no, key=lambda r: int(r["rank"]))
    out += [f"## {g} (search {rows[0]['search_id']}, query `{rows[0]['query']}`)", "",
            "| rank | paper | title | ledger verdict | model said | evidence // context | gene / stimulus terms found | downgrade | your call |", "|---|---|---|---|---|---|---|---|---|"]
    for r in pick:
        x = v[r["paper_id"]]; ev = (x["evidence"] + (" // " + x["context"] if x["context"] else "")).replace("|", "/").replace("\n", " ")
        out.append(f"| {r['rank']} | {r['paper_id']} | {r['title'][:80]} | **{r["verdict"]}** | {x["model_answer"]} | {ev[:450]} | {x['evidence_names'] or '-'} / {x['evidence_stimulus'] or '-'} | {x['downgraded'] or 'none'} | |")
    out.append("")
R3 = ROOT / "results/search/pilot4/named_stim_n25"
out += ["## Optional: every verdict that changed from Round 4 to Round 5", "",
        "Same papers (all 12 genes had identical top 25s). Is the Round 5 verdict the right one?", "",
        "| gene | rank | paper | title | R4 → R5 | why | Round 5 evidence // context | your call |", "|---|---|---|---|---|---|---|---|"]
for g in ["Tnf", "Nos2", "Edn1", "Slc7a2", "Tnfsf15", "Hdc", "Tarm1", "Calhm6", "Rnd1", "Lipg", "Col27a1", "Hcar2"]:
    a = {r["paper_id"]: r for r in csv.DictReader(open(R3 / g / "verdicts.csv"))}
    b = {r["paper_id"]: r for r in csv.DictReader(open(RUN / g / "verdicts.csv"))}
    for p in sorted(set(a) & set(b), key=lambda p: int(b[p]["rank"])):
        if "success" == a[p]["judge_status"] == b[p]["judge_status"] and a[p]["answer"] != b[p]["answer"]:
            why = b[p]["downgraded"] or (f"Round 4 downgrade ({a[p]['downgraded'][8:]}) now passes" if a[p]["downgraded"] else "model answer changed")
            ev = ((b[p]["evidence"] or "(none)") + (" // " + b[p]["context"] if b[p]["context"] else "")).replace("|", "/").replace("\n", " ")[:400]
            out.append(f"| {g} | {b[p]['rank']} | {p} | {b[p]['title'][:70]} | {a[p]['answer']} → **{b[p]['answer']}** | {why} | {ev} | |")
out.append("")
(ROOT / "results/search/pilot5/review_sample.md").write_text("\n".join(out))
