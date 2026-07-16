pub mod html;
pub mod markdown;
pub mod text;

/// Extracts plain, chunkable text from a file's raw contents.
pub trait Reader {
    fn extract(&self, raw: &str) -> String;
}

/// Picks a reader based on a file's extension (case-insensitive).
/// Returns `None` for unrecognized extensions so callers can fail loudly
/// instead of silently mistreating, e.g., a `.pdf` as plain text.
pub fn reader_for_extension(ext: &str) -> Option<Box<dyn Reader>> {
    match ext.to_lowercase().as_str() {
        "txt" => Some(Box::new(text::TextReader)),
        "md" | "markdown" => Some(Box::new(markdown::MarkdownReader)),
        "html" | "htm" => Some(Box::new(html::HtmlReader)),
        _ => None,
    }
}
