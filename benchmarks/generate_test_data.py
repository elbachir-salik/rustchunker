"""Generates synthetic .txt documents for benchmarking rustchunker."""
import argparse
import os
import random

WORDS = (
    "the quick brown fox jumps over lazy dog while sun sets slowly behind "
    "distant mountains and travelers continue their journey through forest "
    "paths lined with ancient trees whose branches reach toward cloudy sky "
    "researchers study complex systems that govern behavior of large networks "
    "engineers build scalable software solving problems for millions of users "
    "scientists discover patterns hidden within vast oceans of raw data points"
).split()

SENTENCE_ENDERS = [".", ".", ".", "!", "?"]


def make_sentence(rng, min_words=6, max_words=16):
    n = rng.randint(min_words, max_words)
    words = [rng.choice(WORDS) for _ in range(n)]
    words[0] = words[0].capitalize()
    return " ".join(words) + rng.choice(SENTENCE_ENDERS)


def make_paragraph(rng, sentences=5):
    return " ".join(make_sentence(rng) for _ in range(sentences))


def make_document(rng, paragraphs=6):
    return "\n\n".join(make_paragraph(rng) for _ in range(paragraphs))


def generate_documents(out_dir, count, paragraphs=6, seed=42):
    rng = random.Random(seed)
    os.makedirs(out_dir, exist_ok=True)
    for i in range(count):
        doc = make_document(rng, paragraphs)
        path = os.path.join(out_dir, f"doc_{i:05d}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--paragraphs", type=int, default=6)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_documents(args.out, args.count, args.paragraphs, args.seed)
    print(f"Generated {args.count} documents in {args.out}")


if __name__ == "__main__":
    main()
