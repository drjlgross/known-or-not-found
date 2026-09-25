"""Re-apply the strict script checks to saved model answers, without calling Paperclip.

Use after a fix to the checks (e.g. gene_names.normalize, 2026-09-25: Greek letters and PDF combining marks).
For each gene: parent set = its ledger rows (by search_id), answers = results/search/<gene>/map_answers.txt (the saved
`results --save` export). Rewrites ledger verdicts, verdicts.csv and summary.json counts via the same functions as a
live run. The previous verdicts.csv is kept as verdicts_pre_recheck.csv.
Usage: python3 src/recheck_verdicts.py <outdir> <genes...>
"""
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search_gene as sg  # noqa: E402

outdir = (sg.ROOT / sys.argv[1]).resolve()
assert sg.ROOT in outdir.parents
rows = list(csv.DictReader(sg.LEDGER.open(), delimiter="\t"))
for gene in sys.argv[2:]:
    gdir = outdir / gene
    summary = json.loads((gdir / "summary.json").read_text())
    if summary.get("status") != "ok":
        print(json.dumps({"gene": gene, "skipped": "search not ok"}))
        continue
    assert summary.get("strict") and summary.get("mode") == "map", gene
    sid = summary["search_id"]
    parent = [(int(r["rank"]), r["paper_id"], r["title"]) for r in rows if r["search_id"] == sid]
    parent.sort()
    assert [r for r, _, _ in parent] == list(range(1, len(parent) + 1)) and len(parent) == summary["parent_n"], gene
    ans = sg.parse_map_export((gdir / "map_answers.txt").read_text())
    stray = set(ans) - {p for _, p, _ in parent}
    assert not stray, (gene, stray)
    before = {k: summary.get(k) for k in ("yes", "yes_before_checks", "downgraded", "paper_errors")}
    shutil.copy(gdir / "verdicts.csv", gdir / "verdicts_pre_recheck.csv")
    sg.apply_checks(ans, gene, summary.get("stimulus_check", False), summary.get("two_quote", False))
    counts = sg.write_verdicts(ans, parent, sid, gdir, "map")
    summary.update(**counts)
    summary.setdefault("rechecks", []).append({"date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                              "reason": "name check: normalize Greek letters and combining marks",
                                              "before": before})
    (gdir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"gene": gene, "yes_before": before["yes"], "yes_after": counts["yes"],
                      "model_yes": counts["yes_before_checks"], "paper_errors": counts["paper_errors"]}))
