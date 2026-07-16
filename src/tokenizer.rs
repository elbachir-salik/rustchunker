/// Byte-offset spans of whitespace-delimited tokens in `text`.
/// Offsets are byte indices from `char_indices()`, which always land on
/// valid UTF-8 boundaries, so they can be sliced back into `text` safely.
pub fn tokenize_spans(text: &str) -> Vec<(usize, usize)> {
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

/// Count of whitespace-delimited tokens in `text`.
pub fn count_tokens(text: &str) -> usize {
    text.split_whitespace().count()
}

/// Converts Rust byte offsets to Unicode character (codepoint) offsets.
/// All internal chunking logic operates on byte offsets (needed to slice
/// `&str` correctly and cheaply), but Python string indexing is
/// character-based -- `text[start:end]` in Python silently disagrees with
/// a byte offset for any text containing multi-byte UTF-8 characters
/// (accented letters, smart quotes, CJK, emoji). This must be the only
/// place that conversion happens, right at the Python-facing boundary.
///
/// Built once per document (a single pass over `char_indices()`) and
/// binary-searched per offset, so converting many chunk boundaries stays
/// O(n log n) rather than re-scanning from the start for each one.
pub struct ByteToChar {
    char_boundary_bytes: Vec<usize>,
}

impl ByteToChar {
    pub fn new(text: &str) -> Self {
        Self {
            char_boundary_bytes: text.char_indices().map(|(b, _)| b).collect(),
        }
    }

    /// `byte_offset` must be a valid char boundary (start of some character,
    /// or the text's total byte length for an end-of-string offset).
    pub fn convert(&self, byte_offset: usize) -> usize {
        self.char_boundary_bytes.partition_point(|&b| b < byte_offset)
    }
}
