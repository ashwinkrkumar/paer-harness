"""Download and unpack Reuters-21578 (NLTK distribution) into <package root>/data/reuters.

Usage: python get_data.py            (cross-platform, no extra dependencies)
"""

import os
import sys
import urllib.request
import zipfile

URL = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/reuters.zip"


def main():
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = os.path.join(pkg, "data")
    os.makedirs(data, exist_ok=True)
    target = os.path.join(data, "reuters")
    if os.path.isdir(os.path.join(target, "training")):
        print(f"already present: {target}")
        return
    zpath = os.path.join(data, "reuters.zip")
    print(f"downloading {URL} ...")
    urllib.request.urlretrieve(URL, zpath)
    print("unpacking ...")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(data)
    n_train = len(os.listdir(os.path.join(target, "training")))
    n_test = len(os.listdir(os.path.join(target, "test")))
    print(f"done: {target} ({n_train} training + {n_test} test files)")


if __name__ == "__main__":
    sys.exit(main())
