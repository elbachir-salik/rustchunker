use unicode_segmentation::UnicodeSegmentation;

use super::fixed::FixedStrategy;
use super::Strategy;
use crate::tokenizer::count_tokens;

/// Trailing tokens that Unicode's default sentence-boundary algorithm treats
/// as sentence-final (since it isn't followed by a lowercase letter) but
/// which are actually mid-sentence abbreviations. Checked against the last
/// whitespace-delimited word of a candidate sentence.
const ABBREVIATIONS: &[&str] = &[
    "Dr.", "Mr.", "Mrs.", "Ms.", "Prof.", "Sr.", "Jr.", "St.", "vs.", "etc.", "e.g.", "i.e.",
    "U.S.", "U.S.A.", "U.K.", "Inc.", "Ltd.", "Co.", "No.",
];

fn ends_with_abbreviation(sentence: &str) -> bool {
    let trimmed = sentence.trim_end();
    let last_word = trimmed.rsplit(char::is_whitespace).next().unwrap_or(trimmed);
    ABBREVIATIONS.contains(&last_word)
}

/// Unicode sentence boundaries, merged back across known abbreviations so
/// e.g. "Dr. Smith is here." is one sentence, not two.
fn sentence_spans(text: &str) -> Vec<(usize, usize)> {
    let mut spans: Vec<(usize, usize)> = Vec::new();

    for (start, s) in text.split_sentence_bound_indices() {
        let end = start + s.len();
        if ends_with_abbreviation(s) {
            if let Some(last) = spans.last_mut() {
                last.1 = end;
                continue;
            }
        }
        spans.push((start, end));
    }
    spans
}

fn flush(chunks: &mut Vec<(usize, usize)>, group_start: &mut Option<usize>, group_end: usize) {
    if let Some(start) = group_start.take() {
        chunks.push((start, group_end));
    }
}

pub struct SentenceStrategy;

impl Strategy for SentenceStrategy {
    fn split(&self, text: &str, max_tokens: usize) -> Vec<(usize, usize)> {
        let mut chunks: Vec<(usize, usize)> = Vec::new();
        let mut group_start: Option<usize> = None;
        let mut group_end: usize = 0;
        let mut group_tokens: usize = 0;

        for (start, end) in sentence_spans(text) {
            let sentence_tokens = count_tokens(&text[start..end]);

            if sentence_tokens > max_tokens {
                // A single sentence alone exceeds max_tokens: flush what we
                // have, then hard-split this sentence by tokens so the
                // max_tokens guarantee still holds.
                flush(&mut chunks, &mut group_start, group_end);
                group_tokens = 0;
                for (sub_start, sub_end) in FixedStrategy.split(&text[start..end], max_tokens) {
                    chunks.push((start + sub_start, start + sub_end));
                }
                continue;
            }

            if group_tokens > 0 && group_tokens + sentence_tokens > max_tokens {
                flush(&mut chunks, &mut group_start, group_end);
                group_tokens = 0;
            }

            if group_start.is_none() {
                group_start = Some(start);
            }
            group_tokens += sentence_tokens;
            group_end = end;
        }
        flush(&mut chunks, &mut group_start, group_end);

        chunks
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn slices<'a>(text: &'a str, spans: &[(usize, usize)]) -> Vec<&'a str> {
        spans.iter().map(|&(s, e)| &text[s..e]).collect()
    }

    #[test]
    fn keeps_abbreviation_attached() {
        let text = "Dr. Smith is here. He is a doctor.";
        let spans = SentenceStrategy.split(text, 100);
        assert_eq!(slices(text, &spans), vec!["Dr. Smith is here. He is a doctor."]);
    }

    #[test]
    fn splits_on_real_sentence_boundary_within_budget() {
        let text = "Dr. Smith is here. He is a doctor.";
        let spans = SentenceStrategy.split(text, 5);
        let result = slices(text, &spans);
        assert_eq!(result, vec!["Dr. Smith is here. ", "He is a doctor."]);
    }

    #[test]
    fn handles_acronym_like_usa() {
        let text = "I live in the U.S.A. It is nice.";
        let spans = SentenceStrategy.split(text, 100);
        assert_eq!(slices(text, &spans), vec!["I live in the U.S.A. It is nice."]);
    }

    #[test]
    fn oversized_sentence_is_hard_split() {
        let text = "one two three four five six seven eight.";
        let spans = SentenceStrategy.split(text, 3);
        let result = slices(text, &spans);
        assert_eq!(result, vec!["one two three", "four five six", "seven eight."]);
    }
}
