pub fn extract(raw: &[u8]) -> Result<String, String> {
    // The upstream parser can panic on malformed page dictionaries.
    std::panic::catch_unwind(|| {
        let doc = lopdf::Document::load_mem(raw).map_err(|e| e.to_string())?;
        if doc.is_encrypted() {
            return Err("encrypted PDFs are unsupported; decrypt the document first".into());
        }
        let mut text = String::new();
        for page in doc.get_pages().keys() {
            let mut output = pdf_extract::PlainTextOutput::new(&mut text);
            pdf_extract::output_doc_page(&doc, &mut output, *page).map_err(|e| e.to_string())?;
            text.push('\n');
        }
        if text.trim().is_empty() {
            return Err("PDF has no extractable text; scanned documents require OCR".into());
        }
        Ok(text)
    })
    .map_err(|_| "PDF parser failed on malformed or unsupported content".to_string())?
}
