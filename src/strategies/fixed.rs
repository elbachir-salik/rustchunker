use super::Strategy;
use crate::tokenizer::tokenize_spans;

pub struct FixedStrategy;

impl Strategy for FixedStrategy {
    fn split(&self, text: &str, max_tokens: usize) -> Vec<(usize, usize)> {
        group_token_spans(&tokenize_spans(text), max_tokens)
    }
}

/// Groups pre-computed token spans into `max_tokens`-sized chunk boundaries.
/// Split out from `Strategy::split` so callers that already have token spans
/// on hand (`chunker::chunk_core`, to avoid re-tokenizing the whole document
/// again for overlap) can reuse them directly instead of retokenizing.
pub fn group_token_spans(token_spans: &[(usize, usize)], max_tokens: usize) -> Vec<(usize, usize)> {
    // slice::chunks(0) panics; callers reach here only after chunker.rs has
    // validated max_tokens > 0, but assert it so a future caller that skips
    // that guard fails a debug build loudly instead of panicking obscurely.
    debug_assert!(max_tokens > 0, "group_token_spans requires max_tokens > 0");
    token_spans
        .chunks(max_tokens)
        .map(|group| (group.first().unwrap().0, group.last().unwrap().1))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splits_every_n_tokens() {
        let spans = FixedStrategy.split("hello world this is a test", 3);
        assert_eq!(spans, vec![(0, 16), (17, 26)]);
    }
}
