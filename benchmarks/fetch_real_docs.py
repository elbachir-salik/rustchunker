"""Downloads a small curated set of real-world documents for benchmarking
chunking quality/speed against messy, real text rather than clean
synthetic generated prose.

Requires network access. Skips (doesn't crash) on any individual download
failure -- a missing document just means that file is absent from the
benchmark, not a hard error, since some of these sources (Wikipedia's API,
GitHub raw content) can be flaky or rate-limited.
"""
import argparse
import os
import urllib.request

REAL_DOCS = [
    # Gutenberg: public-domain books, .txt -- exercises the text reader.
    ("https://www.gutenberg.org/cache/epub/1342/pg1342.txt", "gutenberg/pride_and_prejudice.txt"),
    ("https://www.gutenberg.org/cache/epub/1661/pg1661.txt", "gutenberg/sherlock_holmes.txt"),
    ("https://www.gutenberg.org/cache/epub/84/pg84.txt", "gutenberg/frankenstein.txt"),
    # Wikipedia: stable versioned HTML REST endpoint -- exercises the HTML reader.
    (
        "https://en.wikipedia.org/api/rest_v1/page/html/Artificial_intelligence",
        "wikipedia/artificial_intelligence.html",
    ),
    (
        "https://en.wikipedia.org/api/rest_v1/page/html/Rust_(programming_language)",
        "wikipedia/rust_programming_language.html",
    ),
    # Popular GitHub READMEs, raw markdown -- exercises the markdown reader.
    ("https://raw.githubusercontent.com/facebook/react/main/README.md", "readme/react.md"),
    ("https://raw.githubusercontent.com/microsoft/vscode/main/README.md", "readme/vscode.md"),
    ("https://raw.githubusercontent.com/tensorflow/tensorflow/master/README.md", "readme/tensorflow.md"),
]


def fetch(url, out_path, timeout=15, force=False):
    if os.path.exists(out_path) and not force:
        print(f"skip (already exists): {out_path}")
        return True
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rustchunker-benchmark/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"fetched: {out_path} ({len(data)} bytes)")
        return True
    except Exception as e:
        print(f"WARNING: failed to fetch {url}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "real_data"))
    parser.add_argument(
        "--force", action="store_true", help="re-download even if the file already exists"
    )
    args = parser.parse_args()

    ok = 0
    for url, rel_path in REAL_DOCS:
        out_path = os.path.join(args.out, rel_path)
        if fetch(url, out_path, force=args.force):
            ok += 1

    print(f"\n{ok}/{len(REAL_DOCS)} documents available in {args.out}")
    if ok == 0:
        raise SystemExit("No documents could be fetched -- check network access.")


if __name__ == "__main__":
    main()
