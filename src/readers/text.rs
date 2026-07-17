use std::borrow::Cow;

use super::Reader;

pub struct TextReader;

impl Reader for TextReader {
    fn extract<'a>(&self, raw: &'a str) -> Cow<'a, str> {
        // Plain text needs no transformation -- borrow it, no allocation.
        Cow::Borrowed(raw)
    }
}
