#!/usr/bin/env python3
"""
Module: build_manuscript
Purpose: Build jev-bioinformatics-Manuscript-Arli.docx in the NYC conference proceeding format.
Author: Dr. Arli Aditya Parikesit
Date: 2026
Parameters:
    - Layout: Times New Roman 11 pt, 2 cm margins, single spacing, 6 pt after paragraphs
    - Equations: native Word OMML (Office Math), Cambria Math, numbered at the right margin
Requires: python-docx 1.2.0, lxml; figures from scripts/fig1_workflow.py and scripts/robustness_kmer.py
"""
import csv, os, sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "jev-bioinformatics-Manuscript-Arli.docx")
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
FONT = "Times New Roman"

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
    setattr(sec, side, Cm(2))
st = doc.styles["Normal"]
st.font.name, st.font.size = FONT, Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_before, st.paragraph_format.space_after = Pt(0), Pt(6)
st.paragraph_format.line_spacing = 1.0


# ---------- text helpers ----------
def para(text="", bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=11, after=6, before=0, keep=False):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after, p.paragraph_format.space_before = Pt(after), Pt(before)
    if keep:
        p.paragraph_format.keep_with_next = True
    if text:
        add_runs(p, text, bold=bold, italic=italic, size=size)
    return p


def add_runs(p, text, bold=False, italic=False, size=11):
    """Inline markup: *italic* and ^superscript^ (only paired delimiters are markup)."""
    import re
    for tok in re.split(r"(\*[^*\s][^*]*\*|\^[^^]+\^)", text):
        if not tok:
            continue
        ital = len(tok) > 2 and tok[0] == tok[-1] == "*"
        sup = len(tok) > 2 and tok[0] == tok[-1] == "^"
        r = p.add_run(tok[1:-1] if ital or sup else tok)
        r.bold, r.font.size, r.font.name = bold, Pt(size), FONT
        r.italic, r.font.superscript = italic or ital, sup
    return p


def heading(text):
    para(text, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, before=6, keep=True)


def sub(text):
    para(text, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, keep=True)


def caption(label, text, keep=False):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, keep=keep, before=3)
    add_runs(p, label, bold=True)
    add_runs(p, " " + text)


# ---------- Office Math (OMML) builders ----------
def m(tag, *kids, **attrs):
    el = etree.Element(f"{{{M}}}{tag}")
    for k, v in attrs.items():
        el.set(f"{{{M}}}{k}", v)
    for c in kids:
        el.append(c)
    return el


def r(text, plain=False):
    run = m("r")
    if plain:
        run.append(m("rPr", m("sty", val="p"), m("nor")))
    wr = etree.SubElement(run, f"{{{W}}}rPr")
    f = etree.SubElement(wr, f"{{{W}}}rFonts")
    for a in ("ascii", "hAnsi"):
        f.set(f"{{{W}}}{a}", "Cambria Math")
    t = etree.SubElement(run, f"{{{M}}}t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return run


def e(*kids): return m("e", *kids)
def ssub(b, s): return m("sSub", e(*b), m("sub", *s))
def ssup(b, s): return m("sSup", e(*b), m("sup", *s))
def frac(n, d): return m("f", m("num", *n), m("den", *d))


def delim(content, beg="(", end=")"):
    return m("d", m("dPr", m("begChr", val=beg), m("endChr", val=end)), e(*content))


def limlow(base, lim): return m("limLow", e(*base), m("lim", *lim))


def eqarr(*rows): return m("eqArr", *[e(*row) for row in rows])


def equation(parts, number):
    t = doc.add_table(rows=1, cols=2)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    left, right = t.rows[0].cells
    left.width, right.width = Cm(15.5), Cm(1.5)
    pl = left.paragraphs[0]
    pl.paragraph_format.space_before, pl.paragraph_format.space_after = Pt(4), Pt(4)
    pl._p.append(m("oMathPara", m("oMath", *parts)))
    pr = right.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    pr.paragraph_format.space_before = Pt(4)
    pr.add_run(f"({number})").font.name = FONT
    return t


K = lambda x: [ssub([r("𝒦")], [r("k")]), delim([r(x)])]

# ---------- pseudocode box ----------
def code_box(label, title, lines):
    caption(label, title, keep=True)
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single"); b.set(qn("w:sz"), "8"); b.set(qn("w:color"), "1F4E79")
        borders.append(b)
    tcPr.append(borders)
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), "F2F6FA")
    tcPr.append(shd)
    cell.paragraphs[0].text = ""
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = i < len(lines) - 1
        run = p.add_run(line)
        run.font.name, run.font.size = "Courier New", Pt(8.5)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
    para(after=2)


def table(label, title, header, rows, widths, size=9):
    caption(label, title, keep=True)
    t = doc.add_table(rows=1, cols=len(header))
    t.style, t.alignment = "Table Grid", WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""
        add_runs(c.paragraphs[0], h, bold=True, size=size)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], str(v), size=size)
    for row in t.rows:
        for i, c in enumerate(row.cells):
            c.width = Cm(widths[i])
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.keep_with_next = True
    para(after=2)


def figure(path, width_cm, label, text):
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, after=0, keep=True)
    p.add_run().add_picture(path, width=Cm(width_cm))
    caption(label, text)


