import csv
import importlib.util
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("literature_triage", SKILL / "literature_triage.py")
lt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lt)


def test_demo_reproduces_cached_counts(tmp_path):
    out = tmp_path / "demo"
    assert lt.main(["--demo", "--output", str(out)]) == 0
    bins = {r["gene"]: r for r in csv.DictReader(open(out / "tables" / "gene_bins.csv"))}
    for gene in ("Nos2", "Hdc", "Tarm1", "Lipg"):
        meta = json.loads((SKILL / "examples" / "demo_cache" / gene / "meta.json").read_text())
        assert int(bins[gene]["qualifying_count"]) == meta["expected_yes"]
    assert bins["Lipg"]["bin"] == "not found in top N"
    assert "does not mean the gene is novel" in (out / "report.md").read_text()


def test_counts_come_from_ledger(tmp_path):
    out = tmp_path / "demo"
    lt.main(["--demo", "--output", str(out)])
    ledger = list(csv.DictReader(open(out / "tables" / "paper_ledger.tsv"), delimiter="\t"))
    assert len(ledger) == 4 * 25
    for r in csv.DictReader(open(out / "tables" / "gene_bins.csv")):
        assert int(r["qualifying_count"]) == sum(x["gene"] == r["gene"] and x["verdict"] == "yes" for x in ledger)


def test_failed_search_is_error_not_zero():
    rows = lt.ledger_rows("Foo1", {"query": "q", "date": "d", "search_id": "", "error": "search exit 1"})
    assert len(rows) == 1 and rows[0]["status"] == "error" and rows[0]["verdict"] == ""
    assert lt.bin_of(None) == "search error"


def test_failed_paper_is_error_not_no():
    res = {"query": "q", "date": "d", "search_id": "s_1", "parent": [(1, "PMC1", "t")],
           "answers": {"PMC1": {"status": "timeout", "answer": ""}}}
    (row,) = lt.ledger_rows("Foo1", res)
    assert row["status"] == "error" and row["verdict"] == ""


def test_greek_letters_and_pdf_marks_match():
    names = ["Il1b", "IL-1B", "IL-1beta"]
    for text in ("IL-1β mRNA rose", "Il-1β secretion", "IL-1̠b levels"):
        assert lt.names_in(text, names), text


def test_look_alikes_rejected():
    assert not lt.names_in("LPS increased HDAC3 expression", ["Hdc", "histidine decarboxylase", "HDC"])
    assert not lt.names_in("LPS induced CXCL12", ["Ccl12", "CCL12", "MCP-5"])


def test_checks_downgrade_and_keep_model_answer():
    ans = {"a": {"answer": "yes", "evidence": "HDAC2 rose after LPS", "context": ""},
           "b": {"answer": "yes", "evidence": "HDC protein rose with norepinephrine", "context": ""},
           "c": {"answer": "yes", "evidence": "Hdc mRNA rose 6-fold after LPS", "context": ""}}
    lt.apply_checks(ans, ["Hdc", "HDC", "histidine decarboxylase"])
    assert [ans[k]["answer"] for k in "abc"] == ["no", "no", "yes"]
    assert all(ans[k]["model_answer"] == "yes" for k in "abc")
