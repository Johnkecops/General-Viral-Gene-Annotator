#!/usr/bin/env python3
"""
Module: fig1_workflow
Purpose: Draw Figure 1, the two-tier workflow of the General Viral Gene Annotator (logic from README section 2).
Author: Dr. Arli Aditya Parikesit
Date: 2026
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 8.5})
fig, ax = plt.subplots(figsize=(7.2, 3.3), dpi=300); ax.set_xlim(0, 100); ax.set_ylim(-3, 46); ax.axis("off")

def box(x, y, w, h, t, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=fc, ec="#333333", lw=0.8))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", wrap=True)

def arr(x1, y1, x2, y2, t=""):
    ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#333333"))
    if t: ax.text((x1 + x2) / 2 + 1, (y1 + y2) / 2 + 0.8, t, fontsize=7.5, style="italic")

G, B, O, P = "#e2efda", "#ddebf7", "#fce4d6", "#ededed"
box(1, 36, 17, 7, "Query FASTA\n(any header)", P)
box(23, 36, 17, 7, "parse_fasta\n(Pseudocode 1)", P)
box(45, 36, 22, 7, "k-mer containment, k = 15\nvs 5 local references (Eq. 2)", G)
box(72, 36, 26, 7, "Reference panel (Table 1)\nNCBI Datasets, stored locally", G)
box(45, 22, 22, 8, "bio_state: header, profile,\nlength, 300 nt preview", B)
box(72, 22, 26, 8, "Tier 1: constrained choice\n6 classes → p, confidence (Eq. 5)", B)
box(72, 4, 26, 9, "Confidence ≥ 0.85:\nAuto-Processed call", G)
box(38, 4, 29, 9, "Tier 2: LLM escalation\nhomology, recombination, artefacts\n(fallback to Tier 1 call)", O)
box(1, 4, 30, 9, "Consolidated summary\n(all records via asyncio.gather)", P)
arr(18.8, 39.5, 22.2, 39.5); arr(40.8, 39.5, 44.2, 39.5); arr(71.2, 39.5, 67.8, 39.5)
arr(56, 35.2, 56, 30.8); arr(67.8, 26, 71.2, 26)
arr(85, 21.2, 85, 13.8, "yes"); arr(78, 21.2, 60, 13.8, "no")
arr(37.2, 8.5, 31.8, 8.5)
# Auto-Processed path runs under the Tier 2 box to avoid crossing it
ax.plot([85, 85, 16], [3.2, -1.5, -1.5], color="#333333", lw=0.9); arr(16, -1.5, 16, 3.2)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "results/figures/fig1_workflow.png"))
