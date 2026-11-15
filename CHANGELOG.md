# Changelog

All notable changes to this project are documented here. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Sentence overlap handles boundaries inside a whitespace token (such as
  Chinese sentences without spaces) without panicking or losing content.
- Invalid strategies raise before reading files, including with
  `on_error="skip"` and empty file lists.

### Added
- Unicode content and offset invariants, invalid UTF-8 tests, and batch parity tests.
- Release gates for Rust tests, Clippy, formatting, Python compatibility,
  and installation from the source archive.

## [1.0.1] - 2026-07-22

Packaging-only release. No functional or API changes.

### Added
- Prebuilt wheels for **Linux** (x86_64, aarch64) and **macOS** (x86_64,
  Apple Silicon), built and published via GitHub Actions. 1.0.0 shipped only a
  Windows wheel (plus an sdist); non-Windows users no longer need a Rust
  toolchain to `pip install rustchunker`.

## [1.0.0] - 2026-07-21

First stable release. The public API — `chunk`, `chunk_files`, and the `Chunk`
type — is now covered by semantic versioning.

### Added
- `chunk_files(..., on_error="raise" | "skip")`: `"skip"` drops files that
  can't be read or parsed (unsupported extension, I/O error, invalid UTF-8)
  and returns chunks for the rest, instead of aborting the whole batch. A bad
  `max_tokens` / `overlap` still raises even under `"skip"`.
- `rust-version = "1.83"` (MSRV) declared in `Cargo.toml`.
- `LICENSE-MIT` and `LICENSE-APACHE` files (the crate has always been declared
  dual-licensed; the texts are now shipped in the wheel and sdist).

### Changed
- An unknown `strategy` value now raises `ValueError` instead of
  `NotImplementedError` — it signals a caller error (typically a typo), not an
  unbuilt feature.
- Documentation now states explicitly that a "token" is a whitespace-delimited
  **word**, not a model / BPE token.

### Fixed
- A leading UTF-8 byte-order mark (BOM) in a file is now stripped before
  chunking, instead of leaking into the first chunk's text as a `﻿`
  character. Common in Windows-authored `.txt` / `.html` files.

### Removed
- The always-`None` `page_number` key was removed from `Chunk.metadata`. There
  is no pagination support to populate it, and shipping a permanently-null key
  in the stable schema would be misleading. Remaining metadata keys:
  `source_file`, `total_chunks`, `strategy_used`.
