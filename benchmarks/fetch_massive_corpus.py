"""Builds a massive corpus of unique, full-length real documents for the
scaling benchmark, by streaming a large real dataset (HuggingFace
`cc_news`: real news articles, hundreds to thousands of words each) and
writing each article to its own .txt file.

Streaming (the default) downloads only the shards needed for `--count`
documents rather than the whole multi-GB dataset. Requires network access
the first time. Idempotent: skips if the target directory already holds at
least `--count` files.

Unlike ag_news (very short headlines), cc_news articles are long enough to
produce several chunks each, so this exercises real per-document chunking
work, not just per-file ingestion overhead.
"""
import argparse
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000)
    parser.add_argument("--dataset", default="vblagoje/cc_news")
    parser.add_argument("--split", default="train")
    parser.add_argument("--text-column", default="text")
    parser.add_argument(
        "--min-chars", type=int, default=500,
        help="skip documents shorter than this, so the corpus is substantial",
    )
    parser.add_argument(
        "--no-streaming", action="store_true",
        help="download the full dataset instead of streaming shards on demand",
    )
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "massive_data"))
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    existing = sum(1 for f in os.listdir(args.out) if f.endswith(".txt"))
    if existing >= args.count:
        print(f"{existing:,} files already present in {args.out} (>= {args.count:,}); nothing to do.")
        return

    from datasets import load_dataset

    print(f"Streaming {args.dataset} [{args.split}] ...")
    ds = load_dataset(args.dataset, split=args.split, streaming=not args.no_streaming)

    written = 0
    for ex in ds:
        if written >= args.count:
            break
        text = ex.get(args.text_column) or ""
        text = text.strip()
        if len(text) < args.min_chars:
            continue
        path = os.path.join(args.out, f"doc_{written:06d}.txt")
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        written += 1
        if written % 10_000 == 0:
            print(f"  {written:,} / {args.count:,}")

    total = sum(1 for f in os.listdir(args.out) if f.endswith(".txt"))
    print(f"Done. {total:,} files in {args.out}")
    if total < args.count:
        print(f"NOTE: dataset yielded only {total:,} docs (after the {args.min_chars}-char filter).")


if __name__ == "__main__":
    main()
