"""Head-to-head benchmark: rustchunker vs LangChain, LlamaIndex,
semantic-text-splitter, and chonkie, run over the same set of documents.

Extends bench_vs_langchain.py's two-library comparison to the broader set
of chunking libraries people ask about -- that script is left untouched so
its existing README numbers stay reproducible; this one is new/additive.
Libraries that aren't installed are skipped with a warning rather than
failing the whole run.
"""
import argparse
import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import LIBRARIES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "bench_vs_all.png"))
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))
    if not paths:
        raise SystemExit(
            f"No .txt files found in {args.data_dir}. "
            f"Run `python benchmarks/generate_test_data.py --out {args.data_dir}` first."
        )

    print(f"Benchmarking on {len(paths)} documents...")

    results = []
    for name, color, bench_fn in LIBRARIES:
        try:
            elapsed, chunk_count = bench_fn(paths)
        except ImportError as e:
            print(f"{name}: skipped (not installed: {e})")
            continue
        print(f"{name}: {elapsed:.3f}s  ({chunk_count} chunks)")
        results.append((name, color, elapsed, chunk_count))

    if len(results) < 2:
        raise SystemExit(
            "Fewer than 2 libraries available -- install extras with "
            "`pip install -r benchmarks/requirements-extra.txt` to run a real comparison."
        )

    rust_time = next((r[2] for r in results if r[0] == "rustchunker"), None)
    if rust_time:
        print("\nSpeedup vs rustchunker:")
        for name, _, elapsed, _ in results:
            if name != "rustchunker":
                print(f"  {name}: {elapsed / rust_time:.1f}x slower")

    names = [r[0] for r in results]
    colors = [r[1] for r in results]
    times = [r[2] for r in results]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(names, times, color=colors)
    ax.set_ylabel("Time (seconds)")
    ax.set_title(f"Chunking {len(paths)} documents across chunking libraries")
    for bar, value in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}s", ha="center", va="bottom")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}")


if __name__ == "__main__":
    main()
