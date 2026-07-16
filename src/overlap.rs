/// Extends the start of each chunk (after the first) backward by up to
/// `overlap` whitespace tokens, so consecutive chunks share trailing/leading
/// content. Operates on whole token spans, so it never cuts a word in half,
/// and never reaches back past the previous chunk's own (pre-overlap) start
/// — overlap can only pull in tokens that actually belonged to chunk N when
/// building chunk N+1's head.
///
/// Takes the document's token spans as a parameter rather than the text
/// itself, so callers that already tokenized the document (e.g. the fixed
/// strategy's own grouping) can reuse that instead of re-scanning the whole
/// document a second time just for overlap.
pub fn apply_overlap(
    token_spans: &[(usize, usize)],
    spans: &[(usize, usize)],
    overlap: usize,
) -> Vec<(usize, usize)> {
    if overlap == 0 || spans.len() < 2 {
        return spans.to_vec();
    }

    // token_spans is sorted by start offset (built via a left-to-right scan),
    // so this is a binary search, not a linear one -- important, since this
    // is called per chunk and a linear scan here would make the whole
    // function O(n^2) in document size instead of O(n log n).
    let token_index_at_or_after =
        |byte_start: usize| -> usize { token_spans.partition_point(|&(s, _)| s < byte_start) };

    let mut result = Vec::with_capacity(spans.len());
    result.push(spans[0]);

    for i in 1..spans.len() {
        let (_, end) = spans[i];
        let cur_start_idx = token_index_at_or_after(spans[i].0);
        let prev_start_idx = token_index_at_or_after(spans[i - 1].0);

        let available = cur_start_idx.saturating_sub(prev_start_idx);
        let overlap_amount = overlap.min(available);
        let new_start_idx = cur_start_idx - overlap_amount;
        let new_start = token_spans[new_start_idx].0;

        result.push((new_start, end));
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::strategies::fixed::FixedStrategy;
    use crate::strategies::Strategy;
    use crate::tokenizer::tokenize_spans;

    const TEXT: &str = "one two three four five six";

    fn fixed_spans(max_tokens: usize) -> Vec<(usize, usize)> {
        FixedStrategy.split(TEXT, max_tokens)
    }

    fn tokens() -> Vec<(usize, usize)> {
        tokenize_spans(TEXT)
    }

    #[test]
    fn no_overlap_is_a_no_op() {
        let spans = fixed_spans(3);
        assert_eq!(apply_overlap(&tokens(), &spans, 0), spans);
    }

    #[test]
    fn shares_tail_tokens_with_next_chunk() {
        let spans = fixed_spans(3); // "one two three" / "four five six"
        let overlapped = apply_overlap(&tokens(), &spans, 1);
        assert_eq!(overlapped[0], spans[0]);
        // chunk 1 should now start at "three", the last token of chunk 0
        assert_eq!(
            &TEXT[overlapped[1].0..overlapped[1].1],
            "three four five six"
        );
    }

    #[test]
    fn overlap_never_cuts_a_word() {
        let spans = fixed_spans(3);
        let overlapped = apply_overlap(&tokens(), &spans, 2);
        let head = &TEXT[overlapped[1].0..overlapped[1].1];
        assert!(head.split_whitespace().all(|w| !w.is_empty()));
        assert_eq!(head, "two three four five six");
    }

    #[test]
    fn overlap_clamped_to_previous_chunk_length() {
        let spans = fixed_spans(3);
        // requesting far more overlap than chunk 0 has tokens (3)
        let overlapped = apply_overlap(&tokens(), &spans, 100);
        assert_eq!(&TEXT[overlapped[1].0..overlapped[1].1], TEXT);
    }

    #[test]
    fn first_chunk_is_never_extended() {
        let spans = fixed_spans(3);
        let overlapped = apply_overlap(&tokens(), &spans, 2);
        assert_eq!(overlapped[0], spans[0]);
    }
}
