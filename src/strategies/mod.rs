pub mod fixed;
pub mod sentence;

/// A chunking strategy produces chunk boundaries as (start, end) byte-offset
/// spans into the original text, in order, with no strategy responsible for
/// assigning `index` — that's the orchestrator's job (see chunker.rs).
pub trait Strategy {
    fn split(&self, text: &str, max_tokens: usize) -> Vec<(usize, usize)>;
}
