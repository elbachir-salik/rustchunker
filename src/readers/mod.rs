use std::borrow::Cow;

pub mod html;
pub mod markdown;
pub mod text;

/// Extracts plain, chunkable text from a file's raw contents.
///
/// Returns `Cow` so a reader whose extraction is the identity (plain text)
/// can borrow the input with zero allocation, while readers that transform
/// the input (markdown/HTML stripping) return an owned `String`.
pub trait Reader {
    fn extract<'a>(&self, raw: &'a str) -> Cow<'a, str>;
}

/// Human-readable list of accepted file extensions, kept next to
/// `reader_for_extension` so the two can't drift apart in error messages.
pub const SUPPORTED_EXTENSIONS: &str = ".txt, .md, .markdown, .html, .htm";

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
