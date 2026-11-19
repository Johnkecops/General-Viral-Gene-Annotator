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
# Top hit exactly as the pipeline reports it (most shared k-mers, best strand, "none" below MIN_SHARED_KMERS),
# and the plain argmax it replaced (any shared k-mer wins), to show what the minimum changes.
def top_hit(q):
    shared = {v: pipeline.kmer_containment(q, s)[0] for v, s in refs.items()}
    best = max(shared, key=shared.get)
    return pipeline.top_alignment_hit(shared), (best if shared[best] > 0 else "none")
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
sub = {r: [] for r in RATES}; off = []; sub_hits = []
for r in RATES:
    for _ in range(REPS):
        q = mutate(jev, r)
        sub[r].append(kmer(q, jev))
        off.append(max(kmer(q, s) for v, s in refs.items() if v != "jev"))
        sub_hits.append((r, *top_hit(q)))
# 3. Fragment-length sweep at 0% and 5% substitution
frag = {e: {L: [] for L in LENGTHS} for e in (0.0, 0.05)}
frag_off = []  # (rate, length, JEV score, best off-target score, top hit); scoring draws no random numbers
for e in frag:
    for L in LENGTHS:
        for _ in range(REPS):
            st = rng.randrange(0, len(jev) - L + 1)
            q = mutate(jev[st:st + L], e)
            frag[e][L].append(kmer(q, jev))
            frag_off.append((e, L, frag[e][L][-1], max(kmer(q, s) for v, s in refs.items() if v != "jev"), *top_hit(q)))

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

# Top-hit check: how often the reported top hit is JEV, "none" (abstain), or a wrong virus.
def tally(rows):
    out = {}
    for key, hit in rows:
        out.setdefault(key, {"jev": 0, "none": 0, "other": 0})[hit if hit in ("jev", "none") else "other"] += 1
    return out
print(f"substitution sweep: max off-target containment {max(off)}")
for r, c in tally([(x[0], x[1]) for x in sub_hits]).items():
    if c["jev"] < REPS: print(f"   rate {r}: top hit {c}")
print(f"fragment sweep: {len(frag_off)} queries, max off-target containment {max(x[3] for x in frag_off)}")
for (e, L), c in tally([((x[0], x[1]), x[4]) for x in frag_off]).items():
    if c["jev"] < REPS: print(f"   rate {e}, length {L}: top hit {c}")
for name, i, j in (("with", 1, 4), ("without", 2, 5)):
    wrong = [x for x in sub_hits if x[i] not in ("jev", "none")] + [x for x in frag_off if x[j] not in ("jev", "none")]
    print(f"wrong-virus top hits {name} the {pipeline.MIN_SHARED_KMERS}-k-mer minimum, "
          f"{len(sub_hits) + len(frag_off)} simulated queries: {len(wrong)} {wrong}")
