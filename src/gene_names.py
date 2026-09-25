"""Official names and synonyms for mouse gene symbols, from MGI's MRK_List2.rpt (data/raw/, sha256 in
data/raw/download_checksums.sha256). Used for (a) the symbol+name search query, (b) the corpus-count boolean
query, and (c) the strict judge's check that the evidence quote names the gene.
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

MGI = Path(__file__).resolve().parent.parent / "data" / "raw" / "MRK_List2.rpt"
# HGNC complete set (sha256 in data/raw/download_checksums.sha256): human ortholog names, joined on MGI accession ID.
HGNC = MGI.parent / "hgnc_complete_set.txt"
# Synonyms kept for queries/matching: >= 4 characters, not RIKEN clone IDs or Gm placeholders
# (short synonyms like "EL", "Tea", "DIF" match unrelated text).
_JUNK = re.compile(r"^(?:\w+Rik|Gm\d+)$")
# HGNC clone/placeholder aliases (RP1-93H18.5, OTTHUMP..., dJ93H18.5, KIAA..., FLJ..., C6orf187-style kept: real prior symbols)
_HJUNK = re.compile(r"^(?:RP\d+-|OTTHUMP|dJ\d|CT[ABCD]-|KIAA\d|FLJ\d|DKFZ|MGC\d|LOC\d)", re.I)


@lru_cache(maxsize=1)
def _table() -> pd.DataFrame:
    m = pd.read_csv(MGI, sep="\t", dtype=str).fillna("")
    m = m[(m["Status"] == "O") & (m["Marker Type"] == "Gene")]
    assert m["Marker Symbol"].is_unique, "MGI gene symbols must be unique among current genes"
    return m.set_index("Marker Symbol")


def official_name(symbol: str) -> str:
    return _table().loc[symbol, "Marker Name"]


def synonyms(symbol: str) -> list[str]:
    raw = _table().loc[symbol, "Marker Synonyms (pipe-separated)"]
    return [s for s in raw.split("|") if len(s) >= 4 and not _JUNK.match(s)]


def all_names(symbol: str) -> list[str]:
    """Symbol, official name, then kept synonyms; de-duplicated case-insensitively, order preserved."""
    seen, out = set(), []
    for n in [symbol, official_name(symbol), *synonyms(symbol)]:
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out


@lru_cache(maxsize=1)
def _hgnc() -> dict[str, list[str]]:
    """MGI accession ID -> human symbol, name, alias/previous symbols and alias names (>= 4 chars, junk removed).
    When one mouse gene maps to several human genes (Hcar2 -> HCAR2, HCAR3), keep only the one whose symbol matches
    the mouse symbol, so paralog names don't count as this gene."""
    h = pd.read_csv(HGNC, sep="\t", dtype=str).fillna("")
    rows: dict[str, list] = {}
    for _, r in h.iterrows():
        for mgi in filter(None, r["mgd_id"].split("|")):
            rows.setdefault(mgi, []).append(r)
    mouse = {mgi: sym for sym, mgi in _table()["MGI Accession ID"].items()}
    out: dict[str, list[str]] = {}
    for mgi, rs in rows.items():
        exact = [r for r in rs if r["symbol"].upper() == mouse.get(mgi, "").upper()]
        for r in (exact if len(rs) > 1 and exact else rs):
            names = [r["symbol"], r["name"], *r["alias_symbol"].split("|"), *r["prev_symbol"].split("|"),
                     *r["alias_name"].split("|")]
            out.setdefault(mgi, []).extend(n for n in names if len(n) >= 4 and not _HJUNK.match(n))
    return out


def human_names(symbol: str) -> list[str]:
    return _hgnc().get(_table().loc[symbol, "MGI Accession ID"], [])


_GREEK = str.maketrans({"α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "κ": "k", "λ": "l", "θ": "t", "ω": "w",
                        "Α": "A", "Β": "B", "Γ": "G", "Δ": "D", "Κ": "K"})
_GREEK_WORD = re.compile(r"(?<=[0-9\-\s])(alpha|beta|gamma|delta|epsilon|kappa|lambda|theta|omega)(?![A-Za-z])", re.I)


def normalize(text: str) -> str:
    """For name matching only: drop combining marks (PDF-extraction debris such as "IL-1̠b"), map Greek letters to
    Latin initials (IL-1β -> IL-1b), and spelled-out Greek after a digit, hyphen or space to its initial
    (IL-1beta, interleukin 1 beta -> IL-1b, interleukin 1 b)."""
    t = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    t = t.translate(_GREEK)
    return _GREEK_WORD.sub(lambda m: m.group(1)[0], t)


def names_in(text: str, symbol: str, human: bool = False) -> list[str]:
    """Which of the gene's names occur in text (case-insensitive, word-bounded, after normalize() on both sides).
    human=True adds HGNC ortholog names."""
    hits, t = [], normalize(text)
    for n in dict.fromkeys(all_names(symbol) + (human_names(symbol) if human else [])):
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(normalize(n))}(?![A-Za-z0-9])", t, re.I):
            hits.append(n)
    return hits


# Stimulus terms for the Round 4 check that the evidence quote names LPS or a bacterial infection.
STIMULUS = re.compile(
    r"(?<![A-Za-z0-9])(LPS|lipopolysaccharides?|endotox\w*|lipid A|Kdo2|infect\w*|bacteri\w*|seps\w*|septic\w*|"
    r"CLP|cecal ligation|caecal ligation|E\. ?coli|Escherichia|Salmonella|Listeria|Mycobacteri\w*|tubercul\w*|"
    r"Staphylococc\w*|S\. ?aureus|Streptococc\w*|Pseudomonas|Klebsiella|Porphyromonas|Helicobacter|Citrobacter|"
    r"Yersinia|Francisella|Legionella|Chlamydi\w*|Shigella|Brucella)(?![A-Za-z0-9])", re.I)


def stimulus_in(text: str) -> list[str]:
    """Distinct LPS/infection terms in text, in order of first occurrence."""
    seen = []
    for m in STIMULUS.finditer(text):
        if m.group(0).lower() not in (x.lower() for x in seen):
            seen.append(m.group(0))
    return seen
