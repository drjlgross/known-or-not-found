"""Per-gene Paperclip search + relevance judgment, recorded in data/paper_ledger.tsv.

Procedure (CLAUDE.md, Chunk 3), per gene:
  1. search -s pmc,biorxiv,medrxiv,arxiv -n N "<gene> LPS macrophage"   (N capped on the search itself)
  2. parse the ranked parent set from search stdout; also export it with `results --save`
  3. write the parent set to the ledger with verdict=pending, BEFORE judging relevance
  4. judge relevance, by one of two mechanics:
       map    (default) `map --from <sid> --limit N` with a strict {"answer": yes|no, "evidence"} schema;
              one `--resume --retry-failed` pass; a paper that still fails gets status=error, never "no"
       filter `filter --from <sid>` (overwrites the set in place); yes = survived, no = parent minus survivors
  5. verdicts are written to the ledger by this script, from the saved CLI output
A failed search writes one row with status=error; it is never recorded as zero papers.

Raw CLI output for every step goes to <outdir>/<gene>/. Run:
  .venv/bin/python src/search_gene.py --outdir results/search/pilot Tnf Lipg
"""
import argparse
import csv
import fcntl
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import gene_names

ROOT = Path(__file__).resolve().parent.parent
PC = str(ROOT / "src" / "pc.sh")
LEDGER = ROOT / "data" / "paper_ledger.tsv"
COLUMNS = ["gene", "query", "search_id", "date", "rank", "paper_id", "title", "verdict", "status"]
SOURCES = "pmc,biorxiv,medrxiv,arxiv"
QUERY = "{gene} LPS macrophage"
QUERY_NAMED = "{gene} ({name}) LPS macrophage"
QUESTION = ("Does this paper describe the expression of the gene {gene} (the gene, its mRNA, or its encoded "
            "protein, under any name, alias, or species ortholog) changing in response to LPS or bacterial "
            "infection? Answer yes or no, and quote the supporting sentence from the paper as evidence "
            "(empty string if no).")
QUESTION_STRICT = ("Does this paper report its own experimental data (not background statements or citations of "
                   "other work) showing that the expression of the gene {gene} (the gene, its mRNA, or its encoded "
                   "protein, under any name, alias, or species ortholog) changes in response to LPS or bacterial "
                   "infection? Answer yes or no. If yes, quote the sentence reporting that result; it must name the "
                   "gene or its protein. Use an empty string if no.")
# Round 4: the quote itself must show the change AND name LPS/infection as its cause (hand review found yeses
# whose quote was a baseline condition, a no-change result, a background statement, or another stimulus).
QUESTION_STIM = ("Does this paper report its own experimental data (not background statements or citations of "
                 "other work) showing that the expression of the gene {gene} (the gene, its mRNA, or its encoded "
                 "protein, under any name, alias, or species ortholog) changes (increases or decreases) in response "
                 "to LPS or bacterial infection, compared with unstimulated or uninfected controls? Answer no if the "
                 "only evidence is: a change caused by some other stimulus; a result showing no change; a baseline "
                 "or unstimulated condition; or a statement about other work. If yes, quote the single sentence that "
                 "reports that result; it must name the gene or its protein, name LPS or the infection, and state "
                 "the change. Use an empty string if no.")
# Round 5: same question, but evidence may span two passages (papers often name the stimulus in the methods or a
# figure legend and report the gene's change elsewhere). The name and stimulus checks run on both quotes together.
QUESTION_TWO = QUESTION_STIM.split(" If yes, quote")[0] + (
    " If yes, give evidence: the single sentence reporting the change in this gene; and context: if that sentence does "
    "not itself name both the gene (or its protein) and LPS or the infection, one sentence from elsewhere in the paper "
    "(for example the methods or a figure legend) that names what is missing for the same experiment, otherwise an "
    "empty string. Use empty strings if no.")
