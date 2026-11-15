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
- **🎯 Clean sentence boundaries** — the `sentence` strategy splits only on real Unicode sentence ends: 100% clean boundaries in testing, vs 6–99% for the others. *(With `overlap > 0`, chunk **heads** gain a few words of leading context that may begin mid-sentence — see [Strategies](#-strategies).)*
- **🪶 Light** — low memory, and zero Python runtime dependencies.
- **🔌 Drop-in** — `pip install`, two lines of code, fully typed.
- **📄 Reads your files** — `.txt`, `.md`, `.html`, `.pdf`, and Word `.docx` extracted for you.

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
    ["doc1.md", "doc2.txt", "doc3.html", "report.pdf", "report.docx"],
    max_tokens=256,
    overlap=20,
    strategy="sentence",
    on_error="skip",   # drop unreadable files instead of aborting the batch
)
```

Text and markup files must be UTF-8 (a leading byte-order mark is stripped).
PDF and DOCX files are read as binary documents. By default
`chunk_files` raises on the first file it can't read or parse; pass
`on_error="skip"` to drop failing files and keep the rest — handy when ingesting
a large, messy corpus where one bad file shouldn't sink the whole run.

Each `Chunk` has `.text`, `.start` / `.end` (character offsets into the input
string for `chunk()`, or the extracted text for `chunk_files()`), `.index`, and `.metadata`
(`source_file`, `total_chunks`, `strategy_used`, …).

### PDF and Word support

`chunk_files` extracts embedded PDF text and the main body of Word `.docx`
files, including paragraphs and tables. Extraction runs in Rust with the
existing parallel file processing; no Python packages or external converters
are required. Extensions are case-insensitive.

- Scanned/image-only PDFs need OCR first. PDFs with no extractable text raise
  `ValueError`, or are omitted with `on_error="skip"`.
- Encrypted PDFs are unsupported; decrypt them before ingestion. Complex PDF
  layouts may not preserve visual reading order or table structure.
- DOCX compatibility alternatives are extracted once: the first `Choice`, or
  `Fallback` if there is no choice. This is text extraction, not Word layout rendering.
- DOCX headers, footers, footnotes, comments and embedded images are not extracted.
  The main document XML is limited to 64 MiB after decompression.
- Legacy Word `.doc` files are unsupported; convert them to `.docx` first.
- Offsets refer to extracted text, not the original PDF/DOCX bytes or page
  coordinates. Chunks do not include page numbers.
- Malformed PDF/DOCX files raise `ValueError`; missing/unreadable files raise
  `OSError`. Both are omitted with `on_error="skip"`.

The published plain-text benchmarks do not measure PDF/DOCX extraction speed.

## 🧠 Strategies

| `strategy` | what it does |
|---|---|
| `"fixed"` | every N tokens, exact — the fast baseline |
| `"sentence"` | splits on real sentence boundaries (Unicode-aware; keeps "Dr." and "U.S.A." intact), never exceeding `max_tokens` |

`overlap` shares N trailing tokens between consecutive chunks — respecting word
boundaries — so context isn't lost at the seams. With the `sentence` strategy
this leading context is taken at word granularity, so an overlapped chunk's
head can begin part-way through a sentence (its interior boundaries stay
clean). *(More strategies on the way.)*

> **What "token" means here:** a token is a **whitespace-delimited word**, not
> a model / BPE token (tiktoken, SentencePiece, …). `max_tokens` caps words per
> chunk. Word count only approximates an embedder's token budget (roughly
> ~0.75×), so leave headroom when sizing chunks against a hard model limit.

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
git clone https://github.com/elbachir-salik/rustchunker
cd rustchunker
maturin develop --release   # requires Rust + maturin; always use --release for real speed
pytest
```

## Release checks

Run from an activated virtual environment with maturin and pytest installed:

```bash
cargo fmt --all -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked --all-targets
maturin develop --release --locked
python -m pytest -q tests
```

CI also tests the Rust core on Linux, Windows, and macOS, checks the minimum
Rust version (1.83), tests the Linux wheel on the oldest and newest Python,
and builds and tests the source archive before publishing. Maturin enables
PyO3's extension-module feature through `pyproject.toml`; plain Cargo tests
leave it disabled so test executables can link to Python on Unix.

Correctness tests do not measure speed. Before a release, compare runtime
and whole-process peak memory with the previous version on the same machine
and corpus, using release builds and the scripts in [BENCHMARKS.md](BENCHMARKS.md).


## 📄 License

Dual-licensed under **MIT** or **Apache-2.0**, at your option.
