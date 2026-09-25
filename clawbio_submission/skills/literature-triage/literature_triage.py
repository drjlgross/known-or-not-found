#!/usr/bin/env python3
"""literature-triage: sort a DE gene list into "established", "limited" and "not found in the top N" by
per-gene literature search plus a strict, script-checked relevance judgment.

Every count is derived from a provenance ledger (one row per paper per gene). "Not found" means not found in the
top N results for this query on this date. It never means novel. A failed search is an error row, never zero.

Modes:
  --demo   offline replay of cached Paperclip search + judge outputs for 4 genes (no account, no network)
  default  live: calls the `paperclip` CLI (authenticated account required) for each gene in --input
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
DEMO_DIR = SKILL_DIR / "examples"
SOURCES = "pmc,biorxiv,medrxiv,arxiv"
LEDGER_COLS = ["gene", "query", "search_id", "date", "rank", "paper_id", "title", "verdict", "status"]
DISCLAIMER = ('"Not found" means not found in the top {n} search results for this query on this date. '
              "It does not mean the gene is novel or unstudied.")

QUESTION = (
    "Does this paper report its own experimental data (not background statements or citations of other work) "
    "showing that the expression of the gene {gene} (the gene, its mRNA, or its encoded protein, under any name, "
    "alias, or species ortholog) changes (increases or decreases) in response to LPS or bacterial infection, "
    "compared with unstimulated or uninfected controls? Answer no if the only evidence is: a change caused by some "
    "other stimulus; a result showing no change; a baseline or unstimulated condition; or a statement about other "
    "work. If yes, give evidence: the single sentence reporting the change in this gene; and context: if that "
    "sentence does not itself name both the gene (or its protein) and LPS or the infection, one sentence from "
    "elsewhere in the paper (for example the methods or a figure legend) that names what is missing for the same "
    "experiment, otherwise an empty string. Use empty strings if no.")
SCHEMA = json.dumps({"type": "object", "required": ["answer", "evidence", "context"], "additionalProperties": False,
                     "properties": {"answer": {"enum": ["yes", "no"]}, "evidence": {"type": "string"},
                                    "context": {"type": "string"}}})

# ---------------------------------------------------------------- name and stimulus checks (deterministic)
_GREEK = str.maketrans({"α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "κ": "k", "λ": "l", "θ": "t", "ω": "w",
                        "Α": "A", "Β": "B", "Γ": "G", "Δ": "D", "Κ": "K"})
_GREEK_WORD = re.compile(r"(?<=[0-9\-\s])(alpha|beta|gamma|delta|epsilon|kappa|lambda|theta|omega)(?![A-Za-z])", re.I)
STIMULUS = re.compile(
    r"(?<![A-Za-z0-9])(LPS|lipopolysaccharides?|endotox\w*|lipid A|Kdo2|infect\w*|bacteri\w*|seps\w*|septic\w*|"
    r"CLP|cecal ligation|caecal ligation|E\. ?coli|Escherichia|Salmonella|Listeria|Mycobacteri\w*|tubercul\w*|"
    r"Staphylococc\w*|S\. ?aureus|Streptococc\w*|Pseudomonas|Klebsiella|Porphyromonas|Helicobacter|Citrobacter|"
    r"Yersinia|Francisella|Legionella|Chlamydi\w*|Shigella|Brucella)(?![A-Za-z0-9])", re.I)


def normalize(text: str) -> str:
    """Drop combining marks (PDF debris like "IL-1̠b"); Greek letters -> Latin initial (IL-1β -> IL-1b);
    spelled-out Greek after a digit/hyphen/space -> initial (IL-1beta -> IL-1b)."""
    t = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return _GREEK_WORD.sub(lambda m: m.group(1)[0], t.translate(_GREEK))


def names_in(text: str, names: list[str]) -> list[str]:
    t = normalize(text)
    return [n for n in names
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(normalize(n))}(?![A-Za-z0-9])", t, re.I)]


def stimulus_in(text: str) -> list[str]:
    seen: list[str] = []
    for m in STIMULUS.finditer(text):
        if m.group(0).lower() not in (s.lower() for s in seen):
            seen.append(m.group(0))
    return seen


def apply_checks(ans: dict[str, dict], names: list[str]) -> None:
    """In place: keep model_answer; a yes whose quotes don't name the gene, or don't name LPS/infection, -> no."""
    for a in ans.values():
        a["model_answer"] = a.get("answer", "")
        quoted = a.get("evidence", "") + " " + a.get("context", "")
        a["evidence_names"] = ";".join(names_in(quoted, names))
        a["evidence_stimulus"] = ";".join(stimulus_in(quoted))
        if a.get("answer") == "yes" and not a["evidence_names"]:
            a["answer"], a["downgraded"] = "no", "evidence does not name the gene"
        elif a.get("answer") == "yes" and not a["evidence_stimulus"]:
            a["answer"], a["downgraded"] = "no", "evidence does not name LPS or infection"


# ---------------------------------------------------------------- Paperclip I/O
MAP_BLOCK = re.compile(r"^--- \[(\d+)\] \[(\w+)\] (.*?) ---$", re.M)


def parse_map_export(text: str) -> dict[str, dict]:
    """paper_id -> {status, answer, evidence, context} from a `paperclip results m_... --save` export."""
    out: dict[str, dict] = {}
    blocks = list(MAP_BLOCK.finditer(text))
    for i, b in enumerate(blocks):
        body = text[b.end(): blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]
        m_doc = re.search(r"^doc_id: (\S+)", body, re.M) or re.search(r"/papers/([^/\s]+)/", b.group(3))
        if not m_doc:
            continue
        rec = {"status": b.group(2), "answer": "", "evidence": "", "context": ""}
        if rec["status"] == "success":
            m_json = re.search(r"\{.*\}", body, re.S)
            try:
                obj = json.loads(m_json.group(0)) if m_json else {}
            except json.JSONDecodeError:
                obj = {}
            if obj.get("answer") in ("yes", "no"):
                rec.update(answer=obj["answer"], evidence=obj.get("evidence", ""), context=obj.get("context", ""))
            else:
                rec["status"] = "unparseable"
        out[m_doc.group(1)] = rec
    return out


RANK_LINE = re.compile(r"^  (\d+)\. (.+)$")
ID_LINE = re.compile(r"^\s+(PMC\d+|bio_\w+|med_\w+|arx_\S+) · ")


def parse_search(out: str) -> list[tuple[int, str, str]]:
    entries, cur = [], None
    for line in out.splitlines():
        m = RANK_LINE.match(line)
        if m:
            cur = (int(m.group(1)), m.group(2).strip())
            continue
        m = ID_LINE.match(line)
        if m and cur:
            entries.append((cur[0], m.group(1), cur[1]))
            cur = None
    return entries


def paperclip(args: list[str], log: Path) -> tuple[int, str]:
    p = subprocess.run(["paperclip", *args], capture_output=True, text=True, timeout=1800)
    with log.open("a") as fh:
        fh.write(f"$ paperclip {' '.join(args)}\n# exit {p.returncode}\n{p.stdout}{p.stderr}\n")
    return p.returncode, p.stdout + p.stderr


def live_gene(gene: str, official: str, n: int, gdir: Path) -> dict:
    """Search + judge one gene live. Returns {query, search_id, date, parent, answers} or {error}."""
    query = f"{gene} ({official}) LPS macrophage"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rc, out = paperclip(["search", "-s", SOURCES, "-n", str(n), query], gdir / "search.txt")
    m = re.search(r"\[(s_[0-9a-f]+)\]", out)
    if rc != 0 or not m:
        return {"query": query, "date": date, "search_id": "", "error": f"search exit {rc}"}
    sid, parent = m.group(1), parse_search(out)
    if [r for r, _, _ in parent] != list(range(1, len(parent) + 1)):
        return {"query": query, "date": date, "search_id": sid, "error": "search output did not parse"}
    rc, out = paperclip(["map", "--from", sid, "--limit", str(n), "-j", str(n), "--output-schema", SCHEMA,
                         QUESTION.format(gene=gene)], gdir / "map.txt")
    m = re.search(r"saved to (m_[0-9a-f]+)", out)
    if rc != 0 or not m:
        return {"query": query, "date": date, "search_id": sid, "parent": parent, "error": f"map exit {rc}"}
    paperclip(["results", m.group(1), "--save", str(gdir / "map_answers.txt")], gdir / "map_export.txt")
    return {"query": query, "date": date, "search_id": sid, "parent": parent,
            "answers": parse_map_export((gdir / "map_answers.txt").read_text())}


def demo_gene(gene: str, gdir: Path) -> dict:
    d = DEMO_DIR / "demo_cache" / gene
    meta = json.loads((d / "meta.json").read_text())
    parent = [(int(r["rank"]), r["paper_id"], r["title"])
              for r in csv.DictReader(open(d / "parent.tsv"), delimiter="\t")]
    shutil.copy(d / "map_answers.txt", gdir / "map_answers.txt")
    return {"query": meta["query"], "date": meta["date"], "search_id": meta["search_id"], "parent": parent,
            "answers": parse_map_export((d / "map_answers.txt").read_text())}


# ---------------------------------------------------------------- ledger, counts, bins
def bin_of(count: int | None) -> str:
    if count is None:
        return "search error"
    return "not found in top N" if count == 0 else "limited" if count <= 2 else "established"


def ledger_rows(gene: str, res: dict) -> list[dict]:
    """Parent set first (the full top N), verdicts by script. Failed search -> one error row, never zero papers.
    A paper the judge failed on -> status=error with a blank verdict, never "no"."""
    base = {"gene": gene, "query": res["query"], "search_id": res.get("search_id", ""), "date": res["date"]}
    if "error" in res:
        return [{**base, "rank": "", "paper_id": "", "title": f"ERROR: {res['error']}", "verdict": "",
                 "status": "error"}]
    rows, ans = [], res["answers"]
    stray = set(ans) - {p for _, p, _ in res["parent"]}
    if stray:
        return [{**base, "rank": "", "paper_id": "", "title": f"ERROR: judged IDs outside parent set {sorted(stray)}",
                 "verdict": "", "status": "error"}]
    for rank, pid, title in res["parent"]:
        a = ans.get(pid)
        ok = bool(a) and a["status"] == "success"
        rows.append({**base, "rank": rank, "paper_id": pid, "title": title,
                     "verdict": a["answer"] if ok else "", "status": "ok" if ok else "error"})
    return rows


def run(genes: list[dict], names: dict, n: int, outdir: Path, demo: bool) -> dict:
    per_gene = outdir / "genes"
    per_gene.mkdir(parents=True, exist_ok=True)
    ledger, summary = [], []
    for g in genes:
        gene = g["gene"]
        gdir = per_gene / gene
        gdir.mkdir(exist_ok=True)
        res = demo_gene(gene, gdir) if demo else live_gene(gene, names[f"{gene}__official"], n, gdir)
        if "answers" in res:
            apply_checks(res["answers"], names[gene])
            with (gdir / "verdicts.csv").open("w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["rank", "paper_id", "title", "judge_status", "answer", "model_answer", "evidence",
                            "context", "evidence_names", "evidence_stimulus", "downgraded"])
                for rank, pid, title in res["parent"]:
                    a = res["answers"].get(pid, {"status": "absent"})
                    w.writerow([rank, pid, title, a["status"], a.get("answer", ""), a.get("model_answer", ""),
                                a.get("evidence", ""), a.get("context", ""), a.get("evidence_names", ""),
                                a.get("evidence_stimulus", ""), a.get("downgraded", "")])
        rows = ledger_rows(gene, res)
        ledger += rows
        # counts come from the ledger rows only
        failed = len(rows) == 1 and rows[0]["status"] == "error" and not rows[0]["paper_id"]
        count = None if failed else sum(r["verdict"] == "yes" for r in rows)
        raw = None if failed else sum(a.get("model_answer") == "yes" for a in res["answers"].values())
        summary.append({"gene": gene, "log2FC": g.get("log2FoldChange", ""), "padj": g.get("padj", ""),
                        "qualifying_count": count, "yes_before_checks": raw,
                        "paper_errors": sum(r["status"] == "error" for r in rows) if not failed else None,
                        "bin": bin_of(count)})
    return {"ledger": ledger, "genes": summary}


def write_outputs(result: dict, outdir: Path, n: int, argv: list[str], demo: bool) -> None:
    (outdir / "tables").mkdir(exist_ok=True)
    (outdir / "reproducibility").mkdir(exist_ok=True)
    with (outdir / "tables" / "paper_ledger.tsv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(result["ledger"])
    with (outdir / "tables" / "gene_bins.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(result["genes"][0]))
        w.writeheader()
        w.writerows(result["genes"])
    counts: dict[str, int] = {}
    for g in result["genes"]:
        counts[g["bin"]] = counts.get(g["bin"], 0) + 1
    disclaimer = DISCLAIMER.format(n=n)
    lines = ["# Literature triage report", "",
             f"**Mode:** {'demo (offline replay of cached Paperclip outputs, 2026-09-25)' if demo else 'live'}  ",
             f"**Genes:** {len(result['genes'])} · **Papers per gene (N):** {n} · "
             f"**Sources:** {SOURCES}", "",
             f"> {disclaimer}", "",
             "> **Provisional.** Bins come from model judgments plus deterministic name/stimulus checks. "
             "Hand grading of a sample found about 86% precision on yes calls (n = 22), and it is not finished. "
             "Treat bins as triage, not ground truth.", "",
             "## Bin summary", ""]
    lines += [f"- **{b}:** {counts.get(b, 0)}" for b in ("established", "limited", "not found in top N", "search error")]
    lines += ["", "## Per gene", "",
              "| gene | log2FC | qualifying count | yes before checks | paper errors | bin |", "|---|---|---|---|---|---|"]
    for g in result["genes"]:
        lfc = f"{float(g['log2FC']):.2f}" if g["log2FC"] != "" else ""
        lines.append(f"| {g['gene']} | {lfc} | {g['qualifying_count']} | {g['yes_before_checks']} | "
                     f"{g['paper_errors']} | {g['bin']} |")
    lines += ["", "Counts are derived from `tables/paper_ledger.tsv` by script. Per-gene quotes and check results "
              "are in `genes/<gene>/verdicts.csv`.", ""]
    (outdir / "report.md").write_text("\n".join(lines))
    (outdir / "result.json").write_text(json.dumps(
        {"skill": "literature-triage", "version": "0.1.0", "mode": "demo" if demo else "live", "n": n,
         "disclaimer": disclaimer, "bin_counts": counts, "genes": result["genes"]}, indent=2))
    (outdir / "reproducibility" / "commands.sh").write_text(
        "#!/usr/bin/env bash\npython3 skills/literature-triage/literature_triage.py " + " ".join(argv) + "\n")
    (outdir / "reproducibility" / "question.txt").write_text(QUESTION + "\n\nSCHEMA: " + SCHEMA + "\n")


def load_genes(path: Path, k: int) -> list[dict]:
    rows = list(csv.DictReader(open(path)))
    if not rows or "gene" not in rows[0]:
        sys.exit(f"error: {path} needs a 'gene' column (plus optional log2FoldChange, padj)")
    return rows[:k]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, help="CSV of genes (column 'gene'; optional log2FoldChange, padj), ranked")
    ap.add_argument("--gene-names", type=Path, help="JSON: gene -> list of names/aliases, and '<gene>__official'")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--top-k", type=int, default=50)
    ap.add_argument("-n", type=int, default=25, help="papers per gene (search depth)")
    ap.add_argument("--demo", action="store_true", help="offline replay of cached outputs for 4 genes")
    a = ap.parse_args(argv)
    if a.output.exists() and any(a.output.iterdir()):
        sys.exit(f"error: output directory {a.output} is not empty")
    if a.demo:
        genes = load_genes(DEMO_DIR / "demo_de_results.csv", a.top_k)
        names = json.loads((DEMO_DIR / "demo_gene_names.json").read_text())
        n = 25
    else:
        if not (a.input and a.gene_names):
            sys.exit("error: live mode needs --input and --gene-names (or use --demo)")
        if shutil.which("paperclip") is None:
            sys.exit("error: live mode needs the authenticated `paperclip` CLI on PATH (or use --demo)")
        genes, names, n = load_genes(a.input, a.top_k), json.loads(a.gene_names.read_text()), a.n
        missing = [g["gene"] for g in genes if g["gene"] not in names or f"{g['gene']}__official" not in names]
        if missing:
            sys.exit(f"error: --gene-names lacks names for: {missing}")
    a.output.mkdir(parents=True, exist_ok=True)
    result = run(genes, names, n, a.output, a.demo)
    write_outputs(result, a.output, n, argv, a.demo)
    print(json.dumps({"output": str(a.output), "bin_counts": json.loads((a.output / "result.json").read_text())
                      ["bin_counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
