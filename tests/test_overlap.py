import pytest

from rustchunker import chunk


@pytest.mark.parametrize("strategy", ["fixed", "sentence"])
def test_overlap_tail_matches_next_head(strategy):
    text = "one two three four five six seven eight nine ten"
    result = chunk(text, max_tokens=4, overlap=2, strategy=strategy)
    assert len(result) > 1
    for prev, nxt in zip(result, result[1:]):
        prev_tail = prev.text.split()[-2:]
        next_head = nxt.text.split()[:2]
        assert prev_tail == next_head


def test_overlap_respects_word_boundaries():
    text = "alpha beta gamma delta epsilon zeta"
    result = chunk(text, max_tokens=2, overlap=1)
    for c in result:
        assert not c.text.startswith(" ")
        words = c.text.split()
        assert all(w.strip() == w for w in words)


def test_overlap_zero_is_unchanged():
    text = "one two three four five six"
    no_overlap = chunk(text, max_tokens=3, overlap=0)
    default_overlap = chunk(text, max_tokens=3)
    assert [(c.start, c.end) for c in no_overlap] == [
        (c.start, c.end) for c in default_overlap
    ]


def test_overlap_first_chunk_starts_at_zero():
    text = "one two three four five six"
    result = chunk(text, max_tokens=3, overlap=2)
    assert result[0].start == 0


def test_overlap_must_be_smaller_than_max_tokens():
    with pytest.raises(ValueError):
        chunk("one two three four five six", max_tokens=3, overlap=3)


def test_overlap_clamped_when_previous_chunk_is_short():
    # max_tokens - overlap == 1, so base chunks are single tokens; overlap=3
    # requests more than any individual base chunk can supply, so overlap is
    # clamped per-hop rather than accumulating unbounded growth.
    text = "a b c d e"
    result = chunk(text, max_tokens=4, overlap=3)
    for c in result:
        assert len(c.text.split()) <= 4
        assert text[c.start : c.end] == c.text


def test_overlap_never_exceeds_max_tokens():
    text = "one two three four five six seven eight nine ten"
    for c in chunk(text, max_tokens=4, overlap=2):
        assert len(c.text.split()) <= 4
