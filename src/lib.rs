use pyo3::exceptions::{PyNotImplementedError, PyValueError};
use pyo3::prelude::*;

#[pyclass]
struct Chunk {
    #[pyo3(get)]
    text: String,
    #[pyo3(get)]
    start: usize,
    #[pyo3(get)]
    end: usize,
    #[pyo3(get)]
    index: usize,
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

/// Byte-offset spans of whitespace-delimited tokens in `text`.
/// Offsets are byte indices from `char_indices()`, which always land on
/// valid UTF-8 boundaries, so they can be sliced back into `text` safely.
fn tokenize_spans(text: &str) -> Vec<(usize, usize)> {
    let mut spans = Vec::new();
    let mut token_start: Option<usize> = None;

    for (idx, ch) in text.char_indices() {
        if ch.is_whitespace() {
            if let Some(start) = token_start.take() {
                spans.push((start, idx));
            }
        } else if token_start.is_none() {
            token_start = Some(idx);
        }
    }
    if let Some(start) = token_start {
        spans.push((start, text.len()));
    }
    spans
}

#[pyfunction]
#[pyo3(signature = (text, max_tokens, overlap=0, strategy="fixed".to_string()))]
fn chunk(text: &str, max_tokens: usize, overlap: usize, strategy: String) -> PyResult<Vec<Chunk>> {
    if strategy != "fixed" {
        return Err(PyNotImplementedError::new_err(format!(
            "strategy '{}' is not implemented yet; only 'fixed' is supported in this version",
            strategy
        )));
    }
    if overlap != 0 {
        return Err(PyValueError::new_err(
            "overlap is not yet supported; pass overlap=0",
        ));
    }
    if max_tokens == 0 {
        return Err(PyValueError::new_err("max_tokens must be greater than 0"));
    }

    let spans = tokenize_spans(text);
    let chunks = spans
        .chunks(max_tokens)
        .enumerate()
        .map(|(index, group)| {
            let start = group.first().unwrap().0;
            let end = group.last().unwrap().1;
            Chunk {
                text: text[start..end].to_string(),
                start,
                end,
                index,
            }
        })
        .collect();

    Ok(chunks)
}

#[pymodule]
fn _rustchunker(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Chunk>()?;
    m.add_function(wrap_pyfunction!(chunk, m)?)?;
    Ok(())
}
