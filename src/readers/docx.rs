use std::io::{Cursor, Read};

const WORD_NAMESPACES: &[&str] = &[
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
];

const COMPATIBILITY_NS: &str = "http://schemas.openxmlformats.org/markup-compatibility/2006";

pub fn extract(raw: &[u8]) -> Result<String, String> {
    let mut archive = zip::ZipArchive::new(Cursor::new(raw)).map_err(|e| e.to_string())?;
    let mut document = archive
        .by_name("word/document.xml")
        .map_err(|e| e.to_string())?;
    // Bound decompression of untrusted archives without extracting files to disk.
    const MAX_XML_BYTES: u64 = 64 * 1024 * 1024;
    let mut xml = String::new();
    document
        .by_ref()
        .take(MAX_XML_BYTES + 1)
        .read_to_string(&mut xml)
        .map_err(|e| e.to_string())?;
    if xml.len() as u64 > MAX_XML_BYTES {
        return Err("DOCX document.xml exceeds the 64 MiB extraction limit".into());
    }
    let document = roxmltree::Document::parse(&xml).map_err(|e| e.to_string())?;
    let root = document.root_element();
    if !is_word_element(root) || root.tag_name().name() != "document" {
        return Err("DOCX main part is not a Word document".into());
    }
    let mut text = String::new();
    for node in document
        .descendants()
        .filter(|node| is_word_element(*node) && is_selected_content(*node))
    {
        match node.tag_name().name() {
            "t" => text.push_str(node.text().unwrap_or("")),
            "tab" | "tc" => text.push('\t'),
            "br" | "cr" | "p" => text.push('\n'),
            _ => {}
        }
    }
    Ok(text)
}

fn is_word_element(node: roxmltree::Node<'_, '_>) -> bool {
    node.is_element()
        && node
            .tag_name()
            .namespace()
            .is_some_and(|ns| WORD_NAMESPACES.contains(&ns))
}

fn is_selected_content(node: roxmltree::Node<'_, '_>) -> bool {
    node.ancestors().all(|branch| {
        let Some(parent) = branch
            .parent()
            .filter(|parent| parent.has_tag_name((COMPATIBILITY_NS, "AlternateContent")))
        else {
            return true;
        };
        // Plain-text extraction prefers the first Choice, or Fallback if none exists.
        let selected = parent
            .children()
            .find(|child| child.has_tag_name((COMPATIBILITY_NS, "Choice")))
            .or_else(|| {
                parent
                    .children()
                    .find(|child| child.has_tag_name((COMPATIBILITY_NS, "Fallback")))
            });
        selected == Some(branch)
    })
}
