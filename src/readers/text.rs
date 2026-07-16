use super::Reader;

pub struct TextReader;

impl Reader for TextReader {
    fn extract(&self, raw: &str) -> String {
        raw.to_string()
    }
}
