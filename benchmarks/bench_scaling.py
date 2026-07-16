"""Benchmarks rustchunker.chunk_files scaling across different file counts."""
import argparse
import os
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from generate_test_data import generate_documents

from rustchunker import chunk_files

MAX_TOKENS = 256
OVERLAP = 20
SIZES = [100, 1000, 10000]


def ensure_pool(data_dir, count, seed=42):
    existing = (
        [f for f in os.listdir(data_dir) if f.endswith(".txt")] if os.path.isdir(data_dir) else []
    )
    if len(existing) >= count:
        return
    generate_documents(data_dir, count, seed=seed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", default=os.path.join(os.path.dirname(__file__), "data_scaling")
    )
    parser.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    parser.add_argument(
        "--out", default=os.path.join(os.path.dirname(__file__), "bench_scaling.png")
    )
    args = parser.parse_args()

    max_size = max(args.sizes)
    ensure_pool(args.data_dir, max_size)
    all_paths = sorted(
        os.path.join(args.data_dir, f) for f in os.listdir(args.data_dir) if f.endswith(".txt")
    )[:max_size]

    results = []
    for size in sorted(args.sizes):
        paths = all_paths[:size]
        start = time.perf_counter()
        chunks = chunk_files(paths, max_tokens=MAX_TOKENS, overlap=OVERLAP, strategy="sentence")
        elapsed = time.perf_counter() - start
        rate = len(chunks) / elapsed if elapsed > 0 else float("inf")
        print(f"{size:>6} files -> {elapsed:.3f}s  ({len(chunks)} chunks, {rate:.0f} chunks/s)")
        results.append((size, elapsed))

    fig, ax = plt.subplots(figsize=(5, 4))
    sizes, times = zip(*results)
    ax.plot(sizes, times, marker="o", color="#2b7a78")
    ax.set_xlabel("Number of files")
    ax.set_ylabel("Time (seconds)")
    ax.set_title("rustchunker chunk_files scaling")
    ax.set_xscale("log")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"Chart saved to {args.out}")


if __name__ == "__main__":
    main()
