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
