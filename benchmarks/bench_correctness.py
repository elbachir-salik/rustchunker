"""Chunk boundary correctness comparison: does each library's chunk end
actually land on a real sentence boundary, or does it cut mid-sentence?

Uses rustchunker's own (already-tested) Unicode sentence-boundary
detection as the ground-truth oracle -- exposed internally as
rustchunker._rustchunker.sentence_boundaries (not part of the public
chunking API) -- rather than introducing a second, possibly-disagreeing
"what counts as a sentence" implementation just for this benchmark.

Other libraries only return chunk text, not offsets, so each chunk's end
position is relocated in the original document via forward substring
search. If a chunk's text can't be located at all (e.g. after whitespace
normalization), it's counted as "unlocatable" rather than silently
mis-scored as broken or clean.
"""
import argparse
import bisect
import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from _adapters import MAX_TOKENS, OVERLAP, word_count

from rustchunker import chunk
from rustchunker._rustchunker import sentence_boundaries


def chunks_langchain(text):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_TOKENS, chunk_overlap=OVERLAP, length_function=word_count
    )
    return splitter.split_text(text)


def chunks_llama_index(text):
    from llama_index.core.node_parser import SentenceSplitter

    splitter = SentenceSplitter(chunk_size=MAX_TOKENS, chunk_overlap=OVERLAP, tokenizer=str.split)
    return splitter.split_text(text)


def chunks_semantic_text_splitter(text):
    from semantic_text_splitter import TextSplitter

    splitter = TextSplitter.from_callback(word_count, MAX_TOKENS, overlap=OVERLAP)
    return splitter.chunks(text)


def chunks_chonkie(text):
    from chonkie import TokenChunker

    chunker = TokenChunker(tokenizer="word", chunk_size=MAX_TOKENS, chunk_overlap=OVERLAP)
    return [c.text for c in chunker(text)]


TEXT_CHUNKERS = [
    ("LangChain", chunks_langchain),
    ("LlamaIndex", chunks_llama_index),
    ("semantic-text-splitter", chunks_semantic_text_splitter),
    ("chonkie", chunks_chonkie),
]


def is_clean_boundary(end, sorted_ground_truth_ends, text_len, text):
    if end == text_len:
        return True
    # Nearest ground-truth end at or after `end`, and the one just before it
    # -- the real boundary is one of these two; anything else is too far.
    i = bisect.bisect_left(sorted_ground_truth_ends, end)
    candidates = sorted_ground_truth_ends[max(0, i - 1) : i + 1]
    for ge in candidates:
        lo, hi = (end, ge) if end <= ge else (ge, end)
        if text[lo:hi].strip() == "":
            return True
    return False


def score_document(text):
    ground_truth_ends = sorted(e for _, e in sentence_boundaries(text))
    text_len = len(text)
    results = {}

    rust_chunks = chunk(text, max_tokens=MAX_TOKENS, overlap=OVERLAP, strategy="sentence")
    clean = sum(
        1 for c in rust_chunks if is_clean_boundary(c.end, ground_truth_ends, text_len, text)
    )
    results["rustchunker"] = (clean, len(rust_chunks) - clean, 0, len(rust_chunks))

    for name, fn in TEXT_CHUNKERS:
        try:
            chunk_texts = fn(text)
        except ImportError:
            continue
        clean = broken = unlocatable = 0
        search_from = 0
        for ct in chunk_texts:
            stripped = ct.strip()
            if not stripped:
                unlocatable += 1
                continue
            idx = text.find(stripped, search_from)
            if idx == -1:
                idx = text.find(stripped)  # retry in case ordering assumption failed
            if idx == -1:
                unlocatable += 1
                continue
            end = idx + len(stripped)
            search_from = idx
            if is_clean_boundary(end, ground_truth_ends, text_len, text):
                clean += 1
            else:
                broken += 1
        results[name] = (clean, broken, unlocatable, len(chunk_texts))

    return results


def accumulate(paths, totals, label):
    print(f"\nScoring {len(paths)} {label} document(s)...")
    for p in paths:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for name, (clean, broken, unlocatable, total) in score_document(text).items():
            acc = totals.setdefault(name, [0, 0, 0, 0])
            acc[0] += clean
            acc[1] += broken
            acc[2] += unlocatable
            acc[3] += total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument(
        "--real-data-dir", default=os.path.join(os.path.dirname(__file__), "real_data")
    )
    parser.add_argument(
        "--out", default=os.path.join(os.path.dirname(__file__), "bench_correctness.png")
    )
    parser.add_argument(
        "--synthetic-limit", type=int, default=50, help="cap synthetic docs scored, for speed"
    )
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.data_dir, "*.txt")))[: args.synthetic_limit]
    real_paths = []
    if os.path.isdir(args.real_data_dir):
        for pattern in ("**/*.txt", "**/*.html", "**/*.md"):
            real_paths.extend(glob.glob(os.path.join(args.real_data_dir, pattern), recursive=True))

    if not paths and not real_paths:
        raise SystemExit(
            "No documents found -- run generate_test_data.py and/or fetch_real_docs.py first."
        )

    totals = {}
    if paths:
        accumulate(paths, totals, "synthetic")
    if real_paths:
        accumulate(real_paths, totals, "real")
    else:
        print("\n(no real documents found -- run fetch_real_docs.py for a more meaningful signal)")

    print(f"\n{'Library':<25}{'Clean %':>10}{'Broken %':>10}{'Unlocatable %':>15}{'Chunks':>10}")
    names, clean_pcts, broken_pcts, unlocatable_pcts = [], [], [], []
    for name, (clean, broken, unlocatable, total) in totals.items():
        if total == 0:
            continue
        clean_pct = 100 * clean / total
        broken_pct = 100 * broken / total
        unlocatable_pct = 100 * unlocatable / total
        print(f"{name:<25}{clean_pct:>9.1f}%{broken_pct:>9.1f}%{unlocatable_pct:>14.1f}%{total:>10}")
        names.append(name)
        clean_pcts.append(clean_pct)
        broken_pcts.append(broken_pct)
        unlocatable_pcts.append(unlocatable_pct)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, clean_pcts, label="clean", color="#2b7a78")
    ax.bar(names, broken_pcts, bottom=clean_pcts, label="broken (mid-sentence)", color="#c94c4c")
    bottoms = [c + b for c, b in zip(clean_pcts, broken_pcts)]
    ax.bar(names, unlocatable_pcts, bottom=bottoms, label="unlocatable", color="#999999")
    ax.set_ylabel("% of chunks")
    ax.set_title("Chunk boundary correctness")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    print(f"\nChart saved to {args.out}")


if __name__ == "__main__":
    main()
