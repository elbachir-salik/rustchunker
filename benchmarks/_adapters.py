"""Shared per-library benchmark adapters for the multi-library comparisons.

Each bench_<library>(paths) function reads and chunks every file in `paths`
sequentially (the natural way these libraries are used -- none of them has
a built-in parallel multi-file API except rustchunker) and returns
(elapsed_seconds, total_chunk_count). Each library is imported inside its
own function body, so a missing optional dependency only affects that one
function -- callers should catch ImportError per library and skip it.

All libraries are configured with an equivalent word-count token budget
(MAX_TOKENS/OVERLAP) rather than each library's own default tokenizer, so
the comparison is apples-to-apples on chunk size rather than comparing
different units.
"""
import time

MAX_TOKENS = 256
OVERLAP = 20


def word_count(text):
    return len(text.split())


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def bench_rustchunker(paths):
    from rustchunker import chunk_files

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
        total_chunks += len(splitter.split_text(_read(path)))
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


def bench_llama_index(paths):
    from llama_index.core.node_parser import SentenceSplitter

    splitter = SentenceSplitter(
        chunk_size=MAX_TOKENS,
        chunk_overlap=OVERLAP,
        tokenizer=str.split,
    )
    start = time.perf_counter()
    total_chunks = 0
    for path in paths:
        total_chunks += len(splitter.split_text(_read(path)))
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


def bench_semantic_text_splitter(paths):
    from semantic_text_splitter import TextSplitter

    splitter = TextSplitter.from_callback(word_count, MAX_TOKENS, overlap=OVERLAP)
    start = time.perf_counter()
    total_chunks = 0
    for path in paths:
        total_chunks += len(splitter.chunks(_read(path)))
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


def bench_chonkie(paths):
    from chonkie import TokenChunker

    chunker = TokenChunker(tokenizer="word", chunk_size=MAX_TOKENS, chunk_overlap=OVERLAP)
    start = time.perf_counter()
    total_chunks = 0
    for path in paths:
        total_chunks += len(chunker(_read(path)))
    elapsed = time.perf_counter() - start
    return elapsed, total_chunks


# (display name, chart color, bench function) -- order drives both the
# printed table and the chart's bar order.
LIBRARIES = [
    ("rustchunker", "#2b7a78", bench_rustchunker),
    ("LangChain", "#c94c4c", bench_langchain),
    ("LlamaIndex", "#e0a458", bench_llama_index),
    ("semantic-text-splitter", "#5b5f97", bench_semantic_text_splitter),
    ("chonkie", "#8d8741", bench_chonkie),
]