FILTER_Q = "Does this paper describe the expression of the gene {gene} changing in response to LPS or bacterial infection?"
SCHEMA = json.dumps({"type": "object", "required": ["answer", "evidence"], "additionalProperties": False,
                     "properties": {"answer": {"enum": ["yes", "no"]}, "evidence": {"type": "string"}}})

SCHEMA_TWO = json.dumps({"type": "object", "required": ["answer", "evidence", "context"], "additionalProperties": False,
                         "properties": {"answer": {"enum": ["yes", "no"]}, "evidence": {"type": "string"},
                                        "context": {"type": "string"}}})

RANK_LINE = re.compile(r"^  (\d+)\. (.+)$")
ID_LINE = re.compile(r"^\s+(PMC\d+|bio_\w+|med_\w+|arx_\S+) · ")
MAP_BLOCK = re.compile(r"^--- \[(\d+)\] \[(\w+)\] (.*?) ---$", re.M)


def run(args: list[str], log: Path, timeout: int = 1800) -> tuple[int, str]:
    p = subprocess.run([PC, *args], capture_output=True, text=True, timeout=timeout)
    out = p.stdout + p.stderr
    with log.open("a") as fh:
        fh.write(f"$ src/pc.sh {' '.join(args)}\n# exit {p.returncode}\n{out}\n")
    return p.returncode, out


@contextmanager
def ledger_rows():
    """Locked read-modify-write of the ledger (genes may run concurrently)."""
    lock = LEDGER.with_suffix(".lock")
    with lock.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        rows = list(csv.DictReader(LEDGER.open(), delimiter="\t")) if LEDGER.exists() else []
        yield rows
        with LEDGER.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)


def parse_entries(out: str) -> list[tuple[int, str, str]]:
    """(rank, paper_id, title) per result: a "  N. title" line, then (after an optional author line)
    the first "   <ID> · source · date" line before the next rank line."""
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


def parse_map_export(text: str) -> dict[str, dict]:
    """paper_id -> {"status", "answer", "evidence"} from `results m_... --save` output."""
    out = {}
    blocks = list(MAP_BLOCK.finditer(text))
    for i, b in enumerate(blocks):
        body = text[b.end(): blocks[i + 1].start() if i + 1 < len(blocks) else len(text)]
        status = b.group(2)
        m_doc = re.search(r"^doc_id: (\S+)", body, re.M) or re.search(r"/papers/([^/\s]+)/", b.group(3))
        if not m_doc:
            continue
        rec = {"status": status, "answer": "", "evidence": "", "context": ""}
        if status == "success":
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


def judge_map(gene: str, sid: str, n: int, gdir: Path, question: str, schema: str = SCHEMA) -> tuple[dict[str, dict], str]:
    rc, out = run(["map", "--from", sid, "--limit", str(n), "-j", str(n), "--output-schema", schema, question],
                  gdir / "map.txt")
    m_id = re.search(r"saved to (m_[0-9a-f]+)", out)
    if rc != 0 or not m_id:
        raise RuntimeError(f"map exit {rc}; no map id")
    mid = m_id.group(1)
    run(["results", mid, "--save", str(gdir / "map_answers.txt")], gdir / "map_export.txt")
    ans = parse_map_export((gdir / "map_answers.txt").read_text())
    if any(v["status"] != "success" for v in ans.values()):
        run(["map", "--resume", mid, "--retry-failed"], gdir / "map.txt")
        run(["results", mid, "--save", str(gdir / "map_answers.txt")], gdir / "map_export.txt")
        ans = parse_map_export((gdir / "map_answers.txt").read_text())
    return ans, mid


