import pytest

from rustchunker import Chunk, chunk


def test_chunk_fixed_basic():
    original = "hello world this is a test"
    result = chunk(original, max_tokens=3)
    assert len(result) == 2
    assert all(isinstance(c, Chunk) for c in result)
    assert [c.index for c in result] == [0, 1]
    for c in result:
        assert original[c.start : c.end] == c.text


def test_chunk_applies_overlap():
    original = "one two three four five six"
    result = chunk(original, max_tokens=3, overlap=1)
    assert len(result) == 3
    assert [c.text for c in result] == ["one two", "two three four", "four five six"]
    for c in result:
        assert len(c.text.split()) <= 3
        assert original[c.start : c.end] == c.text


def test_chunk_rejects_unknown_strategy():
    with pytest.raises(NotImplementedError):
        chunk("a b c", max_tokens=2, strategy="paragraph")


def test_chunk_offsets_are_python_character_offsets_not_byte_offsets():
    # Regression test: start/end used to be Rust byte offsets, which
    # silently disagree with Python's character-based string indexing for
    # any multi-byte UTF-8 content. Every other test uses pure ASCII text,
    # where byte and character offsets coincide, so only a non-ASCII
    # fixture like this one can actually catch a regression here.
    original = "café résumé naïve test 日本語 text with emoji 🎉 padding words here"
    result = chunk(original, max_tokens=4, strategy="fixed")
    assert len(result) > 1
    for c in result:
        assert original[c.start : c.end] == c.text
