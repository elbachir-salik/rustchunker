"""Runs ONE library's chunking pass in an isolated process and prints its
peak memory usage as a JSON line. Invoked as a subprocess by
bench_memory.py so that one library's residual allocations or import
overhead can't pollute the next library's measurement.
"""
import argparse
import glob
import json
import os
import sys
import tracemalloc

import psutil

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import LIBRARIES

BENCH_FNS = {name: fn for name, _, fn in LIBRARIES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, choices=sorted(BENCH_FNS))
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))
    if not paths:
        print(json.dumps({"library": args.library, "error": f"no .txt files in {args.data_dir}"}))
        sys.exit(1)

    process = psutil.Process()
    tracemalloc.start()
    try:
        _, chunk_count = BENCH_FNS[args.library](paths)
    except ImportError as e:
        print(json.dumps({"library": args.library, "error": f"not installed: {e}"}))
        sys.exit(0)

    _, tracemalloc_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    mem_info = process.memory_info()
    # peak_wset (Windows-specific) is the true peak; rss is a fallback for
    # other platforms, where it reflects current, not necessarily peak, RSS.
    rss_peak = getattr(mem_info, "peak_wset", None) or mem_info.rss

    print(json.dumps({
        "library": args.library,
        "tracemalloc_peak_mb": tracemalloc_peak / (1024 * 1024),
        "rss_peak_mb": rss_peak / (1024 * 1024),
        "chunk_count": chunk_count,
    }))


if __name__ == "__main__":
    main()
