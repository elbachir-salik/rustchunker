use pyo3::exceptions::{PyNotImplementedError, PyValueError};
use pyo3::prelude::*;

use crate::strategies::fixed::FixedStrategy;
use crate::strategies::sentence::SentenceStrategy;
use crate::strategies::Strategy;
use crate::Chunk;

pub fn chunk_text(
    text: &str,
    max_tokens: usize,
    overlap: usize,
    strategy: &str,
) -> PyResult<Vec<Chunk>> {
    if overlap != 0 {
        return Err(PyValueError::new_err(
            "overlap is not yet supported; pass overlap=0",
        ));
    }
    if max_tokens == 0 {
        return Err(PyValueError::new_err("max_tokens must be greater than 0"));
    }

    let spans = match strategy {
        "fixed" => FixedStrategy.split(text, max_tokens),
        "sentence" => SentenceStrategy.split(text, max_tokens),
        other => {
            return Err(PyNotImplementedError::new_err(format!(
                "strategy '{}' is not implemented yet; only 'fixed' and 'sentence' are supported in this version",
                other
            )))
        }
    };

    Ok(spans
        .into_iter()
        .enumerate()
        .map(|(index, (start, end))| Chunk {
            text: text[start..end].to_string(),
            start,
            end,
            index,
        })
        .collect())
}
