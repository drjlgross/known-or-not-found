// Build the hackathon deck: node deck/build_deck.js  ->  deck/known-or-not-found.pptx
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const INK = "1B2A2F", TEAL = "0F766E", MINT = "CCEDE8", RED = "B42318", GREY = "5B6770", WHITE = "FFFFFF";
const HEAD = "Cambria", BODY = "Calibri";

const bins = {
  established: ["Edn1", "Nos2", "Il6", "Il1b", "Il1a", "Saa3", "Cxcl10", "Acod1", "Gbp5", "Il12b", "Serpinb2", "Cd69",
    "Ptgs2", "Serpina3g", "Socs3", "Adamts4", "Ptx3", "Ccl5", "Slamf1", "Ptges", "Il27", "Cxcl9", "Cxcl2", "Cxcl1",
    "Cxcl3", "Ccl17", "Rasgrp1", "Gbp2", "Mmp13", "Ccl4"],
  limited: ["Shisa3", "Tnfsf15", "Steap4", "Ifi205", "Ccl12", "Rsad2", "Serpina3f", "Hdc", "Rnd1", "Tarm1", "Inhba",
    "Bcl2a1a"],
  notfound: ["Lipg", "Itgb8", "Col27a1", "Trim30c", "Tmem200b", "Iigp1", "Gbp6", "Tnfsf4"],
};
const star = new Set(["Acod1", "Adamts4", "Bcl2a1a", "Ccl17", "Ccl5", "Cd69", "Col27a1", "Gbp5", "Ifi205"]);
const disagree = ["Ccl12", "Ccl4", "Gbp2"];

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "known-or-not-found";

// ---- Slide 1: logic flow
let s = pres.addSlide();
s.background = { color: WHITE };
s.addText("known-or-not-found: literature triage for a DE gene list", {
  x: 0.6, y: 0.4, w: 12.1, h: 0.8, fontFace: HEAD, fontSize: 32, bold: true, color: INK, isTextBox: true, margin: 0 });
s.addText("Which induced genes are already established in the literature, and which weren't found?", {
  x: 0.6, y: 1.15, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 16, italic: true, color: GREY, isTextBox: true, margin: 0 });

const steps = [
  ["1", "DE genes", "rnaseq-de (pydeseq2)\ntop 50: padj < 1e-10,\nranked by log2FC"],
  ["2", "Search", "1 query per gene\n\"Gene (name) LPS\nmacrophage\", top 25"],
  ["3", "Ledger first", "all 25 papers logged\nbefore any judging"],
  ["4", "Judge", "own data? this gene?\nLPS / bacteria vs\ncontrol? + quotes"],
  ["5", "Script checks", "quote names the gene\n(no look-alikes) AND\nnames LPS/infection"],
  ["6", "Bin", "≥3 established\n1–2 limited\n0 not found in top 25"],
];
const bw = 1.85, gap = 0.2, y0 = 2.1, x0 = 0.6;
steps.forEach(([n, t, d], i) => {
  const x = x0 + i * (bw + gap);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y0, w: bw, h: 2.9, fill: { color: i === 5 ? TEAL : MINT },
    line: { color: i === 5 ? TEAL : MINT }, rectRadius: 0.12 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.15, y: y0 + 0.15, w: 0.5, h: 0.5, fill: { color: i === 5 ? WHITE : TEAL },
    line: { color: i === 5 ? WHITE : TEAL } });
  s.addText(n, { x: x + 0.15, y: y0 + 0.15, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: BODY,
    fontSize: 16, bold: true, color: i === 5 ? TEAL : WHITE, isTextBox: true, margin: 0 });
  s.addText(t, { x: x + 0.15, y: y0 + 0.8, w: bw - 0.3, h: 0.5, fontFace: HEAD, fontSize: 18, bold: true,
    color: i === 5 ? WHITE : INK, isTextBox: true, margin: 0 });
  s.addText(d, { x: x + 0.15, y: y0 + 1.35, w: bw - 0.3, h: 1.45, fontFace: BODY, fontSize: 13, valign: "top",
    color: i === 5 ? WHITE : INK, isTextBox: true, margin: 0 });
  if (i < 5) s.addText("›", { x: x + bw - 0.02, y: y0 + 1.1, w: gap + 0.04, h: 0.6, align: "center", fontFace: BODY,
    fontSize: 24, bold: true, color: TEAL, isTextBox: true, margin: 0 });
});
s.addText([
  { text: "Every count is derived by script from a per-paper ledger. ", options: { bold: true } },
  { text: "A failed search is an error, never zero. \"Not found\" means not in the top 25 results for this query on this date — never \"novel\"." },
], { x: 0.6, y: 5.35, w: 12.1, h: 0.9, fontFace: BODY, fontSize: 15, color: INK, isTextBox: true, margin: 0 });
s.addText("Blind human grading audits the judge; bins are provisional until it finishes.", {
  x: 0.6, y: 6.3, w: 12.1, h: 0.5, fontFace: BODY, fontSize: 13, italic: true, color: GREY, isTextBox: true, margin: 0 });

