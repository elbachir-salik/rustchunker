use scraper::Html;

use super::Reader;

pub struct HtmlReader;

impl Reader for HtmlReader {
    fn extract(&self, raw: &str) -> String {
        // scraper's DOM traversal yields <script>/<style> content as plain
        // text nodes like any other element, so it must be stripped before
        // parsing or it ends up embedded in the chunked output.
        let cleaned = strip_tag_block(raw, "script");
        let cleaned = strip_tag_block(&cleaned, "style");
        let document = Html::parse_document(&cleaned);
        document
            .root_element()
            .text()
            .collect::<Vec<_>>()
            .join(" ")
    }
}

fn find_ci(haystack: &str, needle: &str) -> Option<usize> {
    // Tag names are ASCII, so lowercasing doesn't shift byte offsets.
    haystack.to_lowercase().find(&needle.to_lowercase())
}

fn strip_tag_block(html: &str, tag: &str) -> String {
    let open_tag = format!("<{}", tag);
    let close_tag = format!("</{}>", tag);
    let mut result = String::with_capacity(html.len());
    let mut rest = html;

    while let Some(start) = find_ci(rest, &open_tag) {
        result.push_str(&rest[..start]);
        match find_ci(&rest[start..], &close_tag) {
            Some(close_rel) => rest = &rest[start + close_rel + close_tag.len()..],
            None => return result, // unterminated block: drop the remainder
        }
    }
    result.push_str(rest);
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_tags_and_extracts_text() {
        let html = "<html><body><h1>Title</h1><p>Some <b>bold</b> text.</p></body></html>";
        let text = HtmlReader.extract(html);
        assert!(text.contains("Title"));
        assert!(text.contains("Some"));
        assert!(text.contains("bold"));
        assert!(!text.contains('<'));
    }

    #[test]
    fn excludes_script_and_style_content() {
        let html = "<html><head><style>body{color:red}</style></head><body><script>alert(1)</script><p>Visible</p></body></html>";
        let text = HtmlReader.extract(html);
        assert!(text.contains("Visible"));
        assert!(!text.contains("alert"));
        assert!(!text.contains("color:red"));
    }
}
