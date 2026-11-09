"""Load harness results and expose every number used in the manuscript."""

import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.environ.get("PAER_RESULTS", os.path.join(ROOT, "results"))


def load(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


A = load("expA_synthetic.json")
B = load("expB_main.json")
BS = load("expB_sentence.json")
SW = load("expB_sweeps.json")
SEEDS = load("expB_seeds.json")
ORC = load("expC_oracle.json")
D = load("expD_revocation.json")
E = load("expE_latency.json")


def pct(x, nd=1):
    return f"{100 * x:.{nd}f}"


def f(x, nd=2):
    return f"{x:.{nd}f}"


# ---------------- Experiment A ----------------
def a_row(name, key="authorized"):
    return A["designs"][name][key]


A_DESIGNS = [("unfiltered", "Unfiltered"), ("postfilter_topk", "Post-filter, top-2 only"),
             ("postfilter_overfetch5", "Post-filter, over-fetch 10, keep 2"), ("prefilter", "Pre-filter")]

# ---------------- Experiment B ----------------
B_KEYS = [("unfiltered", "D0 unfiltered", "D0"), ("postfilter_topk", "D1 top-k only", "D1"),
          ("postfilter_x2", "D2 over-fetch 2x", "D2 (m = 2)"), ("postfilter_x5", "D2 over-fetch 5x", "D2 (m = 5)"),
          ("postfilter_x10", "D2 over-fetch 10x", "D2 (m = 10)"), ("postfilter_x20", "D2 over-fetch 20x", "D2 (m = 20)"),
          ("postfilter_x50", "D2 over-fetch 50x", "D2 (m = 50)"), ("prefilter", "D3 pre-filter", "D3")]


def b(retr, key, metric, src=None, part="authorized"):
    src = src or B
    return src[retr][key][part][metric]


def seed_stats(retr, key, metric="target_recall"):
    vals = [s[retr][key]["authorized"][metric] for s in SEEDS]
    return float(np.mean(vals)), float(np.std(vals, ddof=1))


def sweep_rows(which):
    return SW[which]


# ---------------- Experiment C ----------------
def oracle_sorted():
    return sorted(ORC, key=lambda r: r["attacker_authorized_fraction"])


# ---------------- Experiment D ----------------
def d_run(recon, mode):
    return [r for r in D["runs"] if r["recon_interval_min"] == recon and r["e4_mode"] == mode][0]


# ---------------- Experiment E ----------------
def e_rows(n_tenants=3, principal="t0_analyst"):
    if E is None:
        return []
    rows = [r for r in E if r["n_tenants"] == n_tenants and r["principal"] == principal]
    return sorted(rows, key=lambda r: r["n"])


if __name__ == "__main__":
    print("A unfiltered recall", pct(a_row("unfiltered")["target_recall"]))
    print("B bm25 prefilter recall", pct(b("bm25", "prefilter", "target_recall")))
    print("seeds", seed_stats("bm25", "prefilter"))
    print("E rows", len(e_rows()))


ENV = load("environment.json")


def environment_sentence():
    """Human-readable description of the machine the timing figures came from."""
    if not ENV:
        return "a two-core x86-64 Linux virtual machine"
    brand = ENV.get("cpu_brand") or ENV.get("processor") or ENV.get("machine")
    system = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}.get(ENV.get("system"), ENV.get("system"))
    cores = ENV.get("cpu_count")
    article = "an" if str(cores).startswith(("8", "11", "18")) else "a"
    return f"{article} {cores}-core {brand} machine running {system}"


def python_sentence():
    if not ENV:
        return "Python 3.13"
    return f"Python {ENV['python']}"


def package_sentence():
    if not ENV:
        return "NumPy, SciPy, FAISS (faiss-cpu 1.15), the Qdrant client (1.20, local mode), and WordLlama (0.4)"
    return (f"NumPy {ENV.get('numpy_version','')}, SciPy {ENV.get('scipy_version','')}, FAISS (faiss-cpu {ENV.get('faiss_version','')}), "
            f"the Qdrant client ({ENV.get('qdrant_client_version','')}, local mode), and WordLlama ({ENV.get('wordllama_version','')})")
