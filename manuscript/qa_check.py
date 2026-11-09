"""Quality checks on the rendered manuscript text."""
import re, subprocess, sys

import os
pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "PAER_JCP_manuscript.pdf")
text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
problems = []
if "—" in text:
    problems.append(f"em dashes found: {text.count('—')}")
for ph in ["TODO", "XXX", "{", "}", "nan", "None"]:
    if ph in text.replace("[REPOSITORY URL AND ZENODO DOI TO BE INSERTED BY THE AUTHOR BEFORE SUBMISSION]", ""):
        # braces may appear legitimately in set notation; report count only
        problems.append(f"token '{ph}' appears {text.count(ph)} times (inspect)")
figs = sorted(set(int(m) for m in re.findall(r"Figure (\d+)", text)))
tabs = sorted(set(int(m) for m in re.findall(r"Table (\d+)", text)))
caps_f = sorted(set(int(m) for m in re.findall(r"^\s*Figure (\d+)\.", text, re.M)))
caps_t = sorted(set(int(m) for m in re.findall(r"^\s*Table (\d+)\.", text, re.M)))
print("figures referenced:", figs, "captions:", caps_f)
print("tables referenced:", tabs, "captions:", caps_t)
refs = sorted(set(int(n) for grp in re.findall(r"\[([\d,–\s]+)\]", text) for part in grp.split(",") for n in re.findall(r"\d+", part)))
print("max citation number:", max(refs) if refs else None)
body = text.split("References")[0]
print("words before References:", len(body.split()))
print("abstract words:", len(re.search(r"Abstract:(.*?)Keywords:", text, re.S).group(1).split()))
print("PROBLEMS:" if problems else "no problems", problems)
