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


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
@pytest.mark.parametrize("text", ["", "   \n\t  "])
def test_chunk_empty_or_whitespace_returns_no_chunks(text, strategy):
    assert chunk(text, max_tokens=5, strategy=strategy) == []


def test_chunk_single_token_shorter_than_max():
    result = chunk("hello", max_tokens=10)
    assert len(result) == 1
    assert result[0].text == "hello"
    assert (result[0].start, result[0].end, result[0].index) == (0, 5, 0)


def test_chunk_rejects_zero_max_tokens():
    with pytest.raises(ValueError):
        chunk("a b c", max_tokens=0)


def test_chunk_rejects_overlap_not_smaller_than_max_tokens():
    with pytest.raises(ValueError):
        chunk("a b c", max_tokens=3, overlap=3)


def test_chunk_metadata_shape_for_single_text():
    result = chunk("one two three four", max_tokens=2, strategy="sentence")
    for i, c in enumerate(result):
        assert c.index == i
        assert c.metadata["source_file"] is None
        assert c.metadata["strategy_used"] == "sentence"
        assert c.metadata["total_chunks"] == len(result)


def test_chunk_result_is_frozen():
    c = chunk("hello world", max_tokens=5)[0]
    with pytest.raises(AttributeError):
        c.text = "mutated"
