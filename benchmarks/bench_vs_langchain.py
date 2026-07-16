"""Head-to-head benchmark: rustchunker.chunk_files vs LangChain's
RecursiveCharacterTextSplitter, run over the same set of documents.

LangChain has no built-in multi-file batch API, so its side reads each
file and splits it sequentially in a loop -- the natural way it's used in
practice, and the comparison this library's speedup claim is about.
"""
import argparse
import glob
import os
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from rustchunker import chunk_files

MAX_TOKENS = 256
OVERLAP = 20


def word_count(text):
    return len(text.split())


def bench_rustchunker(paths):
    start = time.perf_counter()
    chunks = chunk_files(paths, max_tokens=MAX_TOKENS, overlap=OVERLAP, strategy="sentence")
    elapsed = time.perf_counter() - start
    return elapsed, len(chunks)


def bench_langchain(paths):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_TOKENS,
        chunk_overlap=OVERLAP,
        length_function=word_count,
    )
    start = time.perf_counter()
    total_chunks = 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        total_chunks += len(splitter.split_text(text))
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument(
        "--out", default=os.path.join(os.path.dirname(__file__), "bench_vs_langchain.png")
    )
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))
    if not paths:
        raise SystemExit(
            f"No .txt files found in {args.data_dir}. "
            f"Run `python benchmarks/generate_test_data.py --out {args.data_dir}` first."
        )

    print(f"Benchmarking on {len(paths)} documents...")

    rust_time, rust_chunks = bench_rustchunker(paths)
    print(f"rustchunker:  {rust_time:.3f}s  ({rust_chunks} chunks)")

    lc_time, lc_chunks = bench_langchain(paths)
    print(f"LangChain:    {lc_time:.3f}s  ({lc_chunks} chunks)")

    speedup = lc_time / rust_time if rust_time > 0 else float("inf")
    print(f"Speedup: {speedup:.1f}x")

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(["rustchunker", "LangChain"], [rust_time, lc_time], color=["#2b7a78", "#c94c4c"])
    ax.set_ylabel("Time (seconds)")
    ax.set_title(f"Chunking {len(paths)} documents ({speedup:.1f}x speedup)")
    for bar, value in zip(bars, [rust_time, lc_time]):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}s", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"Chart saved to {args.out}")


if __name__ == "__main__":
    main()
