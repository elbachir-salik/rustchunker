"""Benchmark chunking libraries against real-world documents (public-domain
books, Wikipedia articles, GitHub READMEs) instead of clean synthetic text.

Requires benchmarks/real_data/ to be populated first via
fetch_real_docs.py. If it's empty (offline, or not yet fetched), this
prints instructions and exits cleanly rather than failing -- this
benchmark is optional and network-dependent, unlike the others.

Fairness note: rustchunker's chunk_files() strips markdown/HTML syntax
automatically via its built-in readers before chunking .md/.html files.
The other libraries here (LangChain, LlamaIndex, semantic-text-splitter,
chonkie) don't include a document loader in their text-splitting API, so
they receive raw file content for .md/.html files -- in real usage you'd
normally pair them with a separate loader for those formats. So the
.md/.html portion of this benchmark reflects realistic default-usage
differences between the libraries, not a pure chunking-algorithm race on
identical input text. The .txt (Gutenberg) portion is a fair,
apples-to-apples comparison since there's no extraction step involved.
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


def find_docs(data_dir):
    paths = []
    for pattern in ("**/*.txt", "**/*.html", "**/*.md"):
        paths.extend(glob.glob(os.path.join(data_dir, pattern), recursive=True))
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "real_data"))
    parser.add_argument(
        "--out", default=os.path.join(os.path.dirname(__file__), "bench_real_docs.png")
    )
    args = parser.parse_args()

    paths = find_docs(args.data_dir)
    if not paths:
        print(
            f"No real documents found in {args.data_dir}.\n"
            f"Run `python benchmarks/fetch_real_docs.py` first (requires network access).\n"
            f"Skipping this benchmark."
        )
        sys.exit(0)

    print(f"Benchmarking on {len(paths)} real documents:")
    for p in paths:
        print(f"  {os.path.relpath(p, args.data_dir)}")

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
            "`pip install -r benchmarks/requirements-extra.txt`."
        )

    names = [r[0] for r in results]
    colors = [r[1] for r in results]
    times = [r[2] for r in results]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(names, times, color=colors)
    ax.set_ylabel("Time (seconds)")
    ax.set_title(f"Chunking {len(paths)} real-world documents")
    for bar, value in zip(bars, times):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}s", ha="center", va="bottom")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}")


if __name__ == "__main__":
    main()
