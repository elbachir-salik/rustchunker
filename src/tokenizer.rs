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
/// For ASCII text -- the overwhelmingly common case -- byte offset equals
/// char offset, so no table is built and `convert` is the identity. This
/// avoids allocating one `usize` per character of the whole document (tens
/// of MB on a large file) just to convert a few hundred chunk boundaries.
///
/// For non-ASCII text the table of char-boundary byte offsets is built once
/// and binary-searched per offset, so converting many boundaries stays
/// O(n log n) rather than re-scanning from the start for each one.
pub enum ByteToChar {
    /// byte offset == char offset for every position; nothing to store.
    Ascii,
    /// Sorted byte offsets of each character boundary.
    Utf8(Vec<usize>),
}

impl ByteToChar {
    pub fn new(text: &str) -> Self {
        if text.is_ascii() {
            ByteToChar::Ascii
        } else {
            ByteToChar::Utf8(text.char_indices().map(|(b, _)| b).collect())
        }
    }

    /// `byte_offset` must be a valid char boundary (start of some character,
    /// or the text's total byte length for an end-of-string offset).
    pub fn convert(&self, byte_offset: usize) -> usize {
        match self {
            ByteToChar::Ascii => byte_offset,
            ByteToChar::Utf8(boundaries) => boundaries.partition_point(|&b| b < byte_offset),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ascii_offsets_are_identity() {
        let text = "hello world";
        let b2c = ByteToChar::new(text);
        assert!(matches!(b2c, ByteToChar::Ascii));
        for i in 0..=text.len() {
            assert_eq!(b2c.convert(i), i);
        }
    }

    #[test]
    fn non_ascii_offsets_map_bytes_to_chars() {
        // "café" -> 'c'(0) 'a'(1) 'f'(2) 'é'(3, 2 bytes at byte 3..5), len 5 bytes / 4 chars
        let text = "café";
        assert_eq!(text.len(), 5);
        let b2c = ByteToChar::new(text);
        assert!(matches!(b2c, ByteToChar::Utf8(_)));
        assert_eq!(b2c.convert(0), 0); // 'c'
        assert_eq!(b2c.convert(3), 3); // 'é' start
        assert_eq!(b2c.convert(5), 4); // end of string -> char count
    }
}
