"""Cross-platform runner: executes every experiment in order, then regenerates the figures.

Usage: python run_all.py [--quick] [--only ABCDE]
    --quick   halves the Reuters workload (for a smoke test; do not use for the paper)
    --only E  run only the listed experiments (letters A to E); figures are always regenerated

Paths are relative to the package root (the folder that contains harness/, results/, figures/).
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
ROOT = os.path.join(PKG, "data", "reuters")
RES = os.path.join(PKG, "results")
FIG = os.path.join(PKG, "figures")
PY = sys.executable


def run(label, args):
    print(f"\n== {label}", flush=True)
    t0 = time.time()
    subprocess.run(args, check=True)
    print(f"   finished in {(time.time() - t0) / 60:.1f} min", flush=True)


def describe_environment():
    import platform, json, importlib
    info = {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
            "cpu_count": os.cpu_count(), "python": platform.python_version(), "processor": platform.processor()}
    if platform.system() == "Darwin":
        try:
            info["cpu_brand"] = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
        except Exception:
            pass
    elif platform.system() == "Linux":
        try:
            for line in open("/proc/cpuinfo"):
                if line.lower().startswith(("model name", "hardware")):
                    info["cpu_brand"] = line.split(":", 1)[1].strip(); break
        except Exception:
            pass
    for mod in ["numpy", "scipy", "faiss", "qdrant_client", "wordllama", "matplotlib"]:
        try:
            m = importlib.import_module(mod); info[f"{mod}_version"] = getattr(m, "__version__", "n/a")
        except Exception:
            info[f"{mod}_version"] = "n/a"
    try:
        from importlib.metadata import version
        info["qdrant_client_version"] = version("qdrant-client"); info["wordllama_version"] = version("wordllama")
    except Exception:
        pass
    json.dump(info, open(os.path.join(RES, "environment.json"), "w"), indent=2)
    return info


def main():
    quick = "--quick" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = set(a.split("=", 1)[1].upper()) if "=" in a else set(sys.argv[sys.argv.index(a) + 1].upper())
    def wanted(stage):
        return only is None or stage in only
    if not os.path.isdir(os.path.join(ROOT, "training")):
        sys.exit(f"Reuters corpus not found at {ROOT}. Run: {PY} {os.path.join(HERE, 'get_data.py')}")
    os.makedirs(RES, exist_ok=True); os.makedirs(FIG, exist_ok=True)
    env = describe_environment()
    print(f"environment: {env.get('cpu_brand') or env.get('processor') or env['machine']}, {env['cpu_count']} cores, Python {env['python']}", flush=True)
    if wanted("A"):
      run("Experiment A: mirrored synthetic benchmark",
        [PY, "-c", f"import json, sys; sys.path.insert(0, r'{HERE}'); from paer import synthetic; "
                   f"json.dump(synthetic.run(), open(r'{os.path.join(RES, 'expA_synthetic.json')}', 'w'), indent=2)"])
    if wanted("B") or wanted("C"):
      run("Experiments B and C: Reuters-21578, two retrievers, existence oracle",
        [PY, os.path.join(HERE, "run_reuters.py"), "--root", ROOT, "--out", RES] + (["--quick"] if quick else []))
    if wanted("D"):
      run("Experiment D: revocation lag replay", [PY, os.path.join(HERE, "run_revocation.py"), "--root", ROOT, "--out", RES])
    if wanted("E"):
      run("Experiment E: vector-index cost", [PY, os.path.join(HERE, "run_latency.py"), "--root", ROOT, "--out", RES])
    run("Figures", [PY, os.path.join(HERE, "make_figures.py"), RES, FIG])
    expected = ["expA_synthetic.json", "expB_main.json", "expB_sentence.json", "expB_sweeps.json", "expB_seeds.json",
                "expC_oracle.json", "expD_revocation.json", "expE_latency.json"]
    missing = [f for f in expected if not os.path.exists(os.path.join(RES, f))]
    print("\nall experiments done." if not missing else f"\nWARNING, missing result files: {missing}")
    print(f"results: {RES}\nfigures: {FIG}")


if __name__ == "__main__":
    main()
