"""Generate all manuscript figures from results/*.json.  Navy/blue palette, Inter font."""

from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)

NAVY = "#1F4E9A"; ORANGE = "#EB6834"; TEAL = "#1BAF7A"; GOLD = "#EDA100"
DEEP = "#14325C"; INK = "#1B1F27"; INK2 = "#5B6270"; GRID = "#E3E7EE"
BLUES = ["#BFD4EE", "#8FB3E0", "#5E8FD0", "#3569B8", "#1F4E9A", "#14325C"]   # ordinal ramp light -> dark

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Inter", "Aptos", "Segoe UI", "Helvetica Neue", "Helvetica", "DejaVu Sans"], "font.size": 9.5, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
    "axes.edgecolor": INK2, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.labelcolor": INK,
    "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False, "legend.fontsize": 8.5,
    "figure.dpi": 200, "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def load(name):
    return json.load(open(os.path.join(RES, name)))


def box(ax, x, y, w, h, text, fc, ec=DEEP, fs=8.5, bold=False, tc=INK, lw=1.0, r=0.015):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x0, y0, x1, y1, color=DEEP, lw=1.0, style="-|>"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=9, color=color, lw=lw))


# --------------------------------------------------------------------------- #
# Figure 1: PAER reference architecture
# --------------------------------------------------------------------------- #
def fig_architecture():
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    box(ax, 0.02, 0.72, 0.96, 0.26, "", "#F3F6FB", ec=DEEP, lw=1.2, r=0.02)
    ax.text(0.5, 0.95, "CONTROL PLANE    policy decisions · identity context · policy versions · audit evidence",
            ha="center", va="center", fontsize=8.2, color=DEEP, fontweight="bold")
    cp = ["Identity / IAM\ncontext", "Policy store and\nversions (RBAC, ABAC)", "Decision and\naudit logs", "Revocation and\nreconciliation"]
    xs = np.linspace(0.05, 0.75, 4)
    for x, t in zip(xs, cp):
        box(ax, x, 0.75, 0.20, 0.15, t, "white", ec=DEEP, fs=7.6)
    box(ax, 0.02, 0.03, 0.96, 0.62, "", "#F8FAFD", ec=NAVY, lw=1.2, r=0.02)
    ax.text(0.5, 0.615, "DATA PLANE    retrieval and generation", ha="center", va="center", fontsize=8.2, color=NAVY, fontweight="bold")
    E = [("E1\nIngestion", "preserve and\nvalidate source\npermission labels"),
         ("E2\nIndex and\nrevocation", "propagate permission\nchanges; bound\nindex drift"),
         ("E3\nQuery-time\nfiltering", "restrict candidates\nbefore ranking, or\nover-fetch then filter"),
         ("E4\nContext\nassembly", "re-check authorization\nand provenance\nagainst live policy"),
         ("E5\nOutput\nsafeguards", "disclosure checks;\nbounded refusal")]
    xs = np.linspace(0.035, 0.795, 5)
    w = 0.17
    for i, (x, (h, b)) in enumerate(zip(xs, E)):
        box(ax, x, 0.36, w, 0.19, h, "#DCE7F6", ec=NAVY, fs=7.4, bold=True, tc=DEEP)
        box(ax, x, 0.07, w, 0.25, b, "white", ec=NAVY, fs=6.9)
        if i < 4:
            arrow(ax, x + w + 0.002, 0.455, xs[i + 1] - 0.002, 0.455, color=NAVY)
    for x_cp, x_dp in [(0.15, 0.12), (0.383, 0.31), (0.617, 0.69), (0.85, 0.88)]:
        arrow(ax, x_cp, 0.75, x_dp, 0.555, color="#8A5A2B", lw=0.9)
    ax.text(0.5, 0.675, "identity, policy decisions and audit records flow between the planes",
            ha="center", va="center", fontsize=7.4, color="#8A5A2B", style="italic")
    fig.savefig(os.path.join(OUT, "fig2_architecture.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 2: threat model
# --------------------------------------------------------------------------- #
def fig_threat():
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.02, 0.04), 0.66, 0.92, boxstyle="round,pad=0,rounding_size=0.02", fc="none", ec=DEEP, lw=1.1, ls="--"))
    ax.text(0.35, 0.93, "Enterprise trust boundary", ha="center", fontsize=8.5, color=DEEP, fontweight="bold")
    ax.add_patch(FancyBboxPatch((0.72, 0.04), 0.26, 0.92, boxstyle="round,pad=0,rounding_size=0.02", fc="none", ec="#8A5A2B", lw=1.1, ls="--"))
    ax.text(0.85, 0.93, "Model provider /\nexternal boundary", ha="center", va="top", fontsize=8.2, color="#8A5A2B", fontweight="bold")
    box(ax, 0.06, 0.66, 0.22, 0.17, "Users and agents\n(authorized and\nunauthorized)", "white", fs=7.8)
    box(ax, 0.38, 0.66, 0.26, 0.17, "PAER data plane\n(E1 to E5 enforcement)", "#DCE7F6", fs=8, bold=True, tc=DEEP)
    box(ax, 0.06, 0.40, 0.22, 0.15, "Source repositories\n(native ACLs)", "white", fs=7.8)
    box(ax, 0.38, 0.40, 0.26, 0.15, "Vector index\n(permission-labelled\nchunks)", "white", fs=7.6)
    box(ax, 0.745, 0.66, 0.21, 0.17, "LLM generation", "white", ec="#8A5A2B", fs=8)
    arrow(ax, 0.28, 0.745, 0.38, 0.745); arrow(ax, 0.17, 0.66, 0.17, 0.55, style="<|-|>")
    arrow(ax, 0.28, 0.475, 0.38, 0.475); arrow(ax, 0.51, 0.55, 0.51, 0.66); arrow(ax, 0.64, 0.745, 0.745, 0.745, color="#8A5A2B")
    T = [(0.04, "T1  Unauthorized\nretrieval, cross-\ntenant access"), (0.20, "T2  Knowledge-\nbase poisoning"),
         (0.36, "T3  Indirect prompt\ninjection via\nretrieved content"), (0.52, "T5  Enforcement\nside channels\n(result counts, scores,\nstale labels)")]
    for x, t in T:
        box(ax, x, 0.08, 0.145, 0.19, t, "#FBE9E3", ec="#B5451B", fs=6.7, tc="#7A2E12")
    box(ax, 0.745, 0.40, 0.21, 0.15, "T4  Output-side\ndisclosure (paraphrase,\nextraction)", "#FBE9E3", ec="#B5451B", fs=7.0, tc="#7A2E12")
    arrow(ax, 0.85, 0.55, 0.85, 0.66, color="#B5451B", lw=0.9)
    arrow(ax, 0.11, 0.27, 0.13, 0.40, color="#B5451B", lw=0.9)
    arrow(ax, 0.29, 0.27, 0.43, 0.40, color="#B5451B", lw=0.9)
    arrow(ax, 0.44, 0.27, 0.48, 0.66, color="#B5451B", lw=0.9)
    arrow(ax, 0.60, 0.27, 0.58, 0.40, color="#B5451B", lw=0.9)
    fig.savefig(os.path.join(OUT, "fig1_threat_model.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 3: mirrored benchmark
# --------------------------------------------------------------------------- #
def fig_mirrored():
    r = load("expA_synthetic.json")
    names = ["unfiltered", "postfilter_topk", "postfilter_overfetch5", "prefilter"]
    labels = ["Unfiltered", "Post-filter\n(top-2 only)", "Post-filter\n(over-fetch 10, keep 2)", "Pre-filter"]
    rec = [100 * r["designs"][n]["authorized"]["target_recall"] for n in names]
    un = [100 * r["designs"][n]["authorized"]["unauthorized_context_rate"] for n in names]
    ctx = [r["designs"][n]["authorized"]["mean_context_docs"] for n in names]
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    x = np.arange(4); w = 0.36
    b1 = ax.bar(x - w / 2 - 0.01, rec, w, color=NAVY, label="Authorized-target Recall@2 (%)")
    b2 = ax.bar(x + w / 2 + 0.01, un, w, color=ORANGE, label="Unauthorized context rate (%)")
    for b, v in zip(list(b1) + list(b2), rec + un):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}", ha="center", fontsize=8, color=INK)
    for xi, c in zip(x, ctx):
        ax.text(xi, 108, f"context docs = {c:.2f}", ha="center", fontsize=7.8, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_ylim(0, 118); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Percent of 900 authorized queries"); ax.yaxis.grid(True); ax.set_axisbelow(True)
    fig.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.04))
    fig.savefig(os.path.join(OUT, "fig3_mirrored.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 4: real corpus, recall vs over-fetch factor, both retrievers
# --------------------------------------------------------------------------- #
def fig_overfetch():
    r = load("expB_main.json"); s = load("expB_sentence.json")
    ms = [1, 2, 5, 10, 20, 50]
    keys = ["postfilter_topk", "postfilter_x2", "postfilter_x5", "postfilter_x10", "postfilter_x20", "postfilter_x50"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=False)
    for ax, (title, data) in zip(axes, [("Headline queries", r), ("Sentence queries", s)]):
        for retr, color, marker, lab in [("bm25", NAVY, "o", "BM25"), ("dense", TEAL, "s", "Dense (WordLlama)")]:
            rec = [100 * data[retr][k]["authorized"]["target_recall"] for k in keys]
            pre = 100 * data[retr]["prefilter"]["authorized"]["target_recall"]
            ax.plot(ms, rec, marker=marker, color=color, lw=2, ms=5.5, label=f"{lab}: post-filter, over-fetch m")
            ax.axhline(pre, color=color, lw=1.2, ls="--", alpha=0.9)
            ax.text(55, pre + 0.4, f"{lab} pre-filter {pre:.1f}", ha="right", va="bottom", fontsize=7.5, color=color)
        ax.set_xscale("log"); ax.set_xticks(ms); ax.set_xticklabels([str(m) for m in ms])
        ax.set_xlabel("Over-fetch factor m (candidates = m x k, k = 5)"); ax.set_title(title)
        ax.yaxis.grid(True); ax.set_axisbelow(True)
    axes[0].set_ylabel("Authorized-target Recall@5 (%)")
    fig.legend(loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.savefig(os.path.join(OUT, "fig4_overfetch.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 5: tenant sweep: context starvation and recall gap vs authorized fraction
# --------------------------------------------------------------------------- #
def fig_tenants():
    sw = load("expB_sweeps.json")["tenants"]
    T = [c["config"]["n_tenants"] for c in sw]
    frac = [c["authorized_fraction"]["t0_analyst"] for c in sw]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    ax = axes[0]
    for retr, color, marker, lab in [("bm25", NAVY, "o", "BM25"), ("dense", TEAL, "s", "Dense")]:
        ctx = [c[retr]["postfilter_topk"]["authorized"]["mean_context_docs"] for c in sw]
        ax.plot(T, ctx, marker=marker, color=color, lw=2, ms=5.5, label=f"{lab}: post-filter (top-k only)")
    ax.axhline(5, color=INK2, ls="--", lw=1); ax.text(10, 5.08, "k = 5 (pre-filter and over-fetch >= 10x)", ha="right", va="bottom", fontsize=7.5, color=INK2)
    ax.set_xlabel("Number of tenants"); ax.set_ylabel("Mean context documents per query"); ax.set_ylim(0, 5.6)
    ax.set_xticks(T); ax.yaxis.grid(True); ax.set_axisbelow(True); ax.legend(loc="center right", fontsize=7.8)
    ax = axes[1]
    for retr, color, marker, lab in [("bm25", NAVY, "o", "BM25"), ("dense", TEAL, "s", "Dense")]:
        gap = [100 * (c[retr]["prefilter"]["authorized"]["target_recall"] - c[retr]["postfilter_topk"]["authorized"]["target_recall"]) for c in sw]
        gap5 = [100 * (c[retr]["prefilter"]["authorized"]["target_recall"] - c[retr]["postfilter_x5"]["authorized"]["target_recall"]) for c in sw]
        ax.plot(T, gap, marker=marker, color=color, lw=2, ms=5.5, label=f"{lab}: top-k only")
        ax.plot(T, gap5, marker=marker, color=color, lw=1.4, ms=4.5, ls=":", label=f"{lab}: over-fetch 5x")
    ax.set_xlabel("Number of tenants"); ax.set_ylabel("Recall@5 lost vs. pre-filter (points)")
    ax.set_xticks(T); ax.set_ylim(-0.5, 18); ax.yaxis.grid(True); ax.set_axisbelow(True); ax.legend(fontsize=7.5, ncol=1, loc="upper left")
    for xi, f in zip(T, frac):
        axes[0].text(xi, 0.15, f"{100*f:.0f}%", ha="center", fontsize=7, color=INK2)
    axes[0].text(0.5, -0.33, "percentages: share of the corpus an analyst in tenant 0 may read", transform=axes[0].transAxes, ha="center", fontsize=7, color=INK2)
    fig.savefig(os.path.join(OUT, "fig5_tenants.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 6: existence oracle AUC vs attacker authorized fraction
# --------------------------------------------------------------------------- #
def fig_oracle():
    orc = load("expC_oracle.json")
    orc = sorted(orc, key=lambda r: r["attacker_authorized_fraction"])
    frac = [100 * r["attacker_authorized_fraction"] for r in orc]
    keys = [("postfilter_topk", "Post-filter, top-k only", BLUES[5], "o"), ("postfilter_x2", "Over-fetch 2x", BLUES[3], "s"),
            ("postfilter_x5", "Over-fetch 5x", BLUES[2], "^"), ("postfilter_x20", "Over-fetch 20x", BLUES[1], "v"),
            ("prefilter", "Pre-filter", ORANGE, "D")]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
    for ax, retr, title in [(axes[0], "bm25", "BM25"), (axes[1], "dense", "Dense (WordLlama)")]:
        for key, lab, color, marker in keys:
            auc = [r[f"{retr}_oracle_restricted"][key]["auc"] for r in orc]
            ax.plot(frac, auc, marker=marker, color=color, lw=1.8, ms=5, label=lab, alpha=0.95)
        ax.axhline(0.5, color=INK2, lw=0.8, ls="--")
        ax.set_xlabel("Share of corpus the attacker may read (%)"); ax.set_title(title)
        ax.yaxis.grid(True); ax.set_axisbelow(True); ax.set_ylim(0.45, 0.85)
    axes[0].set_ylabel("Existence-oracle AUC (result count)")
    axes[0].legend(fontsize=7.5, loc="upper left")
    fig.savefig(os.path.join(OUT, "fig6_oracle.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 7: revocation lag
# --------------------------------------------------------------------------- #
def fig_revocation():
    d = load("expD_revocation.json")["runs"]
    recons = [1.0, 15.0, 60.0, 1440.0]
    labels = ["1 min", "15 min", "60 min", "24 h"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    x = np.arange(len(recons)); w = 0.26
    for i, (mode, color, lab) in enumerate([("none", ORANGE, "No E4 re-check"), ("cached", BLUES[2], "E4 with cached policy (TTL 5 min)"), ("live", NAVY, "E4 with live policy")]):
        vals = []
        for rc in recons:
            run = [r for r in d if r["recon_interval_min"] == rc and r["e4_mode"] == mode][0]
            vals.append(run["stale_docs_per_10k_queries"])
        bars = ax.bar(x + (i - 1) * (w + 0.01), [max(v, 0.3) for v in vals], w, color=color, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, max(v, 0.3) * 1.25, "0" if v == 0 else f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", fontsize=7.5, color=INK)
    ax.set_yscale("log"); ax.set_ylim(0.25, 6000)
    ax.set_xticks(x); ax.set_xticklabels(labels); ax.set_xlabel("E2 reconciliation interval")
    ax.set_ylabel("Stale documents served per 10,000 queries (log)")
    ax.yaxis.grid(True, which="major"); ax.set_axisbelow(True); ax.legend(fontsize=7.8, loc="upper left")
    fig.savefig(os.path.join(OUT, "fig7_revocation.png"))
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Figure 8: latency and effective recall on vector indexes
# --------------------------------------------------------------------------- #
def fig_latency():
    path = os.path.join(RES, "expE_latency.json")
    if not os.path.exists(path):
        print("latency results not present; skipping fig8"); return
    d = json.load(open(path))
    sel = [r for r in d if r["n_tenants"] == 3 and r["principal"] == "t0_analyst"]
    sel.sort(key=lambda r: r["n"])
    ns = [r["n"] for r in sel]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1))
    ax = axes[0]
    series = [("flat_prefilter", "Exact: pre-filter (ID selector)", NAVY, "o", "-"),
              ("flat_postfilter_x20", "Exact: post-filter, over-fetch 20x", NAVY, "o", ":"),
              ("hnsw_prefilter", "HNSW: pre-filter (ID selector)", TEAL, "s", "-"),
              ("hnsw_postfilter_x20", "HNSW: post-filter, over-fetch 20x", TEAL, "s", ":"),
              ("hnsw_postfilter_x1", "HNSW: post-filter, top-k only", GOLD, "^", "-"),
              ("partitioned", "Partitioned exact indexes", ORANGE, "D", "-")]
    for key, lab, color, marker, ls in series:
        ax.plot(ns, [r[key]["timing_ms"]["median"] for r in sel], marker=marker, ls=ls, color=color, lw=1.8, ms=5, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xticks(ns); ax.set_xticklabels([f"{n//1000}k" for n in ns])
    ax.set_xlabel("Indexed vectors (256-d)"); ax.set_ylabel("Median latency per query (ms, log)")
    ax.yaxis.grid(True, which="major"); ax.set_axisbelow(True); ax.legend(fontsize=6.8, loc="upper left", frameon=True, framealpha=0.9, edgecolor="none")
    ax = axes[1]
    for key, lab, color, marker, ls in [("hnsw_prefilter", "HNSW: pre-filter", TEAL, "s", "-"), ("hnsw_postfilter_x20", "HNSW: over-fetch 20x", TEAL, "s", ":"),
                                        ("hnsw_postfilter_x5", "HNSW: over-fetch 5x", BLUES[2], "^", ":"), ("hnsw_postfilter_x1", "HNSW: top-k only", GOLD, "^", "-")]:
        ax.plot(ns, [100 * r[key]["recall"] for r in sel], marker=marker, ls=ls, color=color, lw=1.8, ms=5, label=lab)
    ax.set_xscale("log"); ax.set_xticks(ns); ax.set_xticklabels([f"{n//1000}k" for n in ns])
    ax.set_xlabel("Indexed vectors (256-d)"); ax.set_ylabel("Recall vs. exact pre-filtered top-5 (%)")
    ax.set_ylim(0, 105); ax.yaxis.grid(True); ax.set_axisbelow(True); ax.legend(fontsize=7.2, loc="center")
    fig.savefig(os.path.join(OUT, "fig8_latency.png"))
    plt.close(fig)


if __name__ == "__main__":
    fig_architecture(); fig_threat(); fig_mirrored(); fig_overfetch(); fig_tenants(); fig_oracle(); fig_revocation(); fig_latency()
    print("figures written to", OUT)
