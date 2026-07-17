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
    let last_word = trimmed
        .rsplit(char::is_whitespace)
        .next()
        .unwrap_or(trimmed);
    ABBREVIATIONS.contains(&last_word)
}

/// Unicode sentence boundaries, merged back across known abbreviations so
/// e.g. "Dr. Smith is here." is one sentence, not two.
///
/// Limitation: the merge is unconditional and English-only. A genuine
/// sentence that ends on a listed abbreviation followed by another sentence
/// ("I moved to the U.S. It is large.") is incorrectly merged into one --
/// the classic sentence-boundary-disambiguation ambiguity. The list also
/// only covers common English abbreviations and is case-sensitive. This
/// trades rare false-merges for the far more common correct-merge case.
///
/// pub(crate) so lib.rs can expose it as an internal, benchmark-only
/// ground-truth oracle (see `sentence_boundaries`) for checking whether
/// other chunking libraries' chunk boundaries land on real sentence ends.
pub(crate) fn sentence_spans(text: &str) -> Vec<(usize, usize)> {
    let mut spans: Vec<(usize, usize)> = Vec::new();
    // Start of a run of candidates being merged forward across an
    // abbreviation-ending false-positive boundary (e.g. "Dr." followed by a
    // capitalized name). None means the next candidate starts its own span.
    let mut pending_start: Option<usize> = None;

    for (start, s) in text.split_sentence_bound_indices() {
        let end = start + s.len();
        let span_start = pending_start.unwrap_or(start);

        if ends_with_abbreviation(s) {
            // This candidate's own ending looks like an abbreviation, so the
            // boundary Unicode placed right after it is likely wrong --
            // don't finalize a span yet, carry the start forward so the
            // next candidate gets merged into this one instead.
            pending_start = Some(span_start);
            continue;
        }

        spans.push((span_start, end));
        pending_start = None;
    }

    // A trailing abbreviation-like ending with nothing after it to merge
    // into (text truncated right after e.g. "etc.") still needs to be
    // flushed as its own span rather than silently dropped.
    if let Some(start) = pending_start {
        spans.push((start, text.len()));
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

            // Whitespace-only segments (e.g. leading whitespace, or an
            // all-whitespace document) carry no content and no tokens --
            // skip them so they don't become empty chunks. This also keeps
            // the sentence strategy consistent with the fixed strategy,
            // which drops whitespace-only input entirely.
            if sentence_tokens == 0 {
                continue;
            }

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
        assert_eq!(
            slices(text, &spans),
            vec!["Dr. Smith is here. He is a doctor."]
        );
    }

    #[test]
    fn whitespace_only_input_yields_no_chunks() {
        assert_eq!(
            SentenceStrategy.split("   \n\t  ", 5),
            Vec::<(usize, usize)>::new()
        );
        assert_eq!(SentenceStrategy.split("", 5), Vec::<(usize, usize)>::new());
    }

    #[test]
    fn sentence_spans_itself_merges_abbreviation_not_just_the_packing_step() {
        // Regression test: a prior version merged abbreviations backward
        // instead of forward, so `sentence_spans` itself still produced
        // "Dr. " as its own separate span -- the tests above only passed
        // because a generous max_tokens let the *packing* step reassemble
        // "Dr." with the next sentence regardless. A token budget too small
        // for packing to save it (max_tokens=1) exposes the real bug: "Dr."
        // would end up as its own isolated chunk. Check sentence_spans
        // directly so this can't be masked by packing again.
        let text = "Dr. Smith is here. He is a doctor.";
        let spans = sentence_spans(text);
        assert_eq!(
            slices(text, &spans),
            vec!["Dr. Smith is here. ", "He is a doctor."]
        );
    }

    #[test]
    fn small_max_tokens_still_keeps_abbreviation_with_next_word() {
        // max_tokens=2 is enough to hold "Dr." + "Smith" together (but not
        // the whole 4-token sentence, so the oversized-sentence hard-split
        // fallback still kicks in). Before the fix, "Dr." was treated as its
        // own complete 1-token "sentence" from the start and would have
        // been emitted as its own isolated chunk regardless of max_tokens.
        let text = "Dr. Smith is here.";
        let spans = SentenceStrategy.split(text, 2);
        let result = slices(text, &spans);
        assert!(
            result[0].starts_with("Dr. Smith"),
            "expected 'Dr.' to stay attached to 'Smith', got {:?}",
            result
        );
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
        assert_eq!(
            slices(text, &spans),
            vec!["I live in the U.S.A. It is nice."]
        );
    }

    #[test]
    fn oversized_sentence_is_hard_split() {
        let text = "one two three four five six seven eight.";
        let spans = SentenceStrategy.split(text, 3);
        let result = slices(text, &spans);
        assert_eq!(
            result,
            vec!["one two three", "four five six", "seven eight."]
        );
    }
}