// ---- Slide 2: LPS worked example
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Worked example: 50 LPS-induced genes", { x: 0.6, y: 0.35, w: 12.1, h: 0.7, fontFace: HEAD, fontSize: 32,
  bold: true, color: INK, isTextBox: true, margin: 0 });
s.addText("GSE250273 · mouse BMDM · LPS 4 h vs. time-matched control · 3 vs. 3", { x: 0.6, y: 1.0, w: 12.1, h: 0.4,
  fontFace: BODY, fontSize: 15, color: GREY, isTextBox: true, margin: 0 });

const cols = [
  ["30", "established", "≥3 qualifying papers", bins.established, TEAL, WHITE],
  ["12", "limited", "1–2 qualifying papers", bins.limited, MINT, INK],
  ["8", "not found in top 25", "0 qualifying papers", bins.notfound, "E8ECEE", INK],
];
const cw = 3.95, cg = 0.13;
cols.forEach(([num, label, sub, genes, fill, fg], i) => {
  const x = 0.6 + i * (cw + cg);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.6, w: cw, h: 4.75, fill: { color: fill }, line: { color: fill },
    rectRadius: 0.12 });
  s.addText(num, { x: x + 0.25, y: 1.7, w: 1.4, h: 1.0, fontFace: HEAD, fontSize: 54, bold: true, color: fg,
    isTextBox: true, margin: 0 });
  s.addText([{ text: label, options: { bold: true, fontSize: 18, breakLine: true } },
    { text: sub, options: { fontSize: 12 } }],
    { x: x + 1.6, y: 1.85, w: cw - 1.8, h: 0.8, fontFace: BODY, color: fg, valign: "middle", isTextBox: true, margin: 0 });
  const txt = genes.map(g => (star.has(g) ? g + "*" : g)).join("  ·  ");
  s.addText(txt, { x: x + 0.25, y: 2.85, w: cw - 0.5, h: 3.35, fontFace: BODY, fontSize: 17, color: fg, valign: "top",
    isTextBox: true, margin: 0 });
});
s.addText([
  { text: "* ", options: { bold: true } },
  { text: "human graders agreed with the pipeline on every graded paper for that gene (partial blind grading, 30 papers so far). " },
  { text: "Disagreed on ≥1 paper: " + disagree.join(", ") + ". ", options: { bold: true } },
  { text: "Yes-call precision so far ≈ 86% (19/22). Positive controls Nos2, Il6, Il1b, Cxcl10 all land in established." },
], { x: 0.6, y: 6.5, w: 12.1, h: 0.8, fontFace: BODY, fontSize: 12, color: GREY, isTextBox: true, margin: 0 });

// ---- Slide 3: repo link + QR
s = pres.addSlide();
s.background = { color: INK };
s.addText("Look at the repo", { x: 0.6, y: 0.8, w: 7.4, h: 0.9, fontFace: HEAD, fontSize: 40, bold: true, color: WHITE,
  isTextBox: true, margin: 0 });
s.addText("github.com/drjlgross/\nknown-or-not-found", { x: 0.6, y: 2.2, w: 7.4, h: 2.2, fontFace: BODY, fontSize: 40,
  bold: true, color: "7FE0D2", isTextBox: true, margin: 0,
  hyperlink: { url: "https://github.com/drjlgross/known-or-not-found" } });
s.addText("Pipeline, per-paper ledger, chunk reports, blind grading sheet, and a ClawBio skill (literature-triage) with an offline --demo.",
  { x: 0.6, y: 4.7, w: 7.2, h: 1.2, fontFace: BODY, fontSize: 16, color: "D6DEE2", isTextBox: true, margin: 0 });
const qr = fs.readFileSync(path.join(__dirname, "repo_qr.png")).toString("base64");
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.55, y: 1.25, w: 4.2, h: 4.2, fill: { color: WHITE },
  line: { color: WHITE }, rectRadius: 0.12 });
s.addImage({ data: "image/png;base64," + qr, x: 8.75, y: 1.45, w: 3.8, h: 3.8, altText: "QR code linking to the repository" });

pres.writeFile({ fileName: path.join(__dirname, "known-or-not-found.pptx") }).then(f => console.log("wrote", f));
