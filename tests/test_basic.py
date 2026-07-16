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
