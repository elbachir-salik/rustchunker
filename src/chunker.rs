use pyo3::exceptions::{PyNotImplementedError, PyValueError};
use pyo3::prelude::*;

use crate::overlap::apply_overlap;
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
    if max_tokens == 0 {
        return Err(PyValueError::new_err("max_tokens must be greater than 0"));
    }
    if overlap >= max_tokens && overlap != 0 {
        return Err(PyValueError::new_err(
            "overlap must be smaller than max_tokens",
        ));
    }

    // Strategies group content into (max_tokens - overlap)-sized "core"
    // spans; apply_overlap then extends each span's start backward into the
    // previous chunk's tokens, bringing the total size back up to
    // max_tokens. Doing it this way (rather than grouping at max_tokens and
    // extending on top) keeps the max_tokens cap meaningful when overlap>0.
    let core_max_tokens = max_tokens - overlap;

    let spans = match strategy {
        "fixed" => FixedStrategy.split(text, core_max_tokens),
        "sentence" => SentenceStrategy.split(text, core_max_tokens),
        other => {
            return Err(PyNotImplementedError::new_err(format!(
                "strategy '{}' is not implemented yet; only 'fixed' and 'sentence' are supported in this version",
                other
            )))
        }
    };

    let spans = apply_overlap(text, &spans, overlap);

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
