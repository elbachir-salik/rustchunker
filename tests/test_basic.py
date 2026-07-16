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


def test_chunk_rejects_overlap():
    with pytest.raises(ValueError):
        chunk("a b c", max_tokens=2, overlap=1)


def test_chunk_rejects_unknown_strategy():
    with pytest.raises(NotImplementedError):
        chunk("a b c", max_tokens=2, strategy="sentence")
