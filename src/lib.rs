use std::path::PathBuf;

use pyo3::prelude::*;

mod chunker;
mod overlap;
mod readers;
mod strategies;
mod tokenizer;

/// A single chunk of a document. Produced only by `chunk()` and
/// `chunk_files()` -- not constructible directly from Python.
///
/// `start`/`end` are character offsets into the *source document*
/// (`text == source[start:end]` in Python, including for non-ASCII text).
///
/// `index` is the chunk's position *within its own source document*
/// (0-based). For `chunk_files`, the returned list concatenates the chunks
/// of every file, so `index` restarts at 0 at each file boundary and is NOT
/// the position in the returned list -- use `metadata["source_file"]` to
/// tell chunks of different files apart, and `metadata["total_chunks"]` for
/// the count within that one file.
///
/// `frozen`: chunks are immutable outputs, so this is read-only from Python.
#[pyclass(frozen)]
pub struct Chunk {
    #[pyo3(get)]
    pub text: String,
    #[pyo3(get)]
    pub start: usize,
    #[pyo3(get)]
    pub end: usize,
    #[pyo3(get)]
    pub index: usize,
    #[pyo3(get)]
    pub metadata: Py<pyo3::types::PyDict>,
}

#[pymethods]
impl Chunk {
    fn __repr__(&self) -> String {
        format!(
            "Chunk(index={}, start={}, end={}, text={:?})",
            self.index, self.start, self.end, self.text
        )
    }
}

#[pyfunction]
#[pyo3(signature = (text, max_tokens, overlap=0, strategy="fixed".to_string()))]
fn chunk(
    py: Python<'_>,
    text: &str,
    max_tokens: usize,
    overlap: usize,
    strategy: String,
) -> PyResult<Vec<Chunk>> {
    chunker::chunk_text(py, text, max_tokens, overlap, &strategy)
}

#[pyfunction]
#[pyo3(signature = (paths, max_tokens, overlap=0, strategy="fixed".to_string()))]
fn chunk_files(
    py: Python<'_>,
    // Vec<PathBuf> so callers can pass str or any os.PathLike (e.g. the
    // pathlib.Path objects returned by Path.glob), not just plain strings.
    paths: Vec<PathBuf>,
    max_tokens: usize,
    overlap: usize,
    strategy: String,
) -> PyResult<Vec<Chunk>> {
    chunker::chunk_files(py, &paths, max_tokens, overlap, &strategy)
}

/// Internal/unstable: exposes rustchunker's own Unicode sentence-boundary
/// detection as a ground-truth oracle for the benchmark suite's chunk
/// boundary correctness comparison (see benchmarks/bench_correctness.py).
/// Not part of the public chunking API and not re-exported from
/// python/rustchunker/__init__.py -- reuses this crate's already-tested
/// sentence detection instead of introducing a second, possibly-disagreeing
/// "what counts as a sentence" implementation just for benchmarking.
///
/// Returns character offsets (see ByteToChar), matching Chunk.start/end and
/// Python string indexing, not the byte offsets used internally.
#[pyfunction]
fn sentence_boundaries(text: &str) -> Vec<(usize, usize)> {
    let byte_to_char = tokenizer::ByteToChar::new(text);
    strategies::sentence::sentence_spans(text)
        .into_iter()
        .map(|(s, e)| (byte_to_char.convert(s), byte_to_char.convert(e)))
        .collect()
}

#[pymodule]
fn _rustchunker(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Chunk>()?;
    m.add_function(wrap_pyfunction!(chunk, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_files, m)?)?;
    m.add_function(wrap_pyfunction!(sentence_boundaries, m)?)?;
    Ok(())
}
