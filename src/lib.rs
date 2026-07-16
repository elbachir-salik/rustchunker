use pyo3::prelude::*;

mod chunker;
mod overlap;
mod readers;
mod strategies;
mod tokenizer;

#[pyclass]
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
    paths: Vec<String>,
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