# =====================================================================
# FRONT MATTER
# =====================================================================
para("TWO-TIER AI TRIAGE FOR VIRAL GENE ANNOTATION WITHOUT RUNTIME SEQUENCE DATABASE QUERIES: "
     "A FIVE-PATHOGEN PROOF OF CONCEPT FOUNDED ON JAPANESE ENCEPHALITIS VIRUS",
     bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
para("Arli Aditya Parikesit^1*^", align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("^1^ORCID: 0000-0001-8716-3926, i3L University (formerly Indonesia International Institute for Life Sciences), "
     "Department of Biotechnology, Field of study: Bioinformatics, Jakarta, Indonesia.",
     align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("* arli.parikesit@i3l.ac.id, +6229567888", align=WD_ALIGN_PARAGRAPH.CENTER, after=12)

para("Abstract", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)
para("Annotation of viral gene sequences normally depends on remote database searches such as NCBI BLAST, or on a "
     "local nucleotide database of tens of gigabytes. Neither option sits well with laboratories that work under "
     "limited bandwidth, limited storage, or outbreak field conditions. We present the General Viral Gene Annotator, "
     "an open pipeline that assigns a query FASTA sequence to one of five human viral pathogens: Japanese encephalitis "
     "virus (gp2), SARS-CoV-2 (ORF1ab), influenza A H5N1 (NA), poliovirus (PVgp1), and HIV-1 (gag-pol). Reference genes "
     "were retrieved once from NCBI Datasets and stored locally, so no database query is issued at run time. The "
     "pipeline joins a deterministic step to a probabilistic one. A dependency-free Python k-mer engine (k = 15) computes, on both strands, the fraction of unique query k-mers shared with each reference gene, which gives an inspectable "
     "similarity profile. That profile, together with sequence length and a sequence preview, is passed to a "
     "constrained-choice probabilistic model (Tier 1) returning a class probability and a decision confidence of "
     "2|p − 0.5|. Samples above a confidence of 0.85 whose label agrees with the k-mer top hit are reported directly. Ambiguous or discordant samples escalate to a large "
     "language model (Tier 2) that reports homology, candidate recombination, and sequencing artefacts as narrative "
     "text, falling back to the Tier 1 call when that service is unreachable. Records run concurrently under asyncio. "
     "The k-mer step identified an HIV-1 gag-pol gene under a nonsense FASTA header from sequence alone, and of 1,200 simulated mutated or fragmented JEV queries it assigned none to another virus, leaving low-evidence queries unassigned. "
     "Thresholds remain computational heuristics, the panel is small, and no wet-laboratory calibration has been "
     "performed, so every call is a hypothesis for confirmation by BLAST, RT-qPCR, or Sanger sequencing. The source "
     "code is available at https://github.com/Johnkecops/General-Viral-Gene-Annotator.")
p = para(align=WD_ALIGN_PARAGRAPH.LEFT)
add_runs(p, "Keywords: ", bold=True)
add_runs(p, "viral genomics; sequence annotation; k-mer similarity; large language models; low-resource bioinformatics")

# =====================================================================
# INTRODUCTION
# =====================================================================
heading("INTRODUCTION")
para("Annotation of a new viral sequence usually starts with a similarity search against a public archive. BLAST "
     "remains the default tool for this step, because its seed-and-extend heuristic returns alignments with E-values "
     "that most virologists know how to read (Altschul et al., 1990; Camacho et al., 2009). The search is either sent "
     "to the NCBI servers or run against a local copy of the nucleotide collection, and each route has a cost. Remote "
     "queries need a stable connection and wait in a shared queue, while a local database occupies tens of gigabytes "
     "and must be refreshed. Portable sequencing during the West African Ebola outbreak showed that sequencing itself "
     "can now be done in the field, and that analysis close to the sample becomes the limiting step (Quick et al., "
     "2016). The same constraint applies to arbovirus surveillance in Indonesia, where routine and standardized "
     "diagnosis of Japanese encephalitis is still missing in most provinces (Garjito et al., 2018).")
para("Alignment-free methods lower this cost by comparing sequences through the words they contain, usually k-mers, "
     "instead of computing alignments (Zielezinski et al., 2017). Kraken 2 assigns reads to taxa through exact "
     "k-mer matches against a precomputed library (Wood et al., 2019), and Mash estimates mutation distance from "
     "MinHash sketches of k-mer sets (Ondov et al., 2016). The containment index, the fraction of one set's words "
     "found in another, was defined for comparing documents (Broder, 1997) and suits the case where a short query "
     "is compared with a longer reference. These tools still need a reference library, although the library can be "
     "small when the panel of target pathogens is fixed in advance.")
para("Language models have also entered sequence analysis. DNABERT and the Nucleotide Transformer learn "
     "representations of genomic sequence through pre-training (Ji et al., 2021; Dalla-Torre et al., 2025), and "
     "general-purpose large language models (LLMs) have been tested on annotation tasks such as naming cell types "
     "from marker genes (Hou and Ji, 2024). Their outputs are probabilistic, and their explanations can be fluent "
     "and wrong, a failure mode known as hallucination (Ji et al., 2023). A pipeline that uses such models for "
     "annotation therefore needs a deterministic anchor that a person can check, plus a rule that decides when a "
     "model's call is accepted. The classical form of that rule is the reject option, in which a classifier "
     "abstains when its confidence falls below a threshold (Chow, 1970).")
para("Japanese encephalitis virus (JEV) is a mosquito-borne flavivirus with a positive-sense RNA genome of about "
     "11 kb that encodes a single polyprotein (Sumiyoshi et al., 1987). An estimated 67,900 cases of Japanese "
     "encephalitis occur each year in 24 endemic countries of Asia and the Western Pacific, and only about 10% are "
     "reported to the World Health Organization (Campbell et al., 2011). Ardeid birds maintain the virus, pigs amplify "
     "it, and *Culex* mosquitoes carry it to people (Mulvey et al., 2021). Phylogeographic work places the origin of "
     "JEV in the Indonesia-Malaysia region, where all genotypes have circulated (Solomon et al., 2003; Schuh et al., "
     "2013). Recent Indonesian surveillance detected the virus in mosquito pools and bats from 11 provinces "
     "(Diptyanusa et al., 2022) and genotype III in sentinel pigs in Bali (Kardena et al., 2024). Elsewhere, genotype "
     "I has replaced genotype III as the dominant lineage in much of Asia (Pan et al., 2011), and the virus reached "
     "south-eastern Australia in 2022 (van den Hurk et al., 2022).")
para("These traits make JEV a demanding founding case for a general annotator. Its genotypes differ from one another "
     "by up to about 20% at the nucleotide level (Solomon et al., 2003), which is a hard test for exact-match "
     "methods. Its polyprotein gene organisation is shared with poliovirus and, through the ORF1ab polyprotein, with "
     "SARS-CoV-2, so a design that handles JEV should carry over to those genes (Kitamura et al., 1981; Wu et al., "
     "2020). This paper describes the General Viral Gene Annotator, a Python pipeline that began as a JEV triage "
     "script and now assigns a query FASTA sequence to one of five human viral pathogens without querying a sequence "
     "database at run time. The study reverse-engineers the published codebase to document its design, recomputes "
     "its deterministic layer on the bundled data, and measures how that layer behaves as a JEV query diverges from "
     "its reference, following the benchmarking logic proposed for alignment-free tools (Zielezinski et al., 2019).")

# =====================================================================
# MATERIALS AND METHODS
# =====================================================================
heading("MATERIALS AND METHODS")
sub("Reference panel and query sets")
para("Reference genes for the five pathogens were downloaded once from NCBI Datasets as gene data packages "
     "(O'Leary et al., 2024) and stored with the code (Table 1). Each package holds the coding sequence in FASTA "
     "format, a JSON Lines data report and an MD5 checksum file. The panel contains the JEVgp2 gene of strain "
     "JaOArS982, annotated by NCBI as a truncated polyprotein (Sumiyoshi et al., 1987), SARS-CoV-2 ORF1ab from "
     "Wuhan-Hu-1 (Wu et al., 2020), the neuraminidase gene of A/goose/Guangdong/1/1996 (H5N1) (Xu et al., 1999), the "
     "poliovirus type 1 Mahoney polyprotein gene PVgp1 (Kitamura et al., 1981) and HIV-1 gag-pol from HXB2 (Ratner "
     "et al., 1985). The whole panel is 37,233 nt long.")
table("Table 1.", "Local reference panel retrieved from NCBI Datasets and used at run time.",
      ["Pathogen (family)", "Gene", "RefSeq accession: range", "NCBI GeneID", "TaxID", "Length (nt)"],
      [["JEV (Flaviviridae)", "JEVgp2", "NC_001437.1: 96-3691", "12978160", "11072", "3,596"],
       ["SARS-CoV-2 (Coronaviridae)", "ORF1ab", "NC_045512.2: 266-21555", "43740578", "2697049", "21,290"],
       ["Influenza A H5N1 (Orthomyxoviridae)", "NA", "NC_007361.1: 21-1430", "3654619", "93838", "1,410"],
       ["Poliovirus 1 (Picornaviridae)", "PVgp1", "NC_002058.3: 743-7372", "919920", "138950", "6,630"],
       ["HIV-1 (Retroviridae)", "gag-pol", "NC_001802.1: 336-4642", "155348", "11676", "4,307"]],
      [4.6, 1.6, 3.9, 2.1, 1.7, 1.9])
para("Three query sets from the repository, all in FASTA format (Pearson and Lipman, 1988), were analysed. The five "
     "reference files were run as self-queries. The file gene.fasta carries the 4,307 nt HIV-1 gag-pol sequence "
     "under the meaningless header \">tralalalalalaallaalal\", which tests whether a call depends on the header. The "
     "file jev_samples.fasta holds two 112 nt synthetic controls built from the tandem repeats (CGTA)n and (GGGAAA)n, "
     "with headers that falsely label them as a JEV genotype III sample and an ambiguous recombinant.")

sub("FASTA parsing and k-mer containment")
para("The parser reads FASTA files line by line in plain Python, so the pipeline needs no Biopython or other "
     "sequence library (Cock et al., 2009). A header line starting with \">\" opens a new record, the following lines "
     "are concatenated, blank lines are skipped, and undecodable bytes are replaced instead of stopping the run. Only "
     "the first record of each reference file is kept, and it is converted to upper case. Pseudocode 1 gives the "
     "procedure together with the scoring step, which follows the word-based framework reviewed by Zielezinski et al. "
     "(2017). For a sequence *S* of length |*S*|, the set of distinct k-mers is given by Eq. (1).")
equation([*K("S"), r("="), delim([r("S"), delim([r("i … i+k−1")], "[", "]"), r(" : 1 ≤ i ≤ "),
          delim([r("S")], "|", "|"), r("−k+1")], "{", "}")], 1)
para("The similarity of a query *Q* to a reference *R* is the containment of the query's k-mer set in the "
     "reference's set (Broder, 1997), as written in Eq. (2); *C* is set to 0 when either sequence is shorter than *k*. "
     "The pipeline uses *k* = 15. There are 4^15^ ≈ 1.07 × 10^9^ possible 15-mers, so chance matches between unrelated "
     "viral genes of a few kilobases are rare, which is the same reasoning behind the k-mer lengths used by Mash and "
     "Kraken (Ondov et al., 2016; Wood et al., 2019). The best-matching reference is selected by Eq. (3), where *V* "
     "is the set of five panel viruses. Before scoring, U is read as T, any k-mer that spans N or another ambiguity code is dropped, and Eq. (2) is evaluated for the query and for its reverse complement, keeping the larger value, so a gene submitted on the opposite strand is still recognised, in the same spirit as the canonical k-mers of Mash (Ondov et al., 2016). The top hit of Eq. (3) is reported only when that reference shares at least five distinct 15-mers with the query, and as none otherwise. The panel genes share no 15-mer with one another on either strand, and random sequences of 112 nt to 21 kb shared at most four with any panel gene, so the minimum sits just above the chance level seen for this panel.")
equation([r("C"), delim([r("Q,R")]), r("="),
          frac([delim([*K("Q"), r("∩"), *K("R")], "|", "|")], [delim([*K("Q")], "|", "|")])], 2)
equation([r("v̂"), r("="), m("func", m("fName", limlow([r("argmax", plain=True)], [r("v∈V")])),
                              e(r("C"), delim([r("Q,"), ssub([r("R")], [r("v")])])))], 3)
para("Because every k-mer that contains a substituted base is lost, the expected containment of a query that "
     "differs from its reference by uniform point substitutions at rate *r* follows Eq. (4) when spurious matches "
     "are ignored (Blanca et al., 2022). To test this behaviour, the JEVgp2 reference was mutated at rates from 0% "
     "to 30% with 50 replicates per rate and random seed 42, each substituted base changing to one of the other three "
     "with equal probability. Random fragments of 50 to 3,000 nt were also drawn at 0% and 5% substitution. Every "
     "simulated query was scored against all five references with the pipeline's own scoring functions, imported unchanged from the script, and its top hit was recorded under the five-k-mer minimum.")
equation([r("E"), delim([r("C")], "[", "]"), r("≈"), ssup([delim([r("1−r")])], [r("k")])], 4)
code_box("Pseudocode 1.", "FASTA parsing and k-mer containment scoring (native Python, no external libraries).", [
    "PROCEDURE PARSE_FASTA(file)",
    "  records ← [ ];  id ← NULL;  seq ← [ ]",
    "  FOR each line IN file DO",
    "    line ← STRIP(line);  IF line = \"\" THEN CONTINUE",
    "    IF line starts with \">\" THEN",
    "      IF id ≠ NULL THEN APPEND (id, JOIN(seq)) TO records",
    "      id ← line[2..];  seq ← [ ]",
    "    ELSE APPEND line TO seq",
    "  IF id ≠ NULL THEN APPEND (id, JOIN(seq)) TO records",
    "  RETURN records",
    "",
    "PROCEDURE KMER_CONTAINMENT(Q, R, k = 15)",
    "  Q ← UPPER(Q) with U read as T;  R ← UPPER(R)",
    "  KQ ← { Q[i .. i+k−1] : i = 1 … |Q|−k+1 }, A/C/G/T only   ▷ Eq. (1)",
    "  KQ' ← same for REVCOMP(Q);  KR ← same for R",
    "  IF KQ = ∅ THEN RETURN (0, 0)",
    "  s ← MAX(|KQ ∩ KR|, |KQ' ∩ KR|)",
    "  RETURN (s, s / |KQ|)                                ▷ Eq. (2)",
])

sub("Tier 1: constrained-choice classification")
para("The FASTA header, the containment profile, the sequence length and the first 300 nt of the sequence are "
     "assembled into a text block (bio_state) and sent to TypeSafe System One, a constrained-choice decision model "
     "reached through the typesafe-sdk client (TypeSafe AI, 2026). The model must choose one of six labels: jev, "
     "sars_cov_2, influenza_h5n1, poliovirus, hiv, or none (non-viral or synthetic). It returns the chosen label, a "
     "probability distribution over the six labels and a decision confidence. The project documentation defines "
     "confidence from the probability *p* of a call as in Eq. (5), so *p* = 0.5 gives γ = 0 and *p* = 0 or 1 gives "
     "γ = 1; in the code the value is read directly from the SDK response. A call is accepted only when γ reaches the threshold τ = 0.85 and the chosen label ℓ agrees with the k-mer top hit v̂ of Eq. (3), as in Eq. (6), which is a reject option in the sense of Chow (1970). A confident label that contradicts v̂ is marked discordant and escalated, so the model cannot overrule the sequence evidence without a second look. Solving Eq. (5) for *p* "
     "shows that a record escalates whenever 0.075 < *p* < 0.925.")
equation([r("γ"), r("="), r("2"), delim([r("p−0.5")], "|", "|")], 5)
equation([r("call", plain=True), r("="), delim([eqarr(
    [r("Auto-Processed,", plain=True), r("  γ≥τ ∧ ℓ=v̂")],
    [r("Escalate to Tier 2,", plain=True), r("  otherwise", plain=True)])], "{", ""),
    r(",   τ=0.85")], 6)

sub("Tier 2: language model escalation, fallback and concurrency")
para("Records below the threshold, and discordant records, go to a large language model through the google-genai client, using the model "
     "identifier gemini-3.8-flash set in the script (Gemini Team, 2023). The system instruction frames the model as a "
     "viral genomics expert covering flaviviruses, coronaviruses, orthomyxoviruses, picornaviruses and retroviruses, "
     "and the prompt asks for homology, candidate recombination and anomalies given the bio_state block, with output "
     "capped at 1,500 tokens. The answer is free text stored beside the Tier 1 label, which stays the reported top "
     "hit. If the call fails, the record is marked \"Tier 1 Fallback (Gemini Unreachable)\" and the Tier 1 label "
     "stands. Because LLM text can contain confident errors (Ji et al., 2023), Tier 2 output is meant for a human "
     "reviewer. Pseudocode 2 summarises the triage of one record.")
code_box("Pseudocode 2.", "Two-tier triage of a FASTA record and concurrent execution.", [
    "PROCEDURE TRIAGE(record, panel, τ = 0.85, m = 5)",
    "  FOR each virus v IN panel DO",
    "    (s[v], C[v]) ← KMER_CONTAINMENT(record.seq, panel[v])",
    "  v_top ← argmax_v s[v];  IF s[v_top] < m THEN v_top ← none   ▷ Eq. (3)",
    "  state ← (record.id, v_top, C, |record.seq|, record.seq[1..300])",
    "  TRY",
    "    (label, P, γ) ← TIER1_CHOICE(state, {jev, sars_cov_2, influenza_h5n1,",
    "                                        poliovirus, hiv, none})",
    "  CATCH err:  RETURN (v_top, C, \"Alignment-Only\", err)",
    "  IF γ ≥ τ AND label = v_top THEN                            ▷ Eq. (6)",
    "    RETURN (label, γ, P, C, \"Auto-Processed\")",
    "  TRY   text ← TIER2_LLM(state);  status ← \"Escalated to Gemini\"",
    "  CATCH err:  text ← err;  status ← \"Tier 1 Fallback\"",
    "  IF γ ≥ τ THEN status ← \"Discordant: \" + status",
    "  RETURN (label, v_top, γ, P, C, status, text)",
    "",
    "MAIN:  results ← AWAIT GATHER( TRIAGE(r, panel) FOR r IN PARSE_FASTA(query) ),",
    "       at most 8 records in flight",
])
para("Each record runs as an asynchronous coroutine, and all records are awaited together with asyncio.gather, at most eight at a time, so "
     "network latency for one record does not hold up the others (Python Software Foundation, 2026). Figure 1 shows "
     "the complete workflow. The pipeline needs Python 3.10 or later with the packages google-genai, typesafe-sdk "
     "and httpx, and it reads its API keys from the TYPESAFE_API_KEY and GEMINI_API_KEY environment variables; without them it reports the k-mer profile alone. The "
     "codebase is deposited on GitHub and is being released as a Streamlit web application, so that users can "
     "upload FASTA files through a browser (Streamlit, 2026). The robustness simulation and figures in this paper "
     "were produced with Python 3.11.5, NumPy 1.26.4 and Matplotlib 3.8.2 (scripts/robustness_kmer.py and "
     "scripts/fig1_workflow.py in the project folder).")
figure(os.path.join(ROOT, "results/figures/fig1_workflow.png"), 16.5, "Figure 1.",
       "Workflow of the General Viral Gene Annotator. Green boxes are deterministic and run offline; blue boxes form "
       "Tier 1; the orange box is the Tier 2 language model path with its fallback.")

# =====================================================================
# RESULTS
# =====================================================================
heading("RESULTS")
with open(os.path.join(ROOT, "results/tables/containment_matrix.csv")) as fh:
    rows = list(csv.reader(fh))
qname = {"jev-gp2-gene.fa": "JEVgp2 reference", "sars-cov-2-orf1ab-gene.fna": "SARS-CoV-2 ORF1ab reference",
         "H5N1-NA-gene.fna": "H5N1 NA reference", "Polio-PVgp1-gene.fna": "PVgp1 reference",
         "HIV-gag-pol-gene.fna": "HIV-1 gag-pol reference", "gene.fasta": "gene.fasta (nonsense header)"}
body = []
for f, i, L, *v in rows[1:]:
    name = qname.get(f, "Control " + ("(CGTA)n" if "01" in i else "(GGGAAA)n"))
    body.append([name, f"{int(L):,}"] + [f"{float(x) / 100:.3f}" for x in v])
para("Table 2 lists the containment scores recomputed from the repository files. Each reference gene scored "
     "*C* = 1.000 against itself and 0.000 against the other four, so the five panel genes share no 15-mer. This is "
     "expected for genes from five virus families that are unrelated at the nucleotide level (Zielezinski et al., "
     "2017). The header-blind file gene.fasta gave the same profile as the HIV-1 reference because its sequence is "
     "identical to it. Both tandem-repeat controls scored 0.000 against every reference; out of 98 overlapping "
     "positions they contain only 23 and 22 distinct 15-mers, and none occurs in a panel gene (Broder, 1997). Scoring both strands left every value in Table 2 unchanged. An earlier example output in the repository documentation showed off-target scores of 0.9% to 2.1% and an HIV-1 score of 68.4% for the same file, whereas the recomputation gives exactly 0% and 100%; the documentation now shows the recomputed output.")
table("Table 2.", "k-mer containment C (k = 15) of each query against the five references, recomputed from the "
      "repository files.", ["Query", "Length (nt)", "HIV-1", "SARS-CoV-2", "H5N1", "PV", "JEV"], body,
      [5.6, 1.9, 1.6, 1.9, 1.6, 1.6, 1.6])
para("For the Tier 1 layer, the project's recorded runs assigned the header-blind gene to HIV-1 and rejected both "
     "synthetic controls as non-JEV with *p* ≈ 0.03. Under Eq. (5) this gives γ = 2|0.03 − 0.5| = 0.94, above the "
     "0.85 threshold, so neither control reached Tier 2 (Chow, 1970). These Tier 1 values come from the project's run "
     "records and were not re-executed for this paper, because the proprietary services require paid API keys (TypeSafe AI, 2026). They also predate the six-class panel: they come from an earlier version of Tier 1 that asked a single JEV or non-JEV question, so they illustrate the confidence rule of Eq. (5) and do not measure the six-class model described above.")
para("Figure 2a shows the mean JEV containment of mutated full-length JEVgp2 queries. The simulated means followed "
     "Eq. (4) closely: 0.860 at 1% substitution (expected 0.860), 0.462 at 5% (0.463), 0.206 at 10% (0.206) and "
     "0.034 at 20% (0.035), in line with the k-mer survival model of Blanca et al. (2022). At 30% substitution the "
     "mean fell to 0.0045, and 1 of 50 replicates shared no 15-mer with the reference. The highest off-target score "
     "among all 500 mutated queries was 0.0008, about 3 of roughly 3,580 query k-mers, so JEV had the highest score whenever any JEV k-mer survived. Figure 2b shows that error-free fragments scored 1.000 at every length from 50 "
     "to 3,000 nt. At 5% substitution the mean stayed near the expected 0.463 at all lengths, but the spread widened "
     "as fragments shortened, from a standard deviation of 0.037 at 3,000 nt to 0.321 at 50 nt, and 5 of the 50 fragments of 50 nt shared no 15-mer with the reference. With the five-k-mer minimum, none of the 1,200 simulated queries was assigned to another virus: 3 of the 50 replicates at 30% substitution and 9 of the 50 fragments of 50 nt at 5% substitution were reported as none, and the rest were assigned to JEV. Without the minimum, one replicate at 30% substitution that kept no JEV 15-mer but matched SARS-CoV-2 by chance would have been reported as SARS-CoV-2.")
figure(os.path.join(ROOT, "results/figures/fig2_robustness.png"), 16.5, "Figure 2.",
       "Behaviour of the k = 15 containment score for simulated JEV queries (50 replicates per condition, seed 42). "
       "(a) Full-length JEVgp2 with uniform substitutions; the dashed line is Eq. (4). (b) Random fragments of the "
       "JEVgp2 reference at 0% and 5% substitution. Error bars are one standard deviation.")

# =====================================================================
# DISCUSSION
# =====================================================================
heading("DISCUSSION")
para("The annotator replaces a database search with a local panel of 37 kb, several orders of magnitude smaller than "
     "the multi-gigabyte collections used for local BLAST searches (Camacho et al., 2009). For a fixed surveillance "
     "question, such as whether a sample from a pig farm in Bali carries JEV, a small panel is enough, and the k-mer "
     "step runs on a laptop without a network connection, which matters for sequencing done in the field (Quick et "
     "al., 2016). Table 3 compares the approach with a standard BLAST pipeline. The deterministic layer can be "
     "audited: anyone can recompute Table 2 from the files, whereas the reasoning inside a language model cannot be "
     "reproduced in the same way (Zielezinski et al., 2017).")
table("Table 3.", "Comparison of a standard BLASTn pipeline with the General Viral Gene Annotator.",
      ["Feature", "Standard pipeline (BLASTn)", "General Viral Gene Annotator"],
      [["Detection method", "Local alignment, seed-and-extend heuristic", "Exact 15-mer containment plus constrained-choice model"],
       ["Reference data", "NCBI nt or RefSeq viral collections", "Five genes, 37,233 nt, stored with the code"],
       ["Network at run time", "Remote search needs it; local search needs large database updates", "None for the k-mer step; API calls for Tiers 1 and 2"],
       ["Reported metrics", "E-value, bit score, % identity, alignment coordinates", "Containment C, class probabilities, confidence γ, free text"],
       ["Divergent query", "Alignment extends through mismatches", "C decays as (1 − r)^15^ (Figure 2)"],
       ["Scope", "Any sequence in the database", "Five pathogens plus a none class"],
       ["Auditability", "Base-level alignment", "k-mer profile recomputable; model reasoning not"]],
      [3.2, 6.6, 6.8])
para("The simulation measures the main weakness of exact k-mer matching, and JEV is the panel member most exposed to it. Genotype "
     "IV differs from genotypes I to III by 17.4% to 19.6% at the nucleotide level (Solomon et al., 2003), and at that "
     "divergence Eq. (4) predicts a containment of only 0.04 to 0.06 against a single genotype III reference. Such a "
     "query would still be called JEV here, because the other panel genes share almost nothing with it, but the "
     "margin is thin, and a short or noisy read could lose every k-mer and fall into the none class. Genotype I, now "
     "dominant across Asia (Pan et al., 2011), and the genotype III strains found in Bali (Kardena et al., 2024) "
     "would each need their own reference, or a shorter *k*, before the score could separate a divergent JEV from a "
     "sequence that is simply new. BLAST copes better with this case because it extends alignments through "
     "mismatches and attaches an E-value to the result (Altschul et al., 1990).")
para("The Tier 1 model adds a label for inputs outside the panel, and the threshold decides how often a person must "
     "read an LLM report (Chow, 1970). The model receives the containment profile together with the 300 nt preview, "
     "which on its own is too short for most homology judgements. General-purpose LLMs were not trained for viral "
     "typing, and their annotation quality varies by task (Hou and Ji, 2024), so Tier 2 text is best read as a list "
     "of hypotheses. DNA foundation models trained on nucleotide sequence could replace the general model in a later "
     "version and would be easier to benchmark (Ji et al., 2021; Dalla-Torre et al., 2025).")
para("The evaluation has clear limits. The test queries are the reference sequences themselves, so Table 2 confirms "
     "that the scoring works as coded; it does not estimate accuracy on new isolates. The threshold of 0.85 was set by "
     "hand and has not been calibrated against laboratory results. Eq. (5) maps a binary probability to confidence, "
     "while the panel has six classes, and the SDK does not document how it computes the value it returns. An earlier version of the repository documentation gave the escalation band as 0.425 < *p* < 0.575, whereas Eq. (5) implies "
     "0.075 < *p* < 0.925; it has since been corrected. Tiers 1 and 2 depend on proprietary services whose model versions can change, which limits reproducibility (Gemini Team, 2023; TypeSafe AI, 2026). The minimum of five shared 15-mers is also empirical and fits a five-gene panel; larger panels or whole-genome queries raise the chance-match level and will need a length-aware threshold (Ondov et al., 2016).")
para("Every call from the annotator should therefore be treated as a hypothesis. A positive JEV call on a clinical, "
     "veterinary or mosquito sample should be confirmed by BLAST against RefSeq, by a JEV-specific TaqMan RT-PCR "
     "(Pyke et al., 2004) and by Sanger sequencing. Typing and recombination claims from Tier 2 should be checked with "
     "Genome Detective (Vilsker et al., 2019) and RDP5 (Martin et al., 2021) after reads are mapped with minimap2 (Li, "
     "2018). A fair benchmark would use held-out JEV genomes of all genotypes, with related flaviviruses as "
     "near-neighbour negatives, scored under the protocols proposed for alignment-free methods (Zielezinski et al., "
     "2019).")

# =====================================================================
# CONCLUSION
# =====================================================================
heading("CONCLUSION AND RECOMMENDATIONS")
para("The General Viral Gene Annotator assigns viral gene sequences to five pathogens using a 37 kb local reference "
     "panel, a 15-mer containment score and a two-tier AI decision layer, and it never queries a sequence database "
     "at run time. On the bundled data the deterministic layer separated the five genes completely, recognised an "
     "HIV-1 gene under a nonsense header, and gave zero similarity to two synthetic repeats. Simulation showed that "
     "containment falls as (1 − r)^15^, so a JEV query 20% divergent from its reference keeps only about 3% of its "
     "15-mers. Before field use, the panel should gain references for each JEV genotype and for related "
     "flaviviruses, the 0.85 threshold should be calibrated on labelled sequences with laboratory confirmation, and "
     "every positive call should be reported next to a BLAST check. The Streamlit release should show the k-mer "
     "profile to users, since it is the part of the output they can verify for themselves.")

heading("ACKNOWLEDGEMENTS")
para("The source code, reference data packages and example FASTA files of the General Viral Gene Annotator are "
     "available in the GitHub repository https://github.com/Johnkecops/General-Viral-Gene-Annotator. The author "
     "thanks i3L University for institutional support. Claude Pro from Anthropic ® was used for ideation, "
     "brainstorming, and outlining the manuscript. However, the author is solely responsible for the validity of "
     "the content.")

# =====================================================================
# REFERENCES (alphabetical, template format; DOI and PMID validated via Crossref and PubMed)
# =====================================================================
heading("REFERENCES")
REFS = [
    "Altschul SF, Gish W, Miller W, Myers EW, Lipman DJ 1990. Basic local alignment search tool. Journal of Molecular Biology, 215(3): 403-410. https://doi.org/10.1016/S0022-2836(05)80360-2 (PMID: 2231712)",
    "Blanca A, Harris RS, Koslicki D, Medvedev P 2022. The statistics of k-mers from a sequence undergoing a simple mutation process without spurious matches. Journal of Computational Biology, 29(2): 155-168. https://doi.org/10.1089/cmb.2021.0431 (PMID: 35108101)",
    "Broder AZ 1997. On the resemblance and containment of documents. In: Proceedings of Compression and Complexity of SEQUENCES 1997. Salerno: IEEE, pp. 21-29. https://doi.org/10.1109/SEQUEN.1997.666900",
    "Camacho C, Coulouris G, Avagyan V, Ma N, Papadopoulos J, Bealer K, Madden TL 2009. BLAST+: architecture and applications. BMC Bioinformatics, 10: 421. https://doi.org/10.1186/1471-2105-10-421 (PMID: 20003500)",
    "Campbell GL, Hills SL, Fischer M, Jacobson JA, Hoke CH, Hombach JM, Marfin AA, Solomon T, Tsai TF, Tsu VD, Ginsburg AS 2011. Estimated global incidence of Japanese encephalitis: a systematic review. Bulletin of the World Health Organization, 89(10): 766-774. https://doi.org/10.2471/BLT.10.085233 (PMID: 22084515)",
    "Chow CK 1970. On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory, 16(1): 41-46. https://doi.org/10.1109/TIT.1970.1054406",
    "Cock PJ, Antao T, Chang JT, Chapman BA, Cox CJ, Dalke A, et al. 2009. Biopython: freely available Python tools for computational molecular biology and bioinformatics. Bioinformatics, 25(11): 1422-1423. https://doi.org/10.1093/bioinformatics/btp163 (PMID: 19304878)",
    "Dalla-Torre H, Gonzalez L, Mendoza-Revilla J, Lopez Carranza N, Grzywaczewski AH, Oteri F, et al. 2025. Nucleotide Transformer: building and evaluating robust foundation models for human genomics. Nature Methods, 22(2): 287-297. https://doi.org/10.1038/s41592-024-02523-z (PMID: 39609566)",
    "Diptyanusa A, Herini ES, Indarjulianto S, Satoto TBT 2022. Estimation of Japanese encephalitis virus infection prevalence in mosquitoes and bats through nationwide sentinel surveillance in Indonesia. PLoS ONE, 17(10): e0275647. https://doi.org/10.1371/journal.pone.0275647 (PMID: 36223381)",
    "Garjito TA, Widiarti, Anggraeni YM, Alfiah S, Tunggul Satoto TB, Farchanny A, et al. 2018. Japanese encephalitis in Indonesia: an update on epidemiology and transmission ecology. Acta Tropica, 187: 240-247. https://doi.org/10.1016/j.actatropica.2018.08.017 (PMID: 30118700)",
    "Gemini Team 2023. Gemini: a family of highly capable multimodal models. arXiv, 2312.11805. https://doi.org/10.48550/arXiv.2312.11805",
    "Hou W, Ji Z 2024. Assessing GPT-4 for cell type annotation in single-cell RNA-seq analysis. Nature Methods, 21(8): 1462-1465. https://doi.org/10.1038/s41592-024-02235-4 (PMID: 38528186)",
    "Ji Y, Zhou Z, Liu H, Davuluri RV 2021. DNABERT: pre-trained Bidirectional Encoder Representations from Transformers model for DNA-language in genome. Bioinformatics, 37(15): 2112-2120. https://doi.org/10.1093/bioinformatics/btab083 (PMID: 33538820)",
    "Ji Z, Lee N, Frieske R, Yu T, Su D, Xu Y, et al. 2023. Survey of hallucination in natural language generation. ACM Computing Surveys, 55(12): 1-38. https://doi.org/10.1145/3571730",
    "Kardena IM, Adi AAAM, Astawa INM, Oka IBM, Sahibzada S, Bruce M, O'Dea M 2024. Seroconversion, genotyping, and potential mosquito vector identification of Japanese encephalitis virus in pig sentinel settings in Bali, Indonesia. Veterinary World, 17(1): 89-98. https://doi.org/10.14202/vetworld.2024.89-98 (PMID: 38406355)",
    "Kitamura N, Semler BL, Rothberg PG, Larsen GR, Adler CJ, Dorner AJ, et al. 1981. Primary structure, gene organization and polypeptide expression of poliovirus RNA. Nature, 291(5816): 547-553. https://doi.org/10.1038/291547a0 (PMID: 6264310)",
    "Li H 2018. Minimap2: pairwise alignment for nucleotide sequences. Bioinformatics, 34(18): 3094-3100. https://doi.org/10.1093/bioinformatics/bty191 (PMID: 29750242)",
    "Martin DP, Varsani A, Roumagnac P, Botha G, Maslamoney S, Schwab T, et al. 2021. RDP5: a computer program for analyzing recombination in, and removing signals of recombination from, nucleotide sequence datasets. Virus Evolution, 7(1): veaa087. https://doi.org/10.1093/ve/veaa087 (PMID: 33936774)",
    "Mulvey P, Duong V, Boyer S, Burgess G, Williams DT, Dussart P, Horwood PF 2021. The ecology and evolution of Japanese encephalitis virus. Pathogens, 10(12): 1534. https://doi.org/10.3390/pathogens10121534 (PMID: 34959489)",
    "O'Leary NA, Cox E, Holmes JB, Anderson WR, Falk R, Hem V, et al. 2024. Exploring and retrieving sequence and metadata for species across the tree of life with NCBI Datasets. Scientific Data, 11: 732. https://doi.org/10.1038/s41597-024-03571-y (PMID: 38969627)",
    "Ondov BD, Treangen TJ, Melsted P, Mallonee AB, Bergman NH, Koren S, Phillippy AM 2016. Mash: fast genome and metagenome distance estimation using MinHash. Genome Biology, 17: 132. https://doi.org/10.1186/s13059-016-0997-x (PMID: 27323842)",
    "Pan XL, Liu H, Wang HY, Fu SH, Liu HZ, Zhang HL, et al. 2011. Emergence of genotype I of Japanese encephalitis virus as the dominant genotype in Asia. Journal of Virology, 85(19): 9847-9853. https://doi.org/10.1128/JVI.00825-11 (PMID: 21697481)",
    "Pearson WR, Lipman DJ 1988. Improved tools for biological sequence comparison. Proceedings of the National Academy of Sciences of the USA, 85(8): 2444-2448. https://doi.org/10.1073/pnas.85.8.2444 (PMID: 3162770)",
    "Pyke AT, Smith IL, van den Hurk AF, Northill JA, Chuan TF, Westacott AJ, et al. 2004. Detection of Australasian Flavivirus encephalitic viruses using rapid fluorogenic TaqMan RT-PCR assays. Journal of Virological Methods, 117(2): 161-167. https://doi.org/10.1016/j.jviromet.2004.01.007 (PMID: 15041213)",
    "Python Software Foundation 2026. asyncio: Asynchronous I/O. Python 3 documentation. Available at: https://docs.python.org/3/library/asyncio.html [29.09.2026]",
    "Quick J, Loman NJ, Duraffour S, Simpson JT, Severi E, Cowley L, et al. 2016. Real-time, portable genome sequencing for Ebola surveillance. Nature, 530(7589): 228-232. https://doi.org/10.1038/nature16996 (PMID: 26840485)",
    "Ratner L, Haseltine W, Patarca R, Livak KJ, Starcich B, Josephs SF, et al. 1985. Complete nucleotide sequence of the AIDS virus, HTLV-III. Nature, 313(6000): 277-284. https://doi.org/10.1038/313277a0 (PMID: 2578615)",
    "Schuh AJ, Ward MJ, Brown AJ, Barrett AD 2013. Phylogeography of Japanese encephalitis virus: genotype is associated with climate. PLoS Neglected Tropical Diseases, 7(8): e2411. https://doi.org/10.1371/journal.pntd.0002411 (PMID: 24009790)",
    "Solomon T, Ni H, Beasley DW, Ekkelenkamp M, Cardosa MJ, Barrett AD 2003. Origin and evolution of Japanese encephalitis virus in southeast Asia. Journal of Virology, 77(5): 3091-3098. https://doi.org/10.1128/JVI.77.5.3091-3098.2003 (PMID: 12584335)",
    "Streamlit 2026. Streamlit: a faster way to build and share data apps. Available at: https://streamlit.io [29.09.2026]",
    "Sumiyoshi H, Mori C, Fuke I, Morita K, Kuhara S, Kondou J, et al. 1987. Complete nucleotide sequence of the Japanese encephalitis virus genome RNA. Virology, 161(2): 497-510. https://doi.org/10.1016/0042-6822(87)90144-9 (PMID: 3686827)",
    "TypeSafe AI 2026. System One decision models and typesafe-sdk. Available at: https://typesafe.ai [29.09.2026]",
    "van den Hurk AF, Skinner E, Ritchie SA, Mackenzie JS 2022. The emergence of Japanese encephalitis virus in Australia in 2022: existing knowledge of mosquito vectors. Viruses, 14(6): 1208. https://doi.org/10.3390/v14061208 (PMID: 35746679)",
    "Vilsker M, Moosa Y, Nooij S, Fonseca V, Ghysens Y, Dumon K, et al. 2019. Genome Detective: an automated system for virus identification from high-throughput sequencing data. Bioinformatics, 35(5): 871-873. https://doi.org/10.1093/bioinformatics/bty695 (PMID: 30124794)",
    "Wood DE, Lu J, Langmead B 2019. Improved metagenomic analysis with Kraken 2. Genome Biology, 20: 257. https://doi.org/10.1186/s13059-019-1891-0 (PMID: 31779668)",
    "Wu F, Zhao S, Yu B, Chen YM, Wang W, Song ZG, et al. 2020. A new coronavirus associated with human respiratory disease in China. Nature, 579(7798): 265-269. https://doi.org/10.1038/s41586-020-2008-3 (PMID: 32015508)",
    "Xu X, Subbarao K, Cox NJ, Guo Y 1999. Genetic characterization of the pathogenic influenza A/Goose/Guangdong/1/96 (H5N1) virus: similarity of its hemagglutinin gene to those of H5N1 viruses from the 1997 outbreaks in Hong Kong. Virology, 261(1): 15-19. https://doi.org/10.1006/viro.1999.9820 (PMID: 10484749)",
    "Zielezinski A, Girgis HZ, Bernard G, Leimeister CA, Tang K, Dencker T, et al. 2019. Benchmarking of alignment-free sequence comparison methods. Genome Biology, 20: 144. https://doi.org/10.1186/s13059-019-1755-7 (PMID: 31345254)",
    "Zielezinski A, Vinga S, Almeida J, Karlowski WM 2017. Alignment-free sequence comparison: benefits, applications, and tools. Genome Biology, 18: 186. https://doi.org/10.1186/s13059-017-1319-7 (PMID: 28974235)",
]
for ref in REFS:
    p = para(ref, align=WD_ALIGN_PARAGRAPH.LEFT, size=10, after=2)
    p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.5), Cm(-0.5)

# Neutral document properties (no generator or AI provenance fields)
cp = doc.core_properties
cp.author = cp.last_modified_by = "Arli Aditya Parikesit"
import datetime
cp.created = cp.modified = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
cp.title = "Two-tier AI triage for viral gene annotation"
cp.comments = cp.keywords = cp.subject = cp.category = ""
# Drop the template's customXml part (unused bibliography sources) so the package carries no extra XML parts
for rid, rel in list(doc.part.rels.items()):
    if not rel.is_external and str(rel.target_part.partname).startswith("/customXml"):
        doc.part.rels.pop(rid)
# The submitted docx has been edited by hand in Word. Never replace it silently: write a sibling file unless --force.
# Text edits made in Word are ported above; layout edits (equation and pseudocode tables) are not, so the
# hand-edited docx stays the source of truth for layout.
if os.path.exists(OUT) and "--force" not in sys.argv:
    OUT = OUT.replace(".docx", "-rebuilt.docx")
    print("existing manuscript kept; pass --force to overwrite it")
doc.save(OUT)
print("saved", OUT)
