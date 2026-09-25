# Chunk 3 hand-review sample (Round 4, canonical ledger)

Mark each row right/wrong. "yes" = the paper's own data show the gene's expression changing with LPS or bacterial infection.

## Tnf (search s_18080549, query `Tnf (tumor necrosis factor) LPS macrophage`)

| rank | paper | title | ledger verdict | model said | evidence quote | gene / stimulus terms found | downgrade | your call |
|---|---|---|---|---|---|---|---|---|
| 6 | PMC2190998 | Extinction of the tumor necrosis factor locus, and of genes encoding the lipopol | **yes** | yes | Both LPS and cycloheximide readily induced TNF gene expression in RAW 264.7 cells (Fig. 2). | Tnf / LPS | none | |
| 8 | bio_206e5a356c66 | Mathematical modelling of activation-induced heterogeneity reveals cell state tr | **no** | yes | Notably, the percentage of TNF-positive BMDMs peaked at 4h post stimulation, demonstrating a faster TNF response in BMDMs in comparison to RAW264.7 cells. | Tnf / - | yes->no: evidence does not name LPS or infection | |
| 14 | PMC7018708 | Macrophages employ quorum licensing to regulate collective activation | **yes** | yes | Pretreatment of cells with IL-10, prior to treatment with LPS, diminished the average intracellular TNF protein expression measured at 3 h post-stimulation (hps), although TNF distributions across IL-10 doses were broad and overlapping (Fig. 1b, Supplementary Fig. 1a). | Tnf / LPS | none | |
| 15 | PMC9411976 | Mathematical modelling of activation-induced heterogeneity in TNF, IL6, NOS2, an | **no** | yes | Notably, the percentage of TNF-positive BMDMs peaked at 4h post stimulation, demonstrating a faster TNF response in BMDMs in comparison to RAW264.7 cells. | Tnf / - | yes->no: evidence does not name LPS or infection | |
| 24 | bio_1ab02dae6d41 | The use of Ipratropium and Tiotropium as novel agents to reduce inflammation in  | **yes** | yes | As shown in figure 3.6, a substantial increase in the TNF- ̕α cytokine concentration was observed in LPS treated cells. | Tnf / LPS | none | |

## Slc7a2 (search s_dbc77b76, query `Slc7a2 (solute carrier family 7 (cationic amino acid transporter, y+ system), member 2) LPS macrophage`)

| rank | paper | title | ledger verdict | model said | evidence quote | gene / stimulus terms found | downgrade | your call |
|---|---|---|---|---|---|---|---|---|
| 1 | PMC6245571 | Species-Specific Transcriptional Regulation of Genes Involved in Nitric Oxide Pr | **yes** | yes | In rats, as in mice (19), LPS greatly increased (18-fold) expression of the cationic amino acid transporter, Slc7a2, whereas goats were the only large animal species in which SLC7A2 mRNA was detectable (TPM 6) and regulated to any degree by LPS, with an induced level (TPM≈16) still lower than the ba | Slc7a2 / LPS | none | |
| 4 | PMC6411972 | Characterisation of genes differentially expressed in macrophages by virulent an | **yes** | yes | The expression level of Slc7a2 was significantly increased later (12–24 h) after infection in Ra-infected macrophages compared with macrophages infected with Rv (Fig. 3A–C). | Slc7a2 / infection;infected | none | |
| 20 | PMC7232099 | Solute Carrier Family 37 Member 2 (SLC37A2) Negatively Regulates Murine Macropha | **no** | yes | Toll-like receptor (TLR) 4 stimulation by lipopolysaccharide (LPS) rapidly increases macrophage SLC37A2 protein expression. | - / lipopolysaccharide;LPS | yes->no: evidence does not name the gene | |
| 23 | PMC6377304 | Loss of Solute Carrier Family 7 Member 2 Exacerbates Inflammation-Associated Col | **yes** | yes | IFN-\u03b3 + LPS stimulation resulted in robust expression of the M1 markers Nos2 and Il1b (Figure 6a) in both WT and Slc7a2\u2013/\u2013 BMmacs. | Slc7a2 / LPS | none | |
| 25 | PMC11077379 | Aberrant Expression of SLC7A11 Impairs the Antimicrobial Activities of Macrophag | **no** | no |  | - / - | none | |

## Hdc (search s_2829f53e, query `Hdc (histidine decarboxylase) LPS macrophage`)