def judge_filter(sid: str, gdir: Path, question: str) -> tuple[dict[str, dict], str]:
    rc, fout = run(["filter", "--from", sid, question], gdir / "filter.txt")
    if rc != 0 or "Filtered:" not in fout:
        raise RuntimeError(f"filter exit {rc}")
    # The in-place update can lag: re-read until the listing's header shows the filter query.
    for _ in range(6):
        rc, lout = run(["results", sid], gdir / "filtered.txt")
        # header is "Query: filter --from <sid> '<q>'" (0.7.52) or "Query: filter '<q>' --from <sid>" (0.7.89)
        hdr = re.search(r"^\s*Query: (.*)$", lout, re.M)
        if hdr and hdr.group(1).startswith("filter") and re.search(rf"--from {sid}\b", hdr.group(1)):
            break
        time.sleep(2)
    else:
        raise RuntimeError("results listing never reflected the filter (stale pre-filter set)")
    kept = {pid for _, pid, _ in parse_entries(lout)}
    m_kept = re.search(r"→ (\d+) papers after filtering", fout)
    if m_kept and int(m_kept.group(1)) != len(kept):
        raise RuntimeError(f"listed {len(kept)} survivors, filter reported {m_kept.group(1)}")
    return {pid: {"status": "success", "answer": "yes", "evidence": ""} for pid in kept}, sid


def corpus_count(gene: str, gdir: Path) -> dict:
    """Papers whose full text matches (any gene name) AND (LPS OR lipopolysaccharide) AND macrophage.
    Paperclip returns at most 500, so the count is exact below 500 and reported as ">=500" at the cap."""
    names = " OR ".join('"' + n.replace('"', "") + '"' for n in gene_names.all_names(gene))
    expr = f'({names}) AND ("LPS" OR "lipopolysaccharide") AND "macrophage"'
    rc, out = run(["search", "-s", SOURCES, "--bool", "--ranking", "bm25", "--full-text", "-n", "500", expr],
                  gdir / "corpus_count.txt")
    m = re.search(r"Found (\d+) papers", out)
    if rc != 0 or not m:
        return {"corpus_count": "", "corpus_count_status": "error", "corpus_expr": expr}
    k = int(m.group(1))
    capped = bool(re.search(r"of 500 requested", out)) and k >= 450
    return {"corpus_count": k, "corpus_count_capped": capped, "corpus_count_status": "ok", "corpus_expr": expr}


def apply_checks(ans: dict[str, dict], gene: str, stim: bool, two: bool) -> None:
    """Strict-mode script checks, in place. The model's own answer is kept as model_answer; a yes whose quotes
    (evidence + context) don't name the gene, or (stim) don't name LPS or an infection, becomes no."""
    for a in ans.values():
        a["model_answer"] = a.get("answer", "")
        a.pop("downgraded", None)
        quoted = a.get("evidence", "") + " " + a.get("context", "")
        a["evidence_names"] = ";".join(gene_names.names_in(quoted, gene, human=two))
        if a.get("answer") == "yes" and not a["evidence_names"]:
            a["answer"], a["downgraded"] = "no", "yes->no: evidence does not name the gene"
        if stim:
            a["evidence_stimulus"] = ";".join(gene_names.stimulus_in(quoted))
            if a.get("answer") == "yes" and not a["evidence_stimulus"]:
                a["answer"], a["downgraded"] = "no", "yes->no: evidence does not name LPS or infection"


