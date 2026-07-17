use std::path::{Path, PathBuf};

use pyo3::exceptions::{PyIOError, PyNotImplementedError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rayon::prelude::*;

use crate::overlap::apply_overlap;
use crate::readers::reader_for_extension;
use crate::strategies::fixed::group_token_spans;
use crate::strategies::sentence::SentenceStrategy;
use crate::strategies::Strategy;
use crate::tokenizer::{tokenize_spans, ByteToChar};
use crate::Chunk;

/// A chunk boundary plus its position within its own source text, before
/// it's wrapped into a `Chunk` pyclass with a metadata dict. Pure Rust data
/// (no Python types), so it's safe to build in parallel across rayon
/// worker threads without touching the GIL.
struct RawChunk {
    text: String,
    start: usize,
    end: usize,
    index: usize,
}

/// Splits `text` into chunk boundaries per `strategy`, with overlap folded
/// in. No Python types involved — safe to call from any thread.
fn chunk_core(text: &str, max_tokens: usize, overlap: usize, strategy: &str) -> PyResult<Vec<RawChunk>> {
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

    // Tokenize once and reuse it for both the fixed strategy's own grouping
    // and apply_overlap's token-boundary lookups, instead of each computing
    // it independently (previously a second full-document scan whenever
    // strategy=="fixed" and overlap>0). Computed lazily -- only when one of
    // those two consumers will actually need it -- so e.g. sentence strategy
    // with overlap=0 still does zero whitespace-tokenization passes.
    let token_spans = if strategy == "fixed" || overlap > 0 {
        Some(tokenize_spans(text))
    } else {
        None
    };

    let spans = match strategy {
        "fixed" => group_token_spans(token_spans.as_ref().unwrap(), core_max_tokens),
        "sentence" => SentenceStrategy.split(text, core_max_tokens),
        other => {
            return Err(PyNotImplementedError::new_err(format!(
                "strategy '{}' is not implemented yet; only 'fixed' and 'sentence' are supported in this version",
                other
            )))
        }
    };

    let spans = if overlap > 0 {
        apply_overlap(token_spans.as_ref().unwrap(), &spans, overlap)
    } else {
        spans
    };

    // RawChunk.start/end must be Python-string-compatible character
    // offsets (see ByteToChar's doc comment) even though everything above
    // this point operates on Rust byte offsets.
    let byte_to_char = ByteToChar::new(text);

    Ok(spans
        .into_iter()
        .enumerate()
        .map(|(index, (start, end))| RawChunk {
            text: text[start..end].to_string(),
            start: byte_to_char.convert(start),
            end: byte_to_char.convert(end),
            index,
        })
        .collect())
}

fn build_metadata(
    py: Python<'_>,
    source_file: Option<&str>,
    total_chunks: usize,
    strategy: &str,
) -> PyResult<Py<PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("source_file", source_file)?;
    dict.set_item("page_number", py.None())?;
    dict.set_item("total_chunks", total_chunks)?;
    dict.set_item("strategy_used", strategy)?;
    Ok(dict.unbind())
}

fn build_chunk(
    py: Python<'_>,
    raw: RawChunk,
    source_file: Option<&str>,
    total_chunks: usize,
    strategy: &str,
) -> PyResult<Chunk> {
    Ok(Chunk {
        text: raw.text,
        start: raw.start,
        end: raw.end,
        index: raw.index,
        metadata: build_metadata(py, source_file, total_chunks, strategy)?,
    })
}

pub fn chunk_text(
    py: Python<'_>,
    text: &str,
    max_tokens: usize,
    overlap: usize,
    strategy: &str,
) -> PyResult<Vec<Chunk>> {
    // The chunking itself is pure Rust and can be CPU-heavy on a large
    // document (Unicode sentence detection), so release the GIL for it and
    // only re-acquire to build the Python Chunk objects.
    let raws = py.detach(|| chunk_core(text, max_tokens, overlap, strategy))?;
    let total_chunks = raws.len();
    raws.into_iter()
        .map(|raw| build_chunk(py, raw, None, total_chunks, strategy))
        .collect()
}

fn read_and_chunk_file(
    path: &Path,
    max_tokens: usize,
    overlap: usize,
    strategy: &str,
) -> PyResult<Vec<RawChunk>> {
    let extension = path.extension().and_then(|e| e.to_str()).ok_or_else(|| {
        PyValueError::new_err(format!(
            "file '{}' has no recognizable extension",
            path.display()
        ))
    })?;

    let reader = reader_for_extension(extension).ok_or_else(|| {
        PyValueError::new_err(format!(
            "unsupported file extension '.{}' for '{}'; supported: {}",
            extension,
            path.display(),
            crate::readers::SUPPORTED_EXTENSIONS,
        ))
    })?;

    let raw_contents = std::fs::read_to_string(path)
        .map_err(|e| PyIOError::new_err(format!("failed to read '{}': {}", path.display(), e)))?;

    let text = reader.extract(&raw_contents);
    chunk_core(&text, max_tokens, overlap, strategy)
}

/// Reads and chunks every file in `paths` in parallel across CPU cores via
/// rayon. The parallel section is pure Rust (no GIL); `Chunk` pyclass
/// instances (which need the GIL to build their metadata dict) are only
/// constructed afterward, back on the calling thread.
pub fn chunk_files(
    py: Python<'_>,
    paths: &[PathBuf],
    max_tokens: usize,
    overlap: usize,
    strategy: &str,
) -> PyResult<Vec<Chunk>> {
    // Read + chunk every file in parallel with the GIL released, so other
    // Python threads keep running during this CPU/IO-bound work. Only
    // pure-Rust data (RawChunk) is produced here; the Python Chunk objects
    // (which need the GIL for their metadata dict) are built afterward, on
    // the calling thread with the GIL re-held.
    let per_file: Vec<(&PathBuf, Vec<RawChunk>)> = py.detach(|| {
        paths
            .par_iter()
            .map(|path| -> PyResult<(&PathBuf, Vec<RawChunk>)> {
                let raws = read_and_chunk_file(path, max_tokens, overlap, strategy)?;
                Ok((path, raws))
            })
            .collect::<PyResult<Vec<_>>>()
    })?;

    let mut chunks = Vec::with_capacity(per_file.iter().map(|(_, raws)| raws.len()).sum());
    for (path, raws) in per_file {
        let total_chunks = raws.len();
        // Non-UTF-8 paths (rare) can't be represented as a Python str here,
        // so source_file is left as None rather than lossily mangled.
        let source_file = path.to_str();
        for raw in raws {
            chunks.push(build_chunk(py, raw, source_file, total_chunks, strategy)?);
        }
    }
    Ok(chunks)
}
