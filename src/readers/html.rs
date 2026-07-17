use std::borrow::Cow;

use scraper::Html;

use super::Reader;

pub struct HtmlReader;

impl Reader for HtmlReader {
    fn extract<'a>(&self, raw: &'a str) -> Cow<'a, str> {
        // scraper's DOM traversal yields <script>/<style> content as plain
        // text nodes like any other element, so it must be stripped before
        // parsing or it ends up embedded in the chunked output.
        let cleaned = strip_tag_block(raw, "script");
        let cleaned = strip_tag_block(&cleaned, "style");
        let document = Html::parse_document(&cleaned);
        Cow::Owned(
            document
                .root_element()
                .text()
                .collect::<Vec<_>>()
                .join(" "),
        )
    }
}

/// ASCII-case-insensitive substring search returning a byte offset into
/// `haystack`. Tag names are ASCII, so we compare byte-by-byte with
/// `eq_ignore_ascii_case` and never allocate. The previous implementation
/// did `haystack.to_lowercase()` on every call, which was both:
///   - quadratic on large documents: a full O(n) allocation + Unicode
///     lowercasing pass per match, and this is called once per `<script>`
///     and `</script>` (and again for `<style>`), so a Wikipedia page with
///     many `<style>` blocks spent >100ms here alone; and
///   - subtly wrong: lowercasing non-ASCII *haystack* content can change
///     byte lengths, so the offset found in the lowercased copy may not be
///     a valid offset into the original string. ASCII bytes never appear as
///     UTF-8 continuation bytes, so an ASCII byte search always lands on a
///     valid char boundary.
fn find_ci(haystack: &str, needle: &str) -> Option<usize> {
    let h = haystack.as_bytes();
    let n = needle.as_bytes();
    if n.is_empty() || h.len() < n.len() {
        return None;
    }
    (0..=h.len() - n.len())
        .find(|&i| h[i..i + n.len()].eq_ignore_ascii_case(n))
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

    #[test]
    fn strips_uppercase_and_mixed_case_tags() {
        let html = "<HTML><HEAD><STYLE>x{y:z}</STYLE></HEAD><BODY><Script>bad()</Script><p>Keep</p></BODY></HTML>";
        let text = HtmlReader.extract(html);
        assert!(text.contains("Keep"));
        assert!(!text.contains("bad"));
        assert!(!text.contains("x{y:z}"));
    }

    #[test]
    fn handles_non_ascii_content_before_stripped_tags() {
        // Regression: the old find_ci lowercased the whole haystack per
        // search, so non-ASCII content *before* a tag could shift the byte
        // offset it returned (wrong slice, or a panic on a non-char
        // boundary). Multi-byte characters before <style>/<script> exercise
        // that path -- the ASCII byte search must land on valid boundaries.
        let html = "<p>café résumé 日本語 —— naïve</p><style>a{b:c}</style><p>Kept 🎉 here</p><script>bad()</script>";
        let text = HtmlReader.extract(html);
        assert!(text.contains("café"));
        assert!(text.contains("日本語"));
        assert!(text.contains("Kept"));
        assert!(!text.contains("a{b:c}"));
        assert!(!text.contains("bad"));
    }
}
