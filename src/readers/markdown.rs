use super::Reader;

pub struct MarkdownReader;

impl Reader for MarkdownReader {
    fn extract(&self, raw: &str) -> String {
        strip_markdown(raw)
    }
}

fn strip_header_prefix(line: &str) -> &str {
    let trimmed = line.trim_start();
    let hashes = trimmed.chars().take_while(|&c| c == '#').count();
    if hashes > 0 && hashes <= 6 {
        trimmed[hashes..].trim_start()
    } else {
        line
    }
}

/// Removes paired markers (e.g. `**bold**`), keeping the enclosed text.
/// An unmatched trailing marker is left as-is rather than dropped, since
/// there's no way to tell it apart from literal text at that point.
fn remove_paired_markers(text: &str, marker: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(start) = rest.find(marker) {
        let after = &rest[start + marker.len()..];
        match after.find(marker) {
            Some(end) => {
                result.push_str(&rest[..start]);
                result.push_str(&after[..end]);
                rest = &after[end + marker.len()..];
            }
            None => break,
        }
    }
    result.push_str(rest);
    result
}

/// Converts `[text](url)` to `text` and `![alt](url)` to `alt`. Bracketed
/// text with no following `(...)` (e.g. `array[0]`) is left untouched.
fn strip_links(text: &str) -> String {
    let mut result = String::with_capacity(text.len());
    let mut rest = text;
    loop {
        let Some(bracket_start) = rest.find('[') else {
            result.push_str(rest);
            break;
        };

        let is_image = bracket_start > 0 && rest.as_bytes()[bracket_start - 1] == b'!';
        let after_bracket = &rest[bracket_start + 1..];

        let matched = after_bracket.find(']').and_then(|close_bracket_rel| {
            let link_text = &after_bracket[..close_bracket_rel];
            let after_close_bracket = &after_bracket[close_bracket_rel + 1..];
            after_close_bracket.strip_prefix('(').and_then(|after_paren| {
                after_paren
                    .find(')')
                    .map(|close_paren_rel| (link_text, &after_paren[close_paren_rel + 1..]))
            })
        });

        match matched {
            Some((link_text, remainder)) => {
                let before_len = if is_image {
                    bracket_start - 1
                } else {
                    bracket_start
                };
                result.push_str(&rest[..before_len]);
                result.push_str(link_text);
                rest = remainder;
            }
            None => {
                result.push_str(&rest[..=bracket_start]);
                rest = &rest[bracket_start + 1..];
            }
        }
    }
    result
}

pub fn strip_markdown(text: &str) -> String {
    let header_stripped = text
        .lines()
        .map(strip_header_prefix)
        .collect::<Vec<_>>()
        .join("\n");
    let no_bold = remove_paired_markers(&header_stripped, "**");
    let no_bold = remove_paired_markers(&no_bold, "__");
    strip_links(&no_bold)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn strips_headers() {
        assert_eq!(strip_markdown("# Title\n## Subtitle\nbody"), "Title\nSubtitle\nbody");
    }

    #[test]
    fn strips_bold() {
        assert_eq!(strip_markdown("this is **bold** and __also bold__"), "this is bold and also bold");
    }

    #[test]
    fn strips_links() {
        assert_eq!(
            strip_markdown("See [OpenAI](https://openai.com) docs"),
            "See OpenAI docs"
        );
    }

    #[test]
    fn strips_images() {
        assert_eq!(strip_markdown("![Alt text](image.png)"), "Alt text");
    }

    #[test]
    fn leaves_non_link_brackets_alone() {
        assert_eq!(strip_markdown("array[0] is first"), "array[0] is first");
    }

    #[test]
    fn combined_document() {
        let doc = "# Report\n\nThis is **important**: see [source](http://x.com).";
        assert_eq!(
            strip_markdown(doc),
            "Report\n\nThis is important: see source."
        );
    }
}