| rank | paper | title | ledger verdict | model said | evidence quote | gene / stimulus terms found | downgrade | your call |
|---|---|---|---|---|---|---|---|---|
| 7 | PMC5763578 | Histone deacetylase 2 (HDAC2) attenuates lipopolysaccharide (LPS)-induced inflam | **no** | no |  | - / - | none | |
| 9 | PMC6821885 | Lipopolysaccharide-induced expansion of histidine decarboxylase-expressing Ly6G+ | **yes** | yes | Quantitative RT-PCR analysis demonstrated that the endogenous Hdc mRNA level was increased 6.1-fold in the lung at 4 hours after LPS administration (L33). | Hdc / LPS | none | |
| 10 | PMC7497259 | Histamine and histidine decarboxylase: Immunomodulatory functions and regulatory | **no** | yes | We found that the GFP-positive histamine-producing neutrophils were dramatically increased in lung and circulating peripheral blood under septic conditions (Takai et al., 2019). | - / septic | yes->no: evidence does not name the gene | |
| 13 | PMC10316655 | HDAC3 promotes macrophage pyroptosis via regulating histone deacetylation in acu | **no** | yes | As shown in Figures 1A and 1B, compared with the baseline status, both the protein and mRNA expression levels of HDAC3 were obviously increased in lung tissues from LPS-treated mice. | - / LPS | yes->no: evidence does not name the gene | |
| 20 | PMC6830127 | Targeting Histone Deacetylases in Myeloid Cells Inhibits Their Maturation and In | **no** | no |  | - / - | none | |

## Optional: every verdict that changed from Round 3 to Round 4

Same papers (all 12 genes had identical top 25s). Is the Round 4 verdict the right one?

| gene | rank | paper | title | R3 → R4 | why | Round 4 quote | your call |
|---|---|---|---|---|---|---|---|
| Tnf | 1 | PMC2213356 | Complementation of Lymphotoxin α Knockout Mice with Tumor Necrosis Fac | yes → **no** | yes->no: evidence does not name LPS or infection | Compared with background-matched wild-type control mice, LṮ́a knockout mice show severely reduced accumulation of TNF protein in both sera and macrophage exudates (Fig. 4), indicating that in addition to the LṮ́a null mutation, this strain of mice  | |
| Tnf | 8 | bio_206e5a356c66 | Mathematical modelling of activation-induced heterogeneity reveals cel | yes → **no** | yes->no: evidence does not name LPS or infection | Notably, the percentage of TNF-positive BMDMs peaked at 4h post stimulation, demonstrating a faster TNF response in BMDMs in comparison to RAW264.7 cells. | |
| Tnf | 15 | PMC9411976 | Mathematical modelling of activation-induced heterogeneity in TNF, IL6 | yes → **no** | yes->no: evidence does not name LPS or infection | Notably, the percentage of TNF-positive BMDMs peaked at 4h post stimulation, demonstrating a faster TNF response in BMDMs in comparison to RAW264.7 cells. | |
| Tnf | 19 | PMC2365439 | RNA from LPS-stirnulated macrophages induces the release of tumour nec | yes → **no** | model answer changed | (none) | |
| Nos2 | 1 | PMC4188127 | “Of Mice and Men”: Arginine Metabolism in Macrophages | no → **yes** | model answer changed | Sel-enomethionine ↓LPS-induced NOS2 expression (RNA and protein) and nitrite production | |
| Nos2 | 5 | PMC7851796 | Dataset on the differentiation of THP-1 monocytes to LPS inducible adh | yes → **no** | model answer changed | (none) | |
| Nos2 | 22 | PMC5967330 | Macrophage inducible nitric oxide synthase circulates inflammation and | yes → **no** | model answer changed | (none) | |
| Nos2 | 23 | PMC6920088 | Inducible nitric oxide synthase-derived extracellular nitric oxide flu | yes → **no** | yes->no: evidence does not name the gene | L19: In contrast, in BMDM, LPS alone (18hr) elicited intermediate NO flux which was markedly augmented when combined with IFNγ. | |
| Edn1 | 13 | PMC13483658 | miR-379-5p serves as a biomarker and regulates sepsis-associated acute | yes → **no** | model answer changed | (none) | |
| Edn1 | 17 | PMC3826139 | Chlorella 11-Peptide Inhibits the Production of Macrophage-Induced Adh | yes → **no** | model answer changed | (none) | |
| Slc7a2 | 16 | PMC7386301 | Species-Specificity of Transcriptional Regulation and the Response to  | yes → **no** | model answer changed | (none) | |
| Hdc | 5 | PMC13493966 | Sympathetic signaling activation alleviated acute respiratory distress | yes → **no** | yes->no: evidence does not name LPS or infection | Western blot analysis also showed a pronounced elevation of HDC protein in norepinephrine-treated cells (Fig. 4F, G). | |