def write_verdicts(ans: dict[str, dict], parent: list[tuple[int, str, str]], sid: str, gdir: Path,
                   mode: str) -> dict:
    """Write ledger verdicts for search sid and gdir/verdicts.csv; return the per-gene counts for summary.json.
    filter: absent = no. map: absent or failed = error (never "no")."""
    with ledger_rows() as rows:
        for r in rows:
            if r["search_id"] != sid:
                continue
            a = ans.get(r["paper_id"])
            if mode == "filter":
                r["verdict"] = "yes" if a else "no"
            elif a and a["status"] == "success":
                r["verdict"], r["status"] = a["answer"], "ok"
            else:
                r["verdict"], r["status"] = "", "error"
    with (gdir / "verdicts.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "paper_id", "title", "judge_status", "answer", "model_answer", "evidence", "context",
                    "evidence_names", "evidence_stimulus", "downgraded"])
        for rank, pid, title in parent:
            a = ans.get(pid, {"status": "absent" if mode == "map" else "filtered_out", "answer": "", "evidence": ""})
            w.writerow([rank, pid, title, a["status"], a["answer"] or ("no" if mode == "filter" else ""),
                        a.get("model_answer", a["answer"]), a["evidence"], a.get("context", ""),
                        a.get("evidence_names", ""), a.get("evidence_stimulus", ""), a.get("downgraded", "")])
    parent_ids = [pid for _, pid, _ in parent]
    n_yes = sum(1 for p in parent_ids if ans.get(p, {}).get("answer") == "yes")
    n_err = 0 if mode == "filter" else sum(1 for p in parent_ids if ans.get(p, {}).get("status") != "success")
    # yes_before_checks: the model's own yes count, before the name/stimulus downgrades (sensitivity column only)
    n_raw = sum(1 for p in parent_ids if ans.get(p, {}).get("model_answer", ans.get(p, {}).get("answer")) == "yes")
    return dict(parent_n=len(parent), yes=n_yes, yes_before_checks=n_raw,
                downgraded=sum(1 for p in parent_ids if ans.get(p, {}).get("downgraded")),
                no=len(parent) - n_yes - n_err, paper_errors=n_err)


