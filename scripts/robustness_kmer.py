#!/usr/bin/env python3
"""
Module: robustness_kmer
Purpose: Recompute the k-mer containment matrix and simulate substitution/fragment robustness on the JEVgp2 reference.
Author: Dr. Arli Aditya Parikesit
Date: 2026
Parameters:
    - K: 15 (same default as compute_kmer_alignment in the pipeline)
    - RATES: uniform substitution rates 0 to 0.30
    - LENGTHS: fragment lengths 50 to 3000 nt
    - REPS: 50 replicates per condition, SEED 42
References:
    - Blanca A et al. 2022. J Comput Biol 29(2): 155-168 (expected k-mer survival (1-r)^k)
"""
import csv, importlib.util, os, random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The file name has spaces, so load it by path. Importing no longer opens API clients.
spec = importlib.util.spec_from_file_location("pipeline", os.path.join(ROOT, "jev sequence alignment.py"))
pipeline = importlib.util.module_from_spec(spec); spec.loader.exec_module(pipeline)
parse_fasta, kmer = pipeline.parse_fasta, pipeline.compute_kmer_alignment
refs = pipeline.load_reference_panel(ROOT)
K, RATES, LENGTHS, REPS, SEED = 15, [0, .01, .02, .05, .08, .10, .15, .20, .25, .30], [50, 100, 150, 300, 500, 1000, 3000], 50, 42
rng = random.Random(SEED)
LABEL = {"hiv": "HIV-1", "sars_cov_2": "SARS-CoV-2", "influenza_h5n1": "H5N1", "poliovirus": "PV", "jev": "JEV"}

def mutate(seq, r):
    return "".join(rng.choice([b for b in "ACGT" if b != c]) if rng.random() < r else c for c in seq)

jev = refs["jev"]
# Self-check before any output is overwritten: identical sequence must score 1, disjoint must score 0.
assert len(refs) == 5 and kmer(jev, jev) == 1.0 and kmer("A" * 40, "C" * 40) == 0.0
for d in ("results/tables", "results/figures"):
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)

# 1. Containment matrix
queries = [(f, rec["id"].split()[0], rec["sequence"]) for f in
           ["jev-gp2-gene.fa", "sars-cov-2-orf1ab-gene.fna", "H5N1-NA-gene.fna", "Polio-PVgp1-gene.fna",
            "HIV-gag-pol-gene.fna", "gene.fasta", "jev_samples.fasta"] for rec in parse_fasta(os.path.join(ROOT, f))]
with open(os.path.join(ROOT, "results/tables/containment_matrix.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["file", "id", "length"] + [LABEL[v] for v in refs])
    for f, i, s in queries:
        w.writerow([f, i, len(s)] + [round(kmer(s, r) * 100, 1) for r in refs.values()])

# 2. Substitution sweep on full JEVgp2
sub = {r: [] for r in RATES}; off = []
for r in RATES:
    for _ in range(REPS):
        q = mutate(jev, r)
        sub[r].append(kmer(q, jev))
        off.append(max(kmer(q, s) for v, s in refs.items() if v != "jev"))
# 3. Fragment-length sweep at 0% and 5% substitution
frag = {e: {L: [] for L in LENGTHS} for e in (0.0, 0.05)}
frag_off = []  # (rate, length, JEV score, best off-target score); scoring draws no random numbers, so the sweep is unchanged
for e in frag:
    for L in LENGTHS:
        for _ in range(REPS):
            st = rng.randrange(0, len(jev) - L + 1)
            q = mutate(jev[st:st + L], e)
            frag[e][L].append(kmer(q, jev))
            frag_off.append((e, L, frag[e][L][-1], max(kmer(q, s) for v, s in refs.items() if v != "jev")))

with open(os.path.join(ROOT, "results/tables/robustness_summary.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["experiment", "param", "mean", "sd", "min", "expected_(1-r)^k", "zero_score_fraction"])
    for r in RATES:
        a = np.array(sub[r]); w.writerow(["substitution", r, a.mean().round(4), a.std(ddof=1).round(4), a.min().round(4), round((1 - r) ** K, 4), (a == 0).mean()])
    for e in frag:
        for L in LENGTHS:
            a = np.array(frag[e][L]); w.writerow([f"fragment_sub{e}", L, a.mean().round(4), a.std(ddof=1).round(4), a.min().round(4), round((1 - e) ** K, 4), (a == 0).mean()])
    w.writerow(["max_offtarget_containment", "all", max(off), "", "", "", ""])

# Figure 2
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 10})
fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.9), dpi=300)
x = np.array(RATES) * 100
m = np.array([np.mean(sub[r]) for r in RATES]); sd = np.array([np.std(sub[r], ddof=1) for r in RATES])
ax[0].errorbar(x, m, yerr=sd, fmt="o", color="#1f4e79", capsize=2, label="Simulated (mean ± SD, n = 50)")
xx = np.linspace(0, 30, 200); ax[0].plot(xx, (1 - xx / 100) ** K, "--", color="#c55a11", label="Expected (1 − r)$^{15}$")
ax[0].axhline(max(off), color="grey", lw=0.8, ls=":", label="Max. off-target score")
ax[0].set_xlabel("Substitution rate r (%)"); ax[0].set_ylabel("JEV containment score C"); ax[0].set_title("(a)", loc="left")
ax[0].legend(frameon=False, fontsize=7.5)
for e, c in ((0.0, "#1f4e79"), (0.05, "#c55a11")):
    mm = [np.mean(frag[e][L]) for L in LENGTHS]; ss = [np.std(frag[e][L], ddof=1) for L in LENGTHS]
    ax[1].errorbar(LENGTHS, mm, yerr=ss, fmt="o-", color=c, capsize=2, ms=3, label=f"r = {int(e*100)}%")
ax[1].set_xscale("log"); ax[1].set_xlabel("Fragment length (nt)"); ax[1].set_ylabel("JEV containment score C"); ax[1].set_ylim(0, 1.05)
ax[1].set_title("(b)", loc="left"); ax[1].legend(frameon=False, fontsize=7.5)
for a in ax: a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(ROOT, "results/figures/fig2_robustness.png"))

# Top-hit check for the claim that JEV stays the best reference: list every query where it does not.
lost = [x for x in frag_off if x[3] >= x[2]]
sub_flat = [c for r in RATES for c in sub[r]]
print(f"substitution sweep: max off-target containment {max(off)}, "
      f"JEV not strictly top in {sum(o >= c for c, o in zip(sub_flat, off))} of {len(off)}")
print(f"fragment sweep: {len(frag_off)} queries, max off-target containment {max(x[3] for x in frag_off)}, "
      f"JEV not strictly top in {len(lost)} (all-zero profiles: {sum(1 for x in lost if x[2] == 0 and x[3] == 0)})")
for e, L in sorted({(x[0], x[1]) for x in lost}):
    print(f"   rate {e}, length {L}: {sum(1 for x in lost if (x[0], x[1]) == (e, L))} of {REPS}")
print(open(os.path.join(ROOT, "results/tables/containment_matrix.csv")).read())
print(open(os.path.join(ROOT, "results/tables/robustness_summary.csv")).read())
