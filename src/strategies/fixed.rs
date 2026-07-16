use super::Strategy;
use crate::tokenizer::tokenize_spans;

pub struct FixedStrategy;

impl Strategy for FixedStrategy {
    fn split(&self, text: &str, max_tokens: usize) -> Vec<(usize, usize)> {
        let spans = tokenize_spans(text);
        spans
            .chunks(max_tokens)
            .map(|group| (group.first().unwrap().0, group.last().unwrap().1))
            .collect()
    }
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
