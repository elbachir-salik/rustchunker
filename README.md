<div align="center">

# ⚡ rustchunker

### Chunk 100,000 documents in ~13 seconds.

A blazing-fast document chunker for RAG pipelines.<br/>
**Rust core · Python API · parallel across every CPU core.**

![Python](https://img.shields.io/badge/python-3.9+-blue?logo=python&logoColor=white)
![Rust](https://img.shields.io/badge/core-Rust-orange?logo=rust)
![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)
[![PyPI](https://img.shields.io/pypi/v/rustchunker)](https://pypi.org/project/rustchunker/)

</div>

---

Splitting documents into chunks is step one of every RAG pipeline. rustchunker
does it with a Rust core and real multi-core parallelism — so a corpus that
takes LangChain or LlamaIndex **minutes** takes rustchunker **seconds**.

| Chunking 100,000 real documents | Time |
|---|---|
| **rustchunker** ⚡ | **12.7s** |
| semantic-text-splitter | 90.6s |
| chonkie | 108.7s |
| LangChain | 113.5s |
| LlamaIndex | 158.4s |

<sub>12 cores · `cc_news` corpus · `sentence` strategy. Full methodology, a
five-library comparison, memory, correctness, and the results that *don't*
favour us → **[BENCHMARKS.md](BENCHMARKS.md)**.</sub>

![Scaling across libraries](benchmarks/bench_massive_scaling.png)

## ✨ Why rustchunker

- **⚡ Built for scale** — ~17–24k chunks/sec, and it pulls *further* ahead as the corpus grows.
- **🧵 Actually parallel** — `chunk_files` fans your whole corpus across every core with `rayon`, GIL released. Pure-Python libraries can't (they're stuck paying multiprocessing overhead).
- **🎯 Never splits mid-sentence** — 100% clean sentence boundaries in testing, vs 6–99% for the others.
- **🪶 Light** — low memory, and zero Python runtime dependencies.
- **🔌 Drop-in** — `pip install`, two lines of code, fully typed.
- **📄 Reads your files** — `.txt`, `.md`, and `.html` parsed and stripped for you.

## 📦 Install

```bash
pip install rustchunker
```

## 🚀 Quickstart

```python
from rustchunker import chunk, chunk_files

# One string
for c in chunk("Your long document…", max_tokens=256, overlap=20, strategy="sentence"):
    print(c.index, c.text)

# Thousands of files, in parallel across all cores
chunks = chunk_files(
    ["doc1.md", "doc2.txt", "doc3.html"],
    max_tokens=256,
    overlap=20,
    strategy="sentence",
)
```

Each `Chunk` has `.text`, `.start` / `.end` (character offsets into the source
document, so `source[c.start:c.end] == c.text`), `.index`, and `.metadata`
(`source_file`, `total_chunks`, `strategy_used`, …).

## 🧠 Strategies

| `strategy` | what it does |
|---|---|
| `"fixed"` | every N tokens, exact — the fast baseline |
| `"sentence"` | splits on real sentence boundaries (Unicode-aware; keeps "Dr." and "U.S.A." intact), never exceeding `max_tokens` |

`overlap` shares N trailing tokens between consecutive chunks — respecting word
boundaries — so context isn't lost at the seams. *(More strategies on the way.)*

## 🎯 When to use it

**Great fit:** ingesting a corpus — a knowledge base, document store, or crawl
of **many** files. That's where the parallelism pays off, and it's the common
RAG ingestion case.

**Honest caveat:** for a *single* document, rustchunker is about as fast as
LangChain — the win is at corpus scale, not per call. The full breakdown of
"how much is the Rust core vs just using all cores" is in
**[BENCHMARKS.md](BENCHMARKS.md)**, decomposed and measured.

## ⚙️ How it works

The chunking runs in Rust via [PyO3](https://pyo3.rs), and `chunk_files`
processes files in parallel with [`rayon`](https://docs.rs/rayon) while
**releasing the Python GIL** — so other threads keep running and you get true
multi-core throughput a pure-Python library can't reach without the overhead of
spawning processes.

## 🛠️ Building from source

```bash
git clone https://github.com/salik-elbachir/rustchunker
cd rustchunker
maturin develop --release   # requires Rust + maturin; always use --release for real speed
pytest
```

## 📄 License

Dual-licensed under **MIT** or **Apache-2.0**, at your option.
