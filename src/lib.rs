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

#[pymodule]
fn _rustchunker(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Chunk>()?;
    m.add_function(wrap_pyfunction!(chunk, m)?)?;
    m.add_function(wrap_pyfunction!(chunk_files, m)?)?;
    Ok(())
}
