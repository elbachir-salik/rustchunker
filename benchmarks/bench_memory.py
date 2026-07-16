"""Peak memory usage comparison across chunking libraries.

Runs each library's chunking pass in its own subprocess (via
_memory_runner.py) to avoid one library's residual allocations or import
overhead polluting the next library's measurement.

Two numbers per library:
- tracemalloc peak: Python-heap allocations only. For rustchunker this
  counts the final Chunk.text strings (real CPython str objects created at
  the PyO3 boundary) but NOT any transient Rust-side buffers freed before
  returning to Python -- so it understates rustchunker's true peak relative
  to pure-Python libraries whose intermediate data structures are all
  Python objects tracemalloc can see. Finer-grained, but partial.
- RSS peak (via psutil): whole-process peak resident memory, covering both
  Python and native allocations. This is the complete picture and the
  number to trust for a fair cross-language comparison.
"""
import argparse
import json
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import LIBRARIES

RUNNER = os.path.join(os.path.dirname(__file__), "_memory_runner.py")


def run_one(library, data_dir):
    result = subprocess.run(
        [sys.executable, RUNNER, "--library", library, "--data-dir", data_dir],
        capture_output=True,
        text=True,
    )
    lines = result.stdout.strip().splitlines()
    if not lines:
        return {"library": library, "error": result.stderr.strip() or "no output"}
    return json.loads(lines[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "bench_memory.png"))
    args = parser.parse_args()

    results = []
    for name, color, _ in LIBRARIES:
        data = run_one(name, args.data_dir)
        if "error" in data:
            print(f"{name}: skipped ({data['error']})")
            continue
        print(
            f"{name}: tracemalloc={data['tracemalloc_peak_mb']:.1f}MB  "
            f"RSS={data['rss_peak_mb']:.1f}MB  ({data['chunk_count']} chunks)"
        )
        results.append((name, color, data["tracemalloc_peak_mb"], data["rss_peak_mb"]))

    if not results:
        raise SystemExit("No libraries produced results.")

    names = [r[0] for r in results]
    colors = [r[1] for r in results]
    tracemalloc_vals = [r[2] for r in results]
    rss_vals = [r[3] for r in results]

    x = list(range(len(names)))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(
        [i - width / 2 for i in x],
        tracemalloc_vals,
        width,
        label="tracemalloc (Python-heap only)",
        color=colors,
        alpha=0.5,
    )
    ax.bar([i + width / 2 for i in x], rss_vals, width, label="RSS (whole process)", color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Peak memory (MB)")
    ax.set_title("Peak memory usage by chunking library")
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}")


if __name__ == "__main__":
    main()
