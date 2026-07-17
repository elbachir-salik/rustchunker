"""Times rustchunker.chunk_files over the first --size files of a corpus and
prints a JSON line. Run in a subprocess so RAYON_NUM_THREADS (which rayon
reads once, when its global pool is first initialized) can be pinned by the
parent to force a specific core count -- used by bench_massive_parallelism.py
to measure rustchunker at 1 core vs all cores.
"""
import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import MAX_TOKENS, OVERLAP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--size", type=int, required=True)
    args = parser.parse_args()

    from rustchunker import chunk_files

    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))[: args.size]
    start = time.perf_counter()
    chunks = chunk_files(paths, max_tokens=MAX_TOKENS, overlap=OVERLAP, strategy="sentence")
    elapsed = time.perf_counter() - start

    print(json.dumps({
        "seconds": elapsed,
        "chunks": len(chunks),
        "rayon_num_threads": os.environ.get("RAYON_NUM_THREADS", "default"),
    }))


if __name__ == "__main__":
    main()