def process(gene: str, n: int, outdir: Path, mode: str, question_tpl: str, also: list[str] | None = None,
            named_query: bool = False, strict: bool = False, count: bool = False, stim: bool = False,
            two: bool = False) -> dict:
    gdir = outdir / gene
    gdir.mkdir(parents=True, exist_ok=True)
    try:
        query = (QUERY_NAMED.format(gene=gene, name=gene_names.official_name(gene)) if named_query
                 else QUERY.format(gene=gene))
    except KeyError:  # symbol not a current MGI gene: record, don't crash the batch
        query = QUERY.format(gene=gene)
        with ledger_rows() as rows:
            rows.append({"gene": gene, "query": query, "search_id": "", "date": "", "rank": "", "paper_id": "",
                         "title": "ERROR at names: symbol not found among current MGI genes", "verdict": "",
                         "status": "error"})
        return {"gene": gene, "status": "error", "stage": "names", "detail": "symbol not in MGI"}
    question = question_tpl.format(gene=gene)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    t0 = time.monotonic()
    also = also or []
    summary = {"gene": gene, "query": query, "also": also, "mode": mode, "strict": strict, "stimulus_check": stim, "two_quote": two,
               "question": question,
               "date": date, "n": n}
    if count:
        summary.update(corpus_count(gene, gdir))

    def error(stage: str, detail: str, sid: str = "") -> dict:
        with ledger_rows() as rows:
            rows[:] = [r for r in rows if not (sid and r["search_id"] == sid)]
            rows.append({"gene": gene, "query": query, "search_id": sid, "date": date, "rank": "", "paper_id": "",
                         "title": f"ERROR at {stage}: {detail}"[:300], "verdict": "", "status": "error"})
        summary.update(status="error", stage=stage, search_id=sid, detail=detail,
                       seconds_total=round(time.monotonic() - t0, 1))
        (gdir / "summary.json").write_text(json.dumps(summary, indent=2))
        return summary

    # 1-2. search; parse the ranked parent set
    try:
        also_args = [x for phr in also for x in ("--also", phr)]
        rc, out = run(["search", "-s", SOURCES, "-n", str(n), *also_args, query], gdir / "search.txt")
    except subprocess.TimeoutExpired:
        return error("search", "timeout")
    m_id, m_found = re.search(r"\[(s_[0-9a-f]+)\]", out), re.search(r"Found (\d+) papers", out)
    if rc != 0 or not m_id:
        return error("search", f"exit {rc}; no result id")
    sid = m_id.group(1)
    parent = parse_entries(out)
    found = int(m_found.group(1)) if m_found else -1
    if len(parent) != found or [r for r, _, _ in parent] != list(range(1, found + 1)):
        return error("search-parse", f"parsed {len(parent)} entries, CLI reported {found}", sid)
    run(["results", sid, "--save", str(gdir / "parent.csv")], gdir / "parent_export.txt")
    t_search = time.monotonic() - t0

    # 3. parent set -> ledger before judging
    with ledger_rows() as rows:
        rows[:] = [r for r in rows if r["search_id"] != sid]
        rows += [{"gene": gene, "query": query, "search_id": sid, "date": date, "rank": rank, "paper_id": pid,
                  "title": title, "verdict": "pending", "status": "ok"} for rank, pid, title in parent]

    # 4. judge
    t1 = time.monotonic()
    try:
        if mode == "map":
            ans, judge_id = judge_map(gene, sid, n, gdir, question, SCHEMA_TWO if two else SCHEMA)
        else:
            ans, judge_id = judge_filter(sid, gdir, question)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        return error(mode, str(exc), sid)
    if strict:
        apply_checks(ans, gene, stim, two)
    parent_ids = [pid for _, pid, _ in parent]
    stray = set(ans) - set(parent_ids)
    if stray:
        return error(f"{mode}-subset", f"judged IDs not in parent set: {sorted(stray)}", sid)
    t_judge = time.monotonic() - t1

    # 5. verdicts by script. filter: absent = no. map: absent or failed = error (never "no").
    counts = write_verdicts(ans, parent, sid, gdir, mode)
    summary.update(status="ok", search_id=sid, judge_id=judge_id, **counts, seconds_search=round(t_search, 1),
                   seconds_judge=round(t_judge, 1), seconds_total=round(time.monotonic() - t0, 1))
    (gdir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    global LEDGER
    ap = argparse.ArgumentParser()
    ap.add_argument("genes", nargs="+")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("-n", type=int, default=25)
    ap.add_argument("--mode", choices=["map", "filter"], default="map")
    ap.add_argument("--question", help="question template with {gene} (default depends on --mode)")
    ap.add_argument("--ledger", default=str(LEDGER), help="ledger path (scratch ledgers for wording tests)")
    ap.add_argument("--workers", type=int, default=1, help="genes processed concurrently")
    ap.add_argument("--also", action="append", default=[], help="extra search phrasing (verbatim; testing only)")
    ap.add_argument("--named-query", action="store_true", help='query "<Symbol> (<MGI official name>) LPS macrophage"')
    ap.add_argument("--strict", action="store_true", help="own-data question + evidence must name the gene (MGI names)")
    ap.add_argument("--stimulus-check", action="store_true",
                    help="with --strict: Round 4 question + evidence must also name LPS or infection")
    ap.add_argument("--two-quote", action="store_true",
                    help="with --strict: Round 5 evidence+context quotes, stimulus check, HGNC human aliases in the name check")
    ap.add_argument("--corpus-count", action="store_true", help="also record the boolean full-text corpus count")
    a = ap.parse_args()
    LEDGER = (ROOT / a.ledger).resolve()
    outdir = (ROOT / a.outdir).resolve()
    for p in (LEDGER, outdir):
        assert ROOT in p.parents, f"{p} must stay inside the project"
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if a.mode == "filter":
        default_q = FILTER_Q
    elif a.strict:
        default_q = QUESTION_TWO if a.two_quote else QUESTION_STIM if a.stimulus_check else QUESTION_STRICT
    else:
        default_q = QUESTION
    question = a.question or default_q
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for s in ex.map(lambda g: process(g, a.n, outdir, a.mode, question, a.also, a.named_query, a.strict, a.corpus_count,
                                        a.strict and (a.stimulus_check or a.two_quote), a.strict and a.two_quote),
                     a.genes):
            print(json.dumps({k: s.get(k) for k in ("gene", "status", "search_id", "judge_id", "parent_n", "yes",
                                                    "no", "downgraded", "paper_errors", "corpus_count",
                                                    "seconds_total", "stage", "detail")}),
                  flush=True)
    print(json.dumps({"wall_seconds": round(time.monotonic() - t0, 1), "genes": len(a.genes), "workers": a.workers}))


if __name__ == "__main__":
    main()
